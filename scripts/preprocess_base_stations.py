"""
기지국 데이터 전처리 — 자치구별 4G/5G 기지국 밀도 산출
=======================================================

목적:
  PMS_4G.csv + base_stations_all.csv(=5G) → 자치구별 고유 기지국 수 집계

회절 특성 고려:
  - 4G (svc_form_c 18/19): 저주파(800MHz~2.6GHz), 셀 반경 1~5km, 회절 양호
    → 동일 좌표(lon,lat)의 중복 제거: 같은 타워에 다중 안테나(주파수/섹터)는
      물리적으로 동일 커버리지 포인트이므로 하나로 간주
    → 단, 통신사별 독립 인프라이므로 carrier 구분은 유지 가능 (옵션)
  - 5G (svc_form_c 43): 고주파(3.5GHz~28GHz), 셀 반경 100~500m, 회절 불량
    → 소형셀이 촘촘히 배치되므로, 좌표 중복은 적으나 동일 처리

출력:
  C:/woo/data/UMC/processed/base_station_by_district.csv
  - district_code, district_name
  - stations_4g (고유 위치 수), stations_5g (고유 위치 수)
  - stations_4g_by_carrier (SKT/KT/LGU+ 각각)
  - stations_5g_by_carrier
  - area_km2

생활인구 도착 시:
  → calculate_umc_scores_v7.py에서 station_density = stations / (living_pop / 1000)
  → 생활인구 없으면 fallback: stations / area_km2

참고:
  - ITU IDI (2023b, p.14): "Population covered by at least a 4G/LTE mobile network (%)"
  - 서울은 4G 100% 커버리지이므로, 커버리지율 대신 밀도가 변별력 있음
  - 기지국 수집일: 2026-03-16 (spectrummap.kr). 2023~2024 대비 급변 없음 가정.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── 경로 ──
BASE = Path(r"C:\woo\data\UMC\raw\base_station")
GIS  = Path(r"C:\woo\data\UMC\raw\gis\Seoul\Seoul.shp")
OUT  = Path(r"C:\woo\data\UMC\processed")
OUT.mkdir(parents=True, exist_ok=True)

# ── 1. 데이터 로드 ──
print("1. 데이터 로드...")
df_4g = pd.read_csv(BASE / "PMS_4G.csv")
df_5g = pd.read_csv(BASE / "base_stations_all.csv")  # 실제로 5G만 포함

print(f"   4G 원본: {len(df_4g):,}건")
print(f"   5G 원본: {len(df_5g):,}건")

# ── 2. 회절 특성 고려한 중복 제거 ──
print("\n2. 동일 위치 중복 제거 (회절 특성 반영)...")

# 4G: 동일 좌표의 다중 안테나는 같은 타워 → 고유 위치만 남김
# (lon, lat) 기준 deduplicate — carrier 무관하게 물리적 위치 단위
# 이유: 4G 저주파(800MHz~2.6GHz)는 회절이 좋아 하나의 타워가 넓은 영역 커버
# 같은 좌표에서 SKT/KT/LGU+ 안테나가 있어도 물리적 커버리지 포인트는 하나
df_4g_dedup = df_4g.drop_duplicates(subset=['longitude', 'latitude'])
print(f"   4G 고유 위치: {len(df_4g_dedup):,}건 (원본 {len(df_4g):,} → {len(df_4g_dedup)/len(df_4g)*100:.1f}% 보존)")

# 4G carrier별 고유 위치도 산출 (보조 지표: 인프라 경쟁 다양성)
df_4g_by_carrier = df_4g.drop_duplicates(subset=['longitude', 'latitude', 'carrier'])
print(f"   4G 고유 (위치×통신사): {len(df_4g_by_carrier):,}건")

# 5G: 고주파(3.5GHz+)는 회절 불량 → 각 소형셀이 독립적 커버리지
# 동일 좌표 중복만 제거 (5G는 공유 타워가 적어 영향 미미)
df_5g_dedup = df_5g.drop_duplicates(subset=['longitude', 'latitude'])
print(f"   5G 고유 위치: {len(df_5g_dedup):,}건 (원본 {len(df_5g):,} → {len(df_5g_dedup)/len(df_5g)*100:.1f}% 보존)")

df_5g_by_carrier = df_5g.drop_duplicates(subset=['longitude', 'latitude', 'carrier'])
print(f"   5G 고유 (위치×통신사): {len(df_5g_by_carrier):,}건")

# ── 3. GeoDataFrame 변환 + 서울 Shapefile 공간 조인 ──
print("\n3. 공간 조인 (기지국 → 자치구)...")
seoul = gpd.read_file(GIS, encoding='cp949')

# 서울 shapefile: EPSG:4326 (WGS84)
# 면적 산출: 투영 좌표계(EPSG:5179, Korea TM)로 변환
seoul_proj = seoul.to_crs('EPSG:5179')
seoul['area_km2'] = seoul_proj.geometry.area / 1e6

def spatial_join_count(df, seoul_gdf, label):
    """기지국 좌표를 자치구에 매핑하여 자치구별 카운트"""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs='EPSG:4326'
    )
    joined = gpd.sjoin(gdf, seoul_gdf[['SIGUNGU_CD', 'geometry']],
                        how='inner', predicate='within')
    counts = joined.groupby('SIGUNGU_CD').size().reset_index(name=label)
    return counts

def spatial_join_carrier_count(df, seoul_gdf, gen_label):
    """통신사별 기지국 카운트"""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs='EPSG:4326'
    )
    joined = gpd.sjoin(gdf, seoul_gdf[['SIGUNGU_CD', 'geometry']],
                        how='inner', predicate='within')
    pivot = joined.groupby(['SIGUNGU_CD', 'carrier']).size().unstack(fill_value=0)
    pivot.columns = [f"{gen_label}_{c}" for c in pivot.columns]
    return pivot.reset_index()

# 고유 위치 기준 (메인 지표)
count_4g = spatial_join_count(df_4g_dedup, seoul, 'stations_4g')
count_5g = spatial_join_count(df_5g_dedup, seoul, 'stations_5g')

# 통신사별 (보조 지표)
carrier_4g = spatial_join_carrier_count(df_4g_by_carrier, seoul, '4g')
carrier_5g = spatial_join_carrier_count(df_5g_by_carrier, seoul, '5g')

print(f"   4G: {count_4g['stations_4g'].sum():,}개 기지국이 25개 자치구에 매핑")
print(f"   5G: {count_5g['stations_5g'].sum():,}개 기지국이 25개 자치구에 매핑")

# ── 4. 병합 ──
print("\n4. 결과 병합...")
result = seoul[['SIGUNGU_CD', 'SIGUNGU_NM', 'area_km2']].copy()
result = result.rename(columns={'SIGUNGU_CD': 'district_code', 'SIGUNGU_NM': 'district_name'})

result = result.merge(count_4g, left_on='district_code', right_on='SIGUNGU_CD', how='left')
if 'SIGUNGU_CD' in result.columns:
    result = result.drop(columns=['SIGUNGU_CD'])

result = result.merge(count_5g, left_on='district_code', right_on='SIGUNGU_CD', how='left')
if 'SIGUNGU_CD' in result.columns:
    result = result.drop(columns=['SIGUNGU_CD'])

result = result.merge(carrier_4g, left_on='district_code', right_on='SIGUNGU_CD', how='left')
if 'SIGUNGU_CD' in result.columns:
    result = result.drop(columns=['SIGUNGU_CD'])

result = result.merge(carrier_5g, left_on='district_code', right_on='SIGUNGU_CD', how='left')
if 'SIGUNGU_CD' in result.columns:
    result = result.drop(columns=['SIGUNGU_CD'])

result = result.fillna(0)

# 면적 기반 밀도 (fallback — 생활인구 도착 전 사용)
result['density_4g_per_km2'] = result['stations_4g'] / result['area_km2']
result['density_5g_per_km2'] = result['stations_5g'] / result['area_km2']

# ── 5. 요약 출력 ──
print("\n5. 자치구별 기지국 현황:")
summary = result[['district_code', 'district_name', 'area_km2',
                   'stations_4g', 'stations_5g',
                   'density_4g_per_km2', 'density_5g_per_km2']].copy()
summary['density_4g_per_km2'] = summary['density_4g_per_km2'].round(1)
summary['density_5g_per_km2'] = summary['density_5g_per_km2'].round(1)
print(summary.to_string(index=False))

print(f"\n   전체 4G: {int(result['stations_4g'].sum()):,}개 / 5G: {int(result['stations_5g'].sum()):,}개")
print(f"   4G 밀도 범위: {result['density_4g_per_km2'].min():.0f} ~ {result['density_4g_per_km2'].max():.0f} /km²")
print(f"   5G 밀도 범위: {result['density_5g_per_km2'].min():.0f} ~ {result['density_5g_per_km2'].max():.0f} /km²")

# ── 6. 저장 ──
outpath = OUT / "base_station_by_district.csv"
result.to_csv(outpath, index=False, encoding='utf-8-sig')
print(f"\n저장 완료: {outpath}")
print(f"   컬럼: {', '.join(result.columns)}")
