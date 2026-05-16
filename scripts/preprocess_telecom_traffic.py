# -*- coding: utf-8 -*-
"""
통신정보 전처리 - 자치구별 연평균 지표 산출 (2023, 2024)
=====================================================

입력: SKT 통신정보 월별 xlsx (행정동 x 성별 x 연령대)
출력: telecom_by_district_{year}.csv (자치구별 인구가중평균)

추출 지표 (컬럼 인덱스, 0-based):
  [37] 최근 3개월 내 요금 연체 비율 (%) -> delinq_rate     [Affordability]
  [59] 데이터 사용량 (GB/인)            -> mobile_data_usage [Available for Use]
  [104] 금융 이용일수 평균              -+
  [109] 쇼핑 이용일수 평균               |-> online_service_days [Available for Use]
  [114] 동영상/방송 이용일수 평균        |   (4개 합산)
  [129] 배달 이용일수 평균              -+

집계 방법:
  1. 월별 파일 로드 -> 행정동x성별x연령대 행
  2. 자치구별 인구가중평균: sum(value * pop) / sum(pop)
  3. 12개월 평균 -> 연평균

참고:
  - ITU IDI (2023b, p.15): "Mobile broadband traffic per subscription (GB)"
  - SKT 단일 통신사 데이터 -> 한계점으로 명시 (KT/LGU+ 미포함)
  - 행정동코드 앞 5자리 = 자치구코드 (11010, 11020, ...)
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# -- 경로 --
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# 통신정보 폴더 자동 탐색
TELECOM_DIR = None
for f in os.listdir(RAW):
    full = RAW / f
    if full.is_dir():
        contents = os.listdir(full)
        if any('29' in c and '.xlsx' in c for c in contents):
            TELECOM_DIR = full
            break

if TELECOM_DIR is None:
    raise FileNotFoundError("통신정보 폴더를 찾을 수 없습니다")

print(f"통신정보 폴더: {TELECOM_DIR}")

# -- 추출할 컬럼 (0-based index) --
COL_IDX = {
    'pop':                5,   # 총인구수 (가중치)
    'delinq_rate':       37,   # 최근 3개월 내 요금 연체 비율
    'mobile_data_usage': 59,   # 데이터 사용량 (GB)
    'svc_finance':      104,   # 금융 이용일수
    'svc_shopping':     109,   # 쇼핑 이용일수
    'svc_video':        114,   # 동영상/방송 이용일수
    'svc_delivery':     129,   # 배달 이용일수
}


def load_and_aggregate_monthly(filepath):
    """월별 파일 1개 -> 자치구별 인구가중평균"""
    df = pd.read_excel(filepath, header=0)

    # 컬럼 인덱스로 추출 (인코딩 무관)
    data = pd.DataFrame()
    data['dong_code'] = df.iloc[:, 0]   # 행정동코드
    data['district_code'] = data['dong_code'].astype(str).str[:5]  # 앞 5자리 = 자치구
    data['pop'] = pd.to_numeric(df.iloc[:, COL_IDX['pop']], errors='coerce').fillna(0)

    for name, idx in COL_IDX.items():
        if name == 'pop':
            continue
        data[name] = pd.to_numeric(df.iloc[:, idx], errors='coerce').fillna(0)

    # 자치구별 인구가중평균
    result = {}
    for district, group in data.groupby('district_code'):
        total_pop = group['pop'].sum()
        row = {'district_code': district, 'pop_total': total_pop}
        for name in COL_IDX:
            if name == 'pop':
                continue
            if total_pop > 0:
                row[name] = (group[name] * group['pop']).sum() / total_pop
            else:
                row[name] = 0
        result[district] = row

    return pd.DataFrame(result.values())


def process_year(year):
    """특정 연도의 12개월 파일 -> 연평균 자치구별 지표"""
    files = sorted([
        f for f in os.listdir(TELECOM_DIR)
        if f.endswith('.xlsx') and f.startswith(str(year))
    ])

    if len(files) == 0:
        print(f"  {year}년 파일 없음")
        return None

    print(f"\n  {year}년: {len(files)}개 월별 파일 처리...")

    monthly_dfs = []
    for f in files:
        filepath = TELECOM_DIR / f
        monthly = load_and_aggregate_monthly(filepath)
        monthly_dfs.append(monthly)
        print(f"    {f} -> {len(monthly)} 자치구")

    # 12개월 평균
    all_months = pd.concat(monthly_dfs, ignore_index=True)
    annual = all_months.groupby('district_code').agg({
        'pop_total': 'mean',
        'delinq_rate': 'mean',
        'mobile_data_usage': 'mean',
        'svc_finance': 'mean',
        'svc_shopping': 'mean',
        'svc_video': 'mean',
        'svc_delivery': 'mean',
    }).reset_index()

    # 온라인 서비스 이용일수 합산 (금융 + 쇼핑 + 동영상 + 배달)
    annual['online_service_days'] = (
        annual['svc_finance'] + annual['svc_shopping'] +
        annual['svc_video'] + annual['svc_delivery']
    )

    annual['year'] = year

    return annual


# -- 실행 --
print("=" * 60)
print("통신정보 전처리 시작")
print("=" * 60)

results = {}
for year in [2023, 2024]:
    df = process_year(year)
    if df is not None:
        results[year] = df

        # 서울 25개 자치구만 필터 (11로 시작)
        df = df[df['district_code'].str.startswith('11')].copy()

        # 요약 출력
        print(f"\n  {year}년 자치구별 요약:")
        print(f"    자치구 수: {len(df)}")
        print(f"    연체율 범위:       {df['delinq_rate'].min():.2f} ~ {df['delinq_rate'].max():.2f} %")
        print(f"    데이터사용량 범위:  {df['mobile_data_usage'].min():.2f} ~ {df['mobile_data_usage'].max():.2f} GB")
        print(f"    온라인서비스일수:   {df['online_service_days'].min():.1f} ~ {df['online_service_days'].max():.1f} 일")

        # 저장
        outpath = OUT / f"telecom_by_district_{year}.csv"
        df.to_csv(outpath, index=False, encoding='utf-8-sig')
        print(f"    저장: {outpath}")

# 2023-2024 통합본도 저장
if 2023 in results and 2024 in results:
    combined = pd.concat([results[2023], results[2024]], ignore_index=True)
    combined = combined[combined['district_code'].str.startswith('11')]
    combined.to_csv(OUT / "telecom_by_district_combined.csv", index=False, encoding='utf-8-sig')
    print(f"\n통합본 저장: {OUT / 'telecom_by_district_combined.csv'}")

    # 연도별 변화 출력
    df23 = results[2023][results[2023]['district_code'].str.startswith('11')]
    df24 = results[2024][results[2024]['district_code'].str.startswith('11')]
    print("\n  연도별 변화 (전체 평균):")
    for col in ['delinq_rate', 'mobile_data_usage', 'online_service_days']:
        v23 = df23[col].mean()
        v24 = df24[col].mean()
        pct = (v24 - v23) / v23 * 100
        print(f"    {col}: {v23:.2f} -> {v24:.2f} ({pct:+.1f}%)")

print("\n전처리 완료!")
