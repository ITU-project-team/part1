# -*- coding: utf-8 -*-
"""
생활인구 전처리 - 자치구별 주간 생활인구 산출 (2023, 2024)
=========================================================

입력: LOCAL_PEOPLE_YYYYMM.zip (월별 ZIP, 내부 일별 CSV)
      각 CSV: 집계구 x 시간대(0-23) x 연령대별 생활인구

출력: C:/woo/data/UMC/processed/living_pop_by_district.csv
      district_code, living_pop_daytime, year

집계 방법:
  1. 월별 1일자 파일만 사용 (대표일)
  2. 주간 시간대 (09-18시, 10시간) 필터
  3. 집계구 -> 자치구 집계 (행정동코드 앞 5자리)
  4. 시간대별 총생활인구 합산 -> 10시간 평균 = 주간 생활인구
  5. 12개월 평균 -> 연평균 주간 생활인구

주간 생활인구를 사용하는 이유:
  - 기지국 밀도 = 기지국 수 / (생활인구 / 1000)
  - 주민등록인구는 '거주지' 기반이므로 실제 통신 수요를 반영하지 못함
  - 주간(09-18시) 생활인구는 실제 해당 자치구에서 활동하는 인구를 반영
  - 예: 강남구는 주민등록인구 54만이지만 주간 생활인구 100만+ (유입)
       노원구는 주민등록인구 52만이지만 주간 생활인구 40만 (유출)
  - 기지국은 실제 통신 수요에 맞춰 배치되므로, 생활인구 대비 밀도가 적절

참고:
  - 서울 생활인구 데이터 출처: 서울열린데이터광장
  - 집계구(census block) 단위 -> 행정동코드 앞 5자리 = 자치구코드
"""

import os
import zipfile
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# -- 경로 --
RAW = Path(r"C:\woo\data\UMC\raw\생활인구")
OUT = Path(r"C:\woo\data\UMC\processed")
OUT.mkdir(parents=True, exist_ok=True)

# -- 주간 시간대 정의 --
DAYTIME_HOURS = list(range(9, 19))  # 09:00 ~ 18:00 (10시간)


def process_one_day(zip_path, target_date_str):
    """
    ZIP 내 특정 일자 CSV -> 자치구별 주간 생활인구

    Parameters:
        zip_path: ZIP 파일 경로
        target_date_str: 'YYYYMMDD' 형식 (예: '20230101')

    Returns:
        DataFrame: district_code, living_pop_daytime
    """
    csv_name = f"LOCAL_PEOPLE_{target_date_str}.csv"

    with zipfile.ZipFile(zip_path) as zf:
        available = [f.filename for f in zf.infolist()]

        if csv_name not in available:
            # 1일 파일이 없으면 가장 빠른 날짜 사용
            available_sorted = sorted(available)
            csv_name = available_sorted[0]
            print(f"    {target_date_str} 없음 -> {csv_name} 사용")

        with zf.open(csv_name) as f:
            df = pd.read_csv(f, encoding='cp949')

    # 컬럼 인덱스 기반 (인코딩 무관)
    # [0] 기준일ID, [1] 시간구분, [2] 행정동코드, [3] 집계구코드, [4] 총생활인구수

    # 주간 시간대 필터
    df_daytime = df[df.iloc[:, 1].isin(DAYTIME_HOURS)].copy()

    # 자치구코드 추출 (행정동코드 앞 5자리)
    df_daytime['district_code'] = df_daytime.iloc[:, 2].astype(str).str[:5]

    # 시간대별 자치구별 총생활인구 합산 (집계구 -> 자치구)
    hourly_district = df_daytime.groupby(['district_code', df_daytime.iloc[:, 1]]).agg(
        pop=pd.NamedAgg(column=df_daytime.columns[4], aggfunc='sum')
    ).reset_index()

    # 자치구별 주간 평균 (10시간 평균)
    result = hourly_district.groupby('district_code')['pop'].mean().reset_index()
    result.columns = ['district_code', 'living_pop_daytime']

    return result


def process_year(year):
    """특정 연도의 12개월 1일 데이터 -> 연평균 주간 생활인구"""
    monthly_results = []

    for month in range(1, 13):
        ym = f"{year}{month:02d}"
        zip_name = f"LOCAL_PEOPLE_{ym}.zip"
        zip_path = RAW / zip_name

        if not zip_path.exists():
            print(f"  {zip_name} 없음 - 건너뜀")
            continue

        target_date = f"{ym}01"  # 매월 1일
        print(f"  {zip_name} -> {target_date}...")

        monthly = process_one_day(zip_path, target_date)
        monthly['month'] = month
        monthly_results.append(monthly)

    if not monthly_results:
        return None

    # 12개월 평균
    all_months = pd.concat(monthly_results, ignore_index=True)
    annual = all_months.groupby('district_code')['living_pop_daytime'].mean().reset_index()
    annual['year'] = year

    return annual


# -- 실행 --
print("=" * 60)
print("생활인구 전처리 시작")
print(f"주간 시간대: {DAYTIME_HOURS[0]}시 ~ {DAYTIME_HOURS[-1]}시")
print("=" * 60)

results = []
for year in [2023, 2024]:
    print(f"\n{'='*40}")
    print(f"{year}년 처리 중...")
    print(f"{'='*40}")

    df = process_year(year)
    if df is not None:
        results.append(df)

        # 서울 25구 필터 (11로 시작)
        seoul = df[df['district_code'].str.startswith('11')].copy()

        print(f"\n  {year}년 요약:")
        print(f"    자치구 수: {len(seoul)}")
        print(f"    주간 생활인구 범위: {seoul['living_pop_daytime'].min():,.0f} ~ {seoul['living_pop_daytime'].max():,.0f}")
        print(f"    서울 전체 주간 생활인구: {seoul['living_pop_daytime'].sum():,.0f}")

        # Top 5 / Bottom 5
        seoul_sorted = seoul.sort_values('living_pop_daytime', ascending=False)
        print(f"\n    Top 5:")
        for _, row in seoul_sorted.head(5).iterrows():
            print(f"      {row['district_code']}: {row['living_pop_daytime']:,.0f}")
        print(f"    Bottom 5:")
        for _, row in seoul_sorted.tail(5).iterrows():
            print(f"      {row['district_code']}: {row['living_pop_daytime']:,.0f}")

# 통합 저장
if results:
    combined = pd.concat(results, ignore_index=True)
    combined = combined[combined['district_code'].str.startswith('11')]

    outpath = OUT / "living_pop_by_district.csv"
    combined.to_csv(outpath, index=False, encoding='utf-8-sig')
    print(f"\n저장 완료: {outpath}")
    print(f"  행 수: {len(combined)} (25구 x {len(results)}년)")
    print(f"  컬럼: {', '.join(combined.columns)}")

    # 연도별 변화
    if len(results) == 2:
        df23 = combined[combined['year'] == 2023]
        df24 = combined[combined['year'] == 2024]
        avg23 = df23['living_pop_daytime'].mean()
        avg24 = df24['living_pop_daytime'].mean()
        pct = (avg24 - avg23) / avg23 * 100
        print(f"\n  연도별 변화 (자치구 평균):")
        print(f"    2023: {avg23:,.0f} -> 2024: {avg24:,.0f} ({pct:+.1f}%)")

print("\n전처리 완료!")
