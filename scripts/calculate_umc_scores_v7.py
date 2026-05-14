# -*- coding: utf-8 -*-
"""
UMC Score v7 - 2023/2024 2개년 산출
====================================

v6 -> v7 주요 변경:
  1. Infrastructure: 기지국 밀도(4G/5G) + CQ 다운로드 속도 (이전: DL속도+레이턴시)
  2. Available for Use: 모바일 데이터 사용량 + 온라인서비스이용일 + WiFi밀도(전체인구 천명당)
     (이전: WiFi밀도 + 인터넷이용빈도)
  3. Affordability: 연체율 + 평균소득 유지 (서울서베이 L2 사용금지 제약)
  4. Devices/Skills/Safety: 디지털역량실태조사 2023 유지 (2024 미존재)
  5. 2개년(2023/2024) 별도 산출 -> Part 3에서 연도별 L2 매칭

입력:
  - base_station_by_district.csv (전처리 완료)
  - telecom_by_district_2023.csv, _2024.csv (전처리 완료)
  - CQ_1_2023.csv, CQ_1_2024.csv (원시)
  - seoul_umc_scores.csv (v6) -> Devices, Skills, Safety, WiFi, avg_income 추출
  - 생활인구 (도착 시) -> station_density 분모 교체

출력:
  - seoul_umc_scores_v7_2023.csv
  - seoul_umc_scores_v7_2024.csv

참고:
  - ITU (2023b) IDI Methodology v3.1
  - 서울서베이는 L2 지표로 사용 금지
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── 경로 ──
RAW = Path(r"C:\woo\data\UMC\raw")
PROCESSED = Path(r"C:\woo\data\UMC\processed")
PART1 = Path(r"C:\woo\Project\umc\Analysis\Part 1")
OUT = PART1 / "output" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("UMC Score v7 산출 (2023 + 2024)")
print("=" * 70)


# ============================================================
# 1. 기지국 밀도 (Infrastructure)
# ============================================================
print("\n[1] 기지국 밀도 로드...")
bs = pd.read_csv(PROCESSED / "base_station_by_district.csv")
bs['district_code'] = bs['district_code'].astype(str)

# 생활인구 코드 크로스워크 (행정안전부 공식코드 -> 순차코드)
# 생활인구 데이터는 행정동코드 앞 5자리(11110-11740)를 사용하고,
# 나머지 데이터(v6, telecom, base_station)는 순차코드(11010-11250)를 사용
LIVING_POP_CROSSWALK = {
    '11110': '11010', '11140': '11020', '11170': '11030', '11200': '11040',
    '11215': '11050', '11230': '11060', '11260': '11070', '11290': '11080',
    '11305': '11090', '11320': '11100', '11350': '11110', '11380': '11120',
    '11410': '11130', '11440': '11140', '11470': '11150', '11500': '11160',
    '11530': '11170', '11545': '11180', '11560': '11190', '11590': '11200',
    '11620': '11210', '11650': '11220', '11680': '11230', '11710': '11240',
    '11740': '11250'
}

# 생활인구 데이터 확인
living_pop_path = PROCESSED / "living_pop_by_district.csv"
if living_pop_path.exists():
    print("  생활인구 데이터 발견 -> 인구 기반 밀도 산출")
    lp = pd.read_csv(living_pop_path)
    lp['district_code'] = lp['district_code'].astype(str)
    # 행정안전부 코드 -> 순차코드 변환
    lp['district_code'] = lp['district_code'].map(LIVING_POP_CROSSWALK)
    unmapped = lp['district_code'].isna().sum()
    if unmapped > 0:
        print(f"  경고: {unmapped}개 행이 코드 변환에 실패")
    lp = lp.dropna(subset=['district_code'])
    print(f"  생활인구 코드 변환 완료: {lp['district_code'].nunique()}개 자치구")
    USE_LIVING_POP = True
else:
    print("  생활인구 데이터 미도착 -> 면적 기반 밀도(fallback) 사용")
    USE_LIVING_POP = False

# 면적 기반 밀도 (fallback or 보조)
bs_infra = bs[['district_code', 'stations_4g', 'stations_5g', 'area_km2',
               'density_4g_per_km2', 'density_5g_per_km2']].copy()

print(f"  자치구: {len(bs_infra)}개")
print(f"  4G 밀도 범위: {bs_infra['density_4g_per_km2'].min():.0f} ~ "
      f"{bs_infra['density_4g_per_km2'].max():.0f} /km2")
print(f"  5G 밀도 범위: {bs_infra['density_5g_per_km2'].min():.0f} ~ "
      f"{bs_infra['density_5g_per_km2'].max():.0f} /km2")


# ============================================================
# 2. CQ 다운로드 속도 (Infrastructure)
# ============================================================
print("\n[2] CQ 다운로드 속도 로드...")

def load_cq(year):
    df = pd.read_csv(RAW / f"CQ_1_{year}.csv", encoding='cp949')
    sido_col = df.columns[1]
    district_col = df.columns[2]
    dl_col = df.columns[4]

    seoul = df[df[sido_col].str.contains('서울', na=False)].copy()
    agg = seoul.groupby(district_col).agg({dl_col: 'mean'}).reset_index()
    agg.columns = ['district_name_cq', 'download_speed']
    agg['year'] = year
    return agg

cq_2023 = load_cq(2023)
cq_2024 = load_cq(2024)
print(f"  2023: {len(cq_2023)}개 자치구, DL {cq_2023['download_speed'].min():.0f}~"
      f"{cq_2023['download_speed'].max():.0f} Mbps")
print(f"  2024: {len(cq_2024)}개 자치구, DL {cq_2024['download_speed'].min():.0f}~"
      f"{cq_2024['download_speed'].max():.0f} Mbps")


# ============================================================
# 3. 통신정보 (Available for Use + Affordability)
# ============================================================
print("\n[3] 통신정보 로드...")
telecom_2023 = pd.read_csv(PROCESSED / "telecom_by_district_2023.csv")
telecom_2024 = pd.read_csv(PROCESSED / "telecom_by_district_2024.csv")
telecom_2023['district_code'] = telecom_2023['district_code'].astype(str)
telecom_2024['district_code'] = telecom_2024['district_code'].astype(str)

for year, df in [(2023, telecom_2023), (2024, telecom_2024)]:
    print(f"  {year}: 연체율 {df['delinq_rate'].min():.1f}~{df['delinq_rate'].max():.1f}%, "
          f"데이터 {df['mobile_data_usage'].min():.1f}~{df['mobile_data_usage'].max():.1f} GB, "
          f"서비스 {df['online_service_days'].min():.0f}~{df['online_service_days'].max():.0f}일")


# ============================================================
# 4. 디지털역량실태조사 2023 (SAV) -> Devices, Skills, Safety
#    + v6에서 WiFi, avg_income 추출
# ============================================================
print("\n[4] 디지털역량실태조사 2023 SAV 직접 로드...")
import pyreadstat

sav, meta = pyreadstat.read_sav(str(RAW / "Seoul_digital_2023.SAV"))
print(f"  SAV shape: {sav.shape}")

# 자치구 매핑 (SQ1 -> 자치구명)
GU_LABELS = {
    1: "종로구", 2: "중구", 3: "용산구", 4: "성동구", 5: "광진구",
    6: "동대문구", 7: "중랑구", 8: "성북구", 9: "강북구", 10: "도봉구",
    11: "노원구", 12: "은평구", 13: "서대문구", 14: "마포구", 15: "양천구",
    16: "강서구", 17: "구로구", 18: "금천구", 19: "영등포구", 20: "동작구",
    21: "관악구", 22: "서초구", 23: "강남구", 24: "송파구", 25: "강동구"
}
GU_CODES = {
    1: "11010", 2: "11020", 3: "11030", 4: "11040", 5: "11050",
    6: "11060", 7: "11070", 8: "11080", 9: "11090", 10: "11100",
    11: "11110", 12: "11120", 13: "11130", 14: "11140", 15: "11150",
    16: "11160", 17: "11170", 18: "11180", 19: "11190", 20: "11200",
    21: "11210", 22: "11220", 23: "11230", 24: "11240", 25: "11250"
}

sav['gu_code'] = sav['SQ1'].astype(int)
sav['district'] = sav['gu_code'].map(GU_LABELS)
sav['district_code'] = sav['gu_code'].map(GU_CODES)
sav['wt'] = sav['WT'].astype(float)

# --- Devices (핵심 디지털 기기) ---
# Q1K1 가구보유: _1 데스크탑, _2 노트북, _5 태블릿 (core)
for v in ['Q1K1_1', 'Q1K1_2', 'Q1K1_5']:
    if v in sav.columns:
        sav[f'{v}_bin'] = ((sav[v].notna()) & (sav[v] != 9998)).astype(int)
q1k1_core = [c for c in ['Q1K1_1_bin', 'Q1K1_2_bin', 'Q1K1_5_bin'] if c in sav.columns]
sav['device_home_core'] = sav[q1k1_core].sum(axis=1)

# Q1K2 개인사용: _1 데스크탑, _2 노트북, _3 스마트폰, _7 태블릿 (core)
for v in ['Q1K2_1', 'Q1K2_2', 'Q1K2_3', 'Q1K2_7']:
    if v in sav.columns:
        sav[f'{v}_bin'] = ((sav[v].notna()) & (sav[v] != 9998)).astype(int)
q1k2_core = [c for c in ['Q1K2_1_bin', 'Q1K2_2_bin', 'Q1K2_3_bin', 'Q1K2_7_bin'] if c in sav.columns]
sav['device_use_core'] = sav[q1k2_core].sum(axis=1)

# --- Skills (Q4 + Q5B + Q6B + Q7) ---
q4_vars = [f'Q4_{i}' for i in range(1, 7)]   # 6문항 x 4점 = 24점
q5b_vars = [f'Q5B_{i}' for i in range(1, 11)] # 10문항 x 4점 = 40점
q6b_vars = [f'Q6B_{i}' for i in range(1, 8)]  # 7문항 x 4점 = 28점
q7_vars = [f'Q7_{i}' for i in range(1, 6)]    # 5문항 x 4점 = 20점

for varset, maxscore, name in [
    (q4_vars, 24, 'skill_q4'), (q5b_vars, 40, 'skill_q5b'),
    (q6b_vars, 28, 'skill_q6b'), (q7_vars, 20, 'skill_q7')
]:
    exist = [v for v in varset if v in sav.columns]
    if len(exist) == len(varset):
        sav[name] = sav[exist].astype(float).sum(axis=1) / maxscore
    else:
        print(f"  경고: {name} 변수 부족 ({len(exist)}/{len(varset)})")

# --- Safety (행동 Q10_1~7 / 인식 Q10_8~10) ---
q10_beh = [f'Q10_{i}' for i in range(1, 8)]   # 7문항 x 4점 = 28점
q10_awa = [f'Q10_{i}' for i in range(8, 11)]   # 3문항 x 4점 = 12점

beh_exist = [v for v in q10_beh if v in sav.columns]
awa_exist = [v for v in q10_awa if v in sav.columns]
sav['safety_behavior'] = sav[beh_exist].astype(float).sum(axis=1) / 28
sav['safety_awareness'] = sav[awa_exist].astype(float).sum(axis=1) / 12

# --- 자치구별 가중평균 ---
agg_cols = ['device_home_core', 'device_use_core',
            'skill_q4', 'skill_q5b', 'skill_q6b', 'skill_q7',
            'safety_behavior', 'safety_awareness']

def weighted_mean_by_district(df, cols, weight_col='wt'):
    result = {}
    for district_code, group in df.groupby('district_code'):
        row = {'district_code': district_code,
               'district': group['district'].iloc[0]}
        w = group[weight_col]
        for col in cols:
            valid = group[col].notna() & w.notna()
            if valid.sum() > 0:
                row[col] = np.average(group.loc[valid, col], weights=w[valid])
            else:
                row[col] = np.nan
        result[district_code] = row
    return pd.DataFrame(result.values())

survey_by_gu = weighted_mean_by_district(sav, agg_cols)
print(f"  자치구별 집계 완료: {len(survey_by_gu)}개")

# --- v6에서 WiFi, avg_income 추출 (행정 데이터) ---
print("  v6에서 WiFi밀도, 평균소득 추출...")
v6 = pd.read_csv(RAW / "seoul_umc_scores.csv", encoding='EUC-KR')
v6['district_code'] = v6['district_code'].astype(str)

v6_admin = v6[['district_code', 'wifi_per_1k_total', 'avg_income']].copy()

# 통합
v6_extract = survey_by_gu.merge(v6_admin, on='district_code', how='left')
print(f"  최종 추출: {len(v6_extract)}개 자치구, {len(v6_extract.columns)}개 컬럼")


# ============================================================
# 5. 자치구명-코드 매핑 (CQ는 자치구명 기준)
# ============================================================
name_code_map = v6_extract[['district_code', 'district']].copy()


# ============================================================
# 6. 연도별 통합 + UMC Score 산출
# ============================================================
print("\n[5] 연도별 UMC Score 산출...")

def normalize_pos(series):
    """Min-Max 정규화 (값이 클수록 좋은 지표)"""
    rng = series.max() - series.min()
    if rng == 0:
        return pd.Series(0.5, index=series.index)
    return (series - series.min()) / rng

def normalize_neg(series):
    """역방향 Min-Max 정규화 (값이 작을수록 좋은 지표)"""
    rng = series.max() - series.min()
    if rng == 0:
        return pd.Series(0.5, index=series.index)
    return (series.max() - series) / rng

def compute_umc_scores(year, cq_df, telecom_df):
    """연도별 UMC Score 산출"""
    print(f"\n  --- {year}년 ---")

    # 기본 프레임: v6 기존 데이터 (Devices, Skills, Safety, WiFi, avg_income)
    result = v6_extract.copy()

    # [Infrastructure] 기지국 밀도 (기지국 데이터는 연도 불변)
    if USE_LIVING_POP:
        # 생활인구 기반 밀도
        lp_year = lp[lp['year'] == year] if 'year' in lp.columns else lp
        result = result.merge(
            lp_year[['district_code', 'living_pop_daytime']],
            on='district_code', how='left'
        )
        result['station_density_4g'] = (
            bs_infra.set_index('district_code')['stations_4g'].reindex(result['district_code']).values
            / (result['living_pop_daytime'] / 1000)
        )
        result['station_density_5g'] = (
            bs_infra.set_index('district_code')['stations_5g'].reindex(result['district_code']).values
            / (result['living_pop_daytime'] / 1000)
        )
    else:
        # 면적 기반 (fallback)
        result = result.merge(
            bs_infra[['district_code', 'density_4g_per_km2', 'density_5g_per_km2']],
            on='district_code', how='left'
        )
        result.rename(columns={
            'density_4g_per_km2': 'station_density_4g',
            'density_5g_per_km2': 'station_density_5g'
        }, inplace=True)

    # [Infrastructure] CQ 다운로드 속도
    cq_merged = cq_df.merge(name_code_map, left_on='district_name_cq', right_on='district', how='left')
    result = result.merge(
        cq_merged[['district_code', 'download_speed']],
        on='district_code', how='left'
    )

    # [Available for Use] 통신정보
    result = result.merge(
        telecom_df[['district_code', 'mobile_data_usage', 'online_service_days', 'delinq_rate']],
        on='district_code', how='left',
        suffixes=('', '_telecom')
    )
    # delinq_rate는 통신정보에서 가져온 것 사용 (연도별 변동)
    if 'delinq_rate_telecom' in result.columns:
        result['delinq_rate'] = result['delinq_rate_telecom']
        result.drop(columns=['delinq_rate_telecom'], inplace=True)

    # WiFi 밀도 rename
    result.rename(columns={'wifi_per_1k_total': 'wifi_density'}, inplace=True)

    # ── 정규화 ──
    print(f"  정규화 중...")

    # Infrastructure (3개, 모두 positive)
    result['n_station_density_4g'] = normalize_pos(result['station_density_4g'])
    result['n_station_density_5g'] = normalize_pos(result['station_density_5g'])
    result['n_download_speed']     = normalize_pos(result['download_speed'])

    # Available for Use (3개, 모두 positive)
    result['n_mobile_data_usage']   = normalize_pos(result['mobile_data_usage'])
    result['n_online_service_days'] = normalize_pos(result['online_service_days'])
    result['n_wifi_density']        = normalize_pos(result['wifi_density'])

    # Affordability (2개: 소득 positive, 연체율 negative)
    result['n_avg_income']  = normalize_pos(result['avg_income'])
    result['n_delinq_rate'] = normalize_neg(result['delinq_rate'])

    # Devices (2개, positive)
    result['n_device_home_core'] = normalize_pos(result['device_home_core'])
    result['n_device_use_core']  = normalize_pos(result['device_use_core'])

    # Skills (3-4개, positive)
    result['n_skill_q4']  = normalize_pos(result['skill_q4'])
    result['n_skill_q5b'] = normalize_pos(result['skill_q5b'])
    result['n_skill_q6b'] = normalize_pos(result['skill_q6b'])
    skill_norm_cols = ['n_skill_q4', 'n_skill_q5b', 'n_skill_q6b']
    if 'skill_q7' in result.columns:
        result['n_skill_q7'] = normalize_pos(result['skill_q7'])
        skill_norm_cols.append('n_skill_q7')

    # Safety (2개, positive)
    result['n_safety_behavior']  = normalize_pos(result['safety_behavior'])
    result['n_safety_awareness'] = normalize_pos(result['safety_awareness'])

    # ── 차원별 Score (동일 가중) ──
    result['score_Infrastructure']    = result[['n_station_density_4g', 'n_station_density_5g',
                                                 'n_download_speed']].mean(axis=1)
    result['score_Available_for_Use'] = result[['n_mobile_data_usage', 'n_online_service_days',
                                                 'n_wifi_density']].mean(axis=1)
    result['score_Affordability']     = result[['n_avg_income', 'n_delinq_rate']].mean(axis=1)
    result['score_Devices']           = result[['n_device_home_core', 'n_device_use_core']].mean(axis=1)
    result['score_Digital_Skills']    = result[skill_norm_cols].mean(axis=1)
    result['score_Safety']            = result[['n_safety_behavior', 'n_safety_awareness']].mean(axis=1)

    # 종합 UMC Score (6개 차원 동일 가중)
    dim_cols = ['score_Infrastructure', 'score_Available_for_Use', 'score_Affordability',
                'score_Devices', 'score_Digital_Skills', 'score_Safety']
    result['score_UMC'] = result[dim_cols].mean(axis=1)
    result['rank_UMC'] = result['score_UMC'].rank(ascending=False, method='min').astype(int)
    result['year'] = year

    # 반올림
    num_cols = result.select_dtypes(include=[np.number]).columns
    result[num_cols] = result[num_cols].round(3)

    # 요약 출력
    result_sorted = result.sort_values('rank_UMC')
    print(f"\n  {year}년 UMC Score 상위 5:")
    for _, row in result_sorted.head(5).iterrows():
        print(f"    {int(row['rank_UMC']):2d}위 {row['district']}: "
              f"UMC={row['score_UMC']:.3f} "
              f"(Infra={row['score_Infrastructure']:.3f}, "
              f"AFU={row['score_Available_for_Use']:.3f}, "
              f"Aff={row['score_Affordability']:.3f})")

    print(f"\n  차원별 평균: ", end='')
    for dc in dim_cols:
        print(f"{dc.replace('score_','')[:5]}={result[dc].mean():.3f}", end=' ')
    print()

    return result_sorted


# 산출
umc_2023 = compute_umc_scores(2023, cq_2023, telecom_2023)
umc_2024 = compute_umc_scores(2024, cq_2024, telecom_2024)


# ============================================================
# 7. 저장
# ============================================================
print("\n" + "=" * 70)
print("저장...")

path_2023 = OUT / "seoul_umc_scores_v7_2023.csv"
path_2024 = OUT / "seoul_umc_scores_v7_2024.csv"

umc_2023.to_csv(path_2023, index=False, encoding='utf-8-sig')
umc_2024.to_csv(path_2024, index=False, encoding='utf-8-sig')

print(f"  {path_2023}")
print(f"  {path_2024}")
print(f"  컬럼 수: {len(umc_2023.columns)}")

# 연도별 순위 변동
print("\n=== 2023 vs 2024 순위 변동 ===")
rank_compare = umc_2023[['district', 'rank_UMC', 'score_UMC']].merge(
    umc_2024[['district', 'rank_UMC', 'score_UMC']],
    on='district', suffixes=('_2023', '_2024')
)
rank_compare['rank_change'] = rank_compare['rank_UMC_2023'] - rank_compare['rank_UMC_2024']
rank_compare['score_change'] = rank_compare['score_UMC_2024'] - rank_compare['score_UMC_2023']
rank_compare = rank_compare.sort_values('rank_change', ascending=False)

print(f"\n  가장 큰 순위 상승:")
for _, row in rank_compare.head(3).iterrows():
    print(f"    {row['district']}: {int(row['rank_UMC_2023'])}위 -> "
          f"{int(row['rank_UMC_2024'])}위 ({int(row['rank_change']):+d})")

print(f"\n  가장 큰 순위 하락:")
for _, row in rank_compare.tail(3).iterrows():
    print(f"    {row['district']}: {int(row['rank_UMC_2023'])}위 -> "
          f"{int(row['rank_UMC_2024'])}위 ({int(row['rank_change']):+d})")

# Part 3용 L2 변수 추출본도 저장
for year, df in [(2023, umc_2023), (2024, umc_2024)]:
    l2_cols = ['district_code', 'district', 'year',
               'station_density_4g', 'station_density_5g', 'download_speed',
               'mobile_data_usage', 'online_service_days', 'wifi_density',
               'delinq_rate', 'avg_income',
               'device_home_core', 'device_use_core',
               'skill_q4', 'skill_q5b', 'skill_q6b',
               'safety_behavior', 'safety_awareness',
               'score_Infrastructure', 'score_Available_for_Use',
               'score_Affordability', 'score_Devices',
               'score_Digital_Skills', 'score_Safety',
               'score_UMC', 'rank_UMC']
    if 'skill_q7' in df.columns:
        l2_cols.insert(l2_cols.index('safety_behavior'), 'skill_q7')

    l2 = df[[c for c in l2_cols if c in df.columns]]
    l2_path = PROCESSED / f"umc_l2_variables_{year}.csv"
    l2.to_csv(l2_path, index=False, encoding='utf-8-sig')
    print(f"\n  Part 3 L2 변수: {l2_path}")

print("\n완료!")
