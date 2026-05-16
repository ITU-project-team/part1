"""
서울특별시 구별 UMC 지표 전처리 (통합 코드)
R preprocess_connectivity.R → Python 변환
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output" / "tables"

# --- 구 코드 매핑 테이블 ---
gu_codes = pd.DataFrame({
    "gu_name": [
        "종로구", "중구", "용산구", "성동구", "광진구",
        "동대문구", "중랑구", "성북구", "강북구", "도봉구",
        "노원구", "은평구", "서대문구", "마포구", "양천구",
        "강서구", "구로구", "금천구", "영등포구", "동작구",
        "관악구", "서초구", "강남구", "송파구", "강동구",
    ],
    "district_code": [
        11010, 11020, 11030, 11040, 11050,
        11060, 11070, 11080, 11090, 11100,
        11110, 11120, 11130, 11140, 11150,
        11160, 11170, 11180, 11190, 11200,
        11210, 11220, 11230, 11240, 11250,
    ],
    "sq1_code": list(range(1, 26)),
})


# ============================================================
# PART 1: 통신품질 (CQ_1_2022~2024)
# ============================================================

years = [2022, 2023, 2024]
raw_list = []
for yr in years:
    path = RAW / f"CQ_1_{yr}.csv"
    df = pd.read_csv(path, encoding="cp949")
    # 제거: 구분, 읍면동, 접속성공률 관련 열, LTE 관련 열
    drop_cols = [c for c in df.columns if c in ["구분", "읍면동"]
                 or "접속성공률" in c or "LTE" in c]
    df = df.drop(columns=drop_cols, errors="ignore")
    df["year"] = yr
    raw_list.append(df)

df_all = pd.concat(raw_list, ignore_index=True)

df_seoul = df_all[
    (df_all["시도"] == "서울특별시") &
    df_all["시군구"].notna() &
    (df_all["시군구"] != "")
].drop(columns=["시도"])

numeric_cols_cq = [
    "전송속도(다운로드)", "전송속도(업로드)",
    "전송성공률(다운로드)", "전송성공률(업로드)",
    "접속시간(다운로드)", "접속시간(업로드)",
    "평균 지연", "평균 손실률",
]

for col in numeric_cols_cq:
    if col in df_seoul.columns:
        df_seoul[col] = pd.to_numeric(df_seoul[col].astype(str).str.strip(), errors="coerce")

df_cq = (
    df_seoul.groupby("시군구")[numeric_cols_cq]
    .mean()
    .reset_index()
    .merge(gu_codes[["gu_name", "district_code"]], left_on="시군구", right_on="gu_name", how="left")
    .drop(columns=["gu_name"])
    .rename(columns={
        "시군구":           "district",
        "전송속도(다운로드)":  "download_speed",
        "전송속도(업로드)":   "upload_speed",
        "전송성공률(다운로드)": "download_success",
        "전송성공률(업로드)":  "upload_success",
        "접속시간(다운로드)":  "download_latency",
        "접속시간(업로드)":   "upload_latency",
        "평균 지연":         "avg_delay",
        "평균 손실률":        "avg_loss_rate",
    })
)
df_cq = df_cq[["district_code", "district"] + [c for c in df_cq.columns
                                                if c not in ["district_code", "district"]]]

print("=== PART 1 완료: 통신품질 ===")


# ============================================================
# PART 2: 공공 와이파이 / 인구 (AFU_1_SGG.xlsx)
# ============================================================

df_afu = pd.read_excel(RAW / "AFU_1_SGG.xlsx")
df_afu["wifi_per_1k_total"] = df_afu["wifi"] / df_afu["olderly"] * 1000
df_afu["SIGUNGU_CD"] = pd.to_numeric(df_afu["SIGUNGU_CD"], errors="coerce")
df_afu = df_afu[["SIGUNGU_CD", "wifi_per_1k_total"]]

print("=== PART 2 완료: 와이파이/인구 ===")


# ============================================================
# PART 3: 서울시민 디지털역량 실태조사 2023
# ============================================================

import pyreadstat

sav, meta = pyreadstat.read_sav(str(RAW / "Seoul_digital_2023.SAV"))

# --- 파생 변수 생성 ---

# Devices: 기기 보유 종류 수 (Q1K1_1~7)
device_home_cols = [f"Q1K1_{i}" for i in range(1, 8)]
device_home_cols_exist = [c for c in device_home_cols if c in sav.columns]
sav["device_home_count"] = (
    sav[device_home_cols_exist].notna() & (sav[device_home_cols_exist] != 0)
).sum(axis=1)

# Devices: 기기 사용 종류 수 (Q1K2_1~10)
device_use_cols = [f"Q1K2_{i}" for i in range(1, 11)]
device_use_cols_exist = [c for c in device_use_cols if c in sav.columns]
sav["device_use_count"] = (
    sav[device_use_cols_exist].notna() & (sav[device_use_cols_exist] != 0)
).sum(axis=1)

# Digital Skills: Q4(기본조작) + Q5B(서비스이용) + Q7(비판적이해)
# Q4_1~6 (24점) + Q5B_1~10 (40점) + Q7_1~5 (20점) = 84점 만점
skill_cols    = [f"Q4_{i}" for i in range(1, 7)]
service_cols  = [f"Q5B_{i}" for i in range(1, 11)]
critical_cols = [f"Q7_{i}" for i in range(1, 6)]
all_skill_cols = skill_cols + service_cols + critical_cols
all_skill_cols_exist = [c for c in all_skill_cols if c in sav.columns]
sav["skill_total"] = sav[all_skill_cols_exist].sum(axis=1, skipna=True)

# Safety: 디지털 보안 (Q10_1~10, 40점 만점)
safety_cols = [f"Q10_{i}" for i in range(1, 11)]
safety_cols_exist = [c for c in safety_cols if c in sav.columns]
sav["safety_total"] = sav[safety_cols_exist].sum(axis=1, skipna=True)

# Available for use: 인터넷 이용 빈도
sav["internet_active"] = (sav["Q3"] == 1).astype(int)

# 연령 그룹 (65세 이상 = 1)
sav["age_group"] = (sav["HSQ3"] >= 6).astype(int)


# --- 가중 평균 / 가중 비율 함수 ---
def wmean(x, w):
    mask = x.notna() & w.notna()
    if mask.sum() == 0:
        return np.nan
    return (x[mask] * w[mask]).sum() / w[mask].sum()


def wprop(x, w):
    mask = x.notna() & w.notna()
    if mask.sum() == 0:
        return np.nan
    return ((x[mask] == 1) * w[mask]).sum() / w[mask].sum()


# --- 구별 전체 인구 집계 ---
def agg_wmean(grp, var, wt_col="WT"):
    return wmean(grp[var], grp[wt_col])


rows = []
for sq1, grp in sav.groupby("SQ1"):
    rows.append({
        "SQ1": sq1,
        "device_home_all":    wmean(grp["device_home_count"], grp["WT"]),
        "device_use_all":     wmean(grp["device_use_count"],  grp["WT"]),
        "skill_all":          wmean(grp["skill_total"],        grp["WT"]),
        "safety_all":         wmean(grp["safety_total"],       grp["WT"]),
        "internet_freq_rate": wprop(grp["internet_active"],    grp["WT"]),
    })
df_all_pop = pd.DataFrame(rows)


# --- 격차 산출 함수 ---
def calc_gap(data, var_name, group_var, val_a, val_b):
    agg = (
        data.groupby(["SQ1", group_var])
        .apply(lambda g: wmean(g[var_name], g["WT"]))
        .reset_index(name="val")
    )
    wide = agg.pivot(index="SQ1", columns=group_var, values="val").reset_index()
    wide["gap"] = wide[val_a] - wide[val_b]
    return wide[["SQ1", "gap"]]


gap_vars  = ["device_home_count", "device_use_count", "skill_total", "safety_total"]
gap_names = ["device_home", "device_use", "skill", "safety"]

# 남녀 격차 (남=1 - 여=2)
df_gender_gaps = df_all_pop[["SQ1"]].copy()
for var, name in zip(gap_vars, gap_names):
    g = calc_gap(sav, var, "SQ2", 1, 2).rename(columns={"gap": f"{name}_gender_gap"})
    df_gender_gaps = df_gender_gaps.merge(g, on="SQ1", how="left")

# 연령 격차 (65세 미만=0 - 65세 이상=1)
df_age_gaps = df_all_pop[["SQ1"]].copy()
for var, name in zip(gap_vars, gap_names):
    g = calc_gap(sav, var, "age_group", 0, 1).rename(columns={"gap": f"{name}_age_gap"})
    df_age_gaps = df_age_gaps.merge(g, on="SQ1", how="left")

# 설문 데이터 통합
df_survey = (
    df_all_pop
    .merge(df_gender_gaps, on="SQ1", how="left")
    .merge(df_age_gaps,    on="SQ1", how="left")
    .merge(gu_codes[["sq1_code", "district_code"]], left_on="SQ1", right_on="sq1_code", how="left")
    .drop(columns=["SQ1", "sq1_code"])
)

print("=== PART 3 완료: 디지털역량 2023 ===")


# ============================================================
# PART 4: 전체 병합 + 반올림 + 저장
# ============================================================

df_final = (
    df_cq
    .merge(df_afu, left_on="district_code", right_on="SIGUNGU_CD", how="left")
    .drop(columns=["SIGUNGU_CD"])
    .merge(df_survey, on="district_code", how="left")
)

numeric_cols = df_final.select_dtypes(include="number").columns.difference(["district_code"])
df_final[numeric_cols] = df_final[numeric_cols].round(3)

print(f"\n=== 최종 결과 ===")
print(f"행: {len(df_final)} / 열: {len(df_final.columns)}")
print("열 이름:")
print("\n".join(df_final.columns.tolist()))

out_dir = OUT
out_dir.mkdir(parents=True, exist_ok=True)
df_final.to_csv(out_dir / "seoul_umc_indicators.csv", index=False, encoding="utf-8-sig")
print(f"\n저장 완료: {out_dir / 'seoul_umc_indicators.csv'}")
print(df_final.to_string())
