# -*- coding: utf-8 -*-
"""
UMC v7 시각화 - 연도별 개별 산출
================================

각 연도(2023, 2024)에 대해 독립적으로 결과물 생성.
연도 간 비교 차트는 포함하지 않음.

산출물 (각 연도별):
  figures/{year}/
    fig_01_heatmap_v7.png         - 차원별 점수 히트맵
    fig_02_bar_umc_v7.png         - UMC 종합 점수 바차트
    fig_03_bar_stacked_v7.png     - 차원별 기여 분해
    fig_04_radar_top_bottom_v7.png - Top3/Bottom3 레이더 차트
    fig_05_map_umc_v7.png         - UMC 종합 지도
    fig_06_map_dimensions_v7.png  - 차원별 지도
  tables/{year}/
    seoul_umc_v7_summary.csv      - 요약 통계
    seoul_umc_v7_descriptives.csv - 기술통계

  tables/
    codebook_umc_v7.csv           - 코드북 (공통)

인코딩: EUC-KR (Excel 바로 열기 가능)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import warnings
warnings.filterwarnings('ignore')

try:
    import geopandas as gpd
    HAS_GEO = True
except ImportError:
    HAS_GEO = False

from pathlib import Path

# ── 경로 ──
PART1 = Path(r"C:\woo\Project\umc\Analysis\Part 1")
RESULT = PART1 / "output" / "tables"
OUT = PART1 / "output"
GIS_PATH = Path(r"C:\woo\data\UMC\raw\gis\Seoul\Seoul.shp")

CSV_ENCODING = 'euc-kr'

# ── Font (English labels) ──
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.unicode_minus'] = False

# ── District name mapping (English) ──
GU_NAME = {
    11010: 'Jongno-gu', 11020: 'Jung-gu', 11030: 'Yongsan-gu',
    11040: 'Seongdong-gu', 11050: 'Gwangjin-gu', 11060: 'Dongdaemun-gu',
    11070: 'Jungnang-gu', 11080: 'Seongbuk-gu', 11090: 'Gangbuk-gu',
    11100: 'Dobong-gu', 11110: 'Nowon-gu', 11120: 'Eunpyeong-gu',
    11130: 'Seodaemun-gu', 11140: 'Mapo-gu', 11150: 'Yangcheon-gu',
    11160: 'Gangseo-gu', 11170: 'Guro-gu', 11180: 'Geumcheon-gu',
    11190: 'Yeongdeungpo-gu', 11200: 'Dongjak-gu', 11210: 'Gwanak-gu',
    11220: 'Seocho-gu', 11230: 'Gangnam-gu', 11240: 'Songpa-gu',
    11250: 'Gangdong-gu'
}

# GIS map labels (shorter, no -gu suffix)
GU_SHORT = {
    11010: 'Jongno', 11020: 'Jung', 11030: 'Yongsan',
    11040: 'Seongdong', 11050: 'Gwangjin', 11060: 'Dongdaemun',
    11070: 'Jungnang', 11080: 'Seongbuk', 11090: 'Gangbuk',
    11100: 'Dobong', 11110: 'Nowon', 11120: 'Eunpyeong',
    11130: 'Seodaemun', 11140: 'Mapo', 11150: 'Yangcheon',
    11160: 'Gangseo', 11170: 'Guro', 11180: 'Geumcheon',
    11190: 'Yeongdeungpo', 11200: 'Dongjak', 11210: 'Gwanak',
    11220: 'Seocho', 11230: 'Gangnam', 11240: 'Songpa',
    11250: 'Gangdong'
}

dim_cols = ['score_Infrastructure', 'score_Available_for_Use', 'score_Affordability',
            'score_Devices', 'score_Digital_Skills', 'score_Safety']
dim_labels = ['Connectivity', 'Available\nfor Use', 'Affordability',
              'Devices', 'Digital\nSkills', 'Safety']
dim_short = ['Connect', 'AFU', 'Afford', 'Device', 'Skill', 'Safety']

# ── GIS 데이터 로드 (한 번만) ──
seoul_gis = None
if HAS_GEO and GIS_PATH.exists():
    seoul_gis = gpd.read_file(str(GIS_PATH), encoding='cp949')
    # Shapefile already uses sequential codes (11010-11250) in SIGUNGU_CD
    seoul_gis['district_code'] = seoul_gis['SIGUNGU_CD'].astype(int)
    seoul_gis['district_name'] = seoul_gis['district_code'].map(GU_NAME)
    seoul_gis['district_short'] = seoul_gis['district_code'].map(GU_SHORT)


# ================================================================
# 연도별 산출 함수
# ================================================================
def generate_year_outputs(year: int):
    """단일 연도의 모든 결과물 산출"""
    print(f"\n{'='*60}")
    print(f"  {year}년 결과물 산출")
    print(f"{'='*60}")

    # -- 디렉토리 --
    fig_dir = OUT / "figures" / str(year)
    tbl_dir = OUT / "tables" / str(year)
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)

    # -- 데이터 로드 --
    umc = pd.read_csv(RESULT / f"seoul_umc_scores_v7_{year}.csv")
    umc['district_name'] = umc['district_code'].map(GU_NAME)

    # ==============================================================
    # Fig 01: Heatmap
    # ==============================================================
    print("\n  [1] 히트맵...")
    umc_sorted = umc.sort_values('score_UMC', ascending=True)
    data = umc_sorted[dim_cols].values
    districts = umc_sorted['district_name'].values

    fig, ax = plt.subplots(figsize=(10, 10))
    im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    ax.set_yticks(range(len(districts)))
    ax.set_yticklabels(districts, fontsize=10)
    ax.set_xticks(range(len(dim_short)))
    ax.set_xticklabels(dim_short, fontsize=10, rotation=45, ha='right')
    ax.set_title(f'{year} UMC Dimension Scores', fontsize=14, fontweight='bold')

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            color = 'white' if val < 0.3 or val > 0.7 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=8, color=color)

    fig.colorbar(im, ax=ax, shrink=0.6, label='Score (0-1)')
    plt.tight_layout()
    plt.savefig(fig_dir / "fig_01_heatmap_v7.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    fig_01_heatmap_v7.png")

    # ==============================================================
    # Fig 02: UMC Bar Chart
    # ==============================================================
    print("  [2] UMC 종합 바차트...")
    umc_sorted = umc.sort_values('score_UMC', ascending=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(umc_sorted))
    colors = plt.cm.RdYlGn(umc_sorted['score_UMC'].values / umc_sorted['score_UMC'].max())

    bars = ax.barh(y, umc_sorted['score_UMC'], color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(umc_sorted['district_name'], fontsize=10)
    ax.set_xlabel('UMC Score', fontsize=11)
    ax.set_title(f'{year} UMC Composite Score by District', fontsize=14, fontweight='bold')
    ax.set_xlim(0, 0.85)

    for i, v in enumerate(umc_sorted['score_UMC']):
        ax.text(v + 0.01, i, f'{v:.3f}', va='center', fontsize=8)

    plt.tight_layout()
    plt.savefig(fig_dir / "fig_02_bar_umc_v7.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    fig_02_bar_umc_v7.png")

    # ==============================================================
    # Fig 03: Stacked Bar (차원 기여)
    # ==============================================================
    print("  [3] 차원별 기여 분해...")
    umc_sorted = umc.sort_values('score_UMC', ascending=True)
    districts = umc_sorted['district_name'].values
    y = np.arange(len(districts))
    dim_colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
    left = np.zeros(len(districts))

    fig, ax = plt.subplots(figsize=(10, 8))
    for i, (col, label) in enumerate(zip(dim_cols, dim_short)):
        vals = umc_sorted[col].values / 6
        ax.barh(y, vals, left=left, color=dim_colors[i], label=label,
                edgecolor='white', linewidth=0.3)
        left += vals

    ax.set_yticks(y)
    ax.set_yticklabels(districts, fontsize=9)
    ax.set_xlabel('Contribution to UMC Score', fontsize=10)
    ax.set_title(f'{year} UMC Score Decomposition by Dimension', fontsize=13, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9, ncol=2)

    plt.tight_layout()
    plt.savefig(fig_dir / "fig_03_bar_stacked_v7.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    fig_03_bar_stacked_v7.png")

    # ==============================================================
    # Fig 04: Radar Chart (Top 3 vs Bottom 3)
    # ==============================================================
    print("  [4] 레이더 차트...")
    angles = np.linspace(0, 2 * np.pi, len(dim_cols), endpoint=False).tolist()
    angles += angles[:1]

    top3 = umc.nlargest(3, 'score_UMC')
    bot3 = umc.nsmallest(3, 'score_UMC')

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    for _, row in top3.iterrows():
        values = row[dim_cols].values.tolist() + [row[dim_cols].values[0]]
        ax.plot(angles, values, 'o-', linewidth=1.8, markersize=5,
                label=f"{row['district_name']} ({row['score_UMC']:.3f})")
        ax.fill(angles, values, alpha=0.05)

    for _, row in bot3.iterrows():
        values = row[dim_cols].values.tolist() + [row[dim_cols].values[0]]
        ax.plot(angles, values, 's--', linewidth=1.8, markersize=5,
                label=f"{row['district_name']} ({row['score_UMC']:.3f})")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dim_short, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_title(f'{year} Top 3 vs Bottom 3', fontsize=13, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=9)

    plt.tight_layout()
    plt.savefig(fig_dir / "fig_04_radar_top_bottom_v7.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    fig_04_radar_top_bottom_v7.png")

    # ==============================================================
    # Fig 05 & 06: GIS Maps
    # ==============================================================
    if seoul_gis is not None:
        gdf = seoul_gis.merge(
            umc[['district_code', 'score_UMC'] + dim_cols],
            on='district_code', how='left'
        )

        # Fig 05: UMC 종합 지도
        print("  [5] GIS 지도 (UMC 종합)...")
        fig, ax = plt.subplots(figsize=(10, 10))
        gdf.plot(column='score_UMC', cmap='RdYlGn', linewidth=0.5,
                 edgecolor='black', ax=ax, legend=False, vmin=0.25, vmax=0.75)
        for _, row in gdf.iterrows():
            centroid = row.geometry.centroid
            short = row.get('district_short', row['district_name'])
            if pd.notna(short):
                ax.text(centroid.x, centroid.y, str(short),
                        fontsize=6, ha='center', va='center', fontweight='bold')
        ax.set_title(f'{year} UMC Score', fontsize=14, fontweight='bold')
        ax.axis('off')

        sm = plt.cm.ScalarMappable(cmap='RdYlGn', norm=plt.Normalize(vmin=0.25, vmax=0.75))
        sm._A = []
        fig.colorbar(sm, ax=ax, shrink=0.5, label='UMC Score')
        plt.tight_layout()
        plt.savefig(fig_dir / "fig_05_map_umc_v7.png", dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    fig_05_map_umc_v7.png")

        # Fig 06: 차원별 지도
        print("  [6] GIS 지도 (차원별)...")
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        axes_flat = axes.flatten()

        for idx, (col, label) in enumerate(zip(dim_cols, dim_labels)):
            a = axes_flat[idx]
            gdf.plot(column=col, cmap='RdYlGn', linewidth=0.5,
                     edgecolor='black', ax=a, legend=False, vmin=0, vmax=1)
            for _, row in gdf.iterrows():
                centroid = row.geometry.centroid
                val = row[col]
                if pd.notna(val):
                    a.text(centroid.x, centroid.y, f'{val:.2f}',
                           fontsize=5, ha='center', va='center', fontweight='bold')
            a.set_title(label.replace('\n', ' '), fontsize=11, fontweight='bold')
            a.axis('off')

        sm2 = plt.cm.ScalarMappable(cmap='RdYlGn', norm=plt.Normalize(vmin=0, vmax=1))
        sm2._A = []
        fig.colorbar(sm2, ax=axes, shrink=0.4, label='Score')
        fig.suptitle(f'{year} UMC Dimensions by District', fontsize=14, fontweight='bold', y=1.01)
        plt.tight_layout()
        plt.savefig(fig_dir / "fig_06_map_dimensions_v7.png", dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    fig_06_map_dimensions_v7.png")
    else:
        print("  [5-6] GIS 시각화 건너뜀 (geopandas 또는 shapefile 없음)")

    # ==============================================================
    # Summary Table
    # ==============================================================
    print("\n  [7] 요약 테이블...")
    summary_rows = []
    for _, row in umc.iterrows():
        r = {
            'year': year,
            'district_code': row['district_code'],
            'district_name': row['district_name'],
            'score_UMC': row['score_UMC'],
        }
        for col, label in zip(dim_cols, dim_short):
            r[f'score_{label}'] = row[col]
        summary_rows.append(r)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(tbl_dir / "seoul_umc_v7_summary.csv", index=False, encoding=CSV_ENCODING)
    print(f"    seoul_umc_v7_summary.csv ({len(summary)} rows)")

    # 기술통계
    desc_rows = []
    for col, label in zip(dim_cols + ['score_UMC'], dim_short + ['UMC']):
        desc_rows.append({
            'dimension': label,
            'mean': round(umc[col].mean(), 4),
            'std': round(umc[col].std(), 4),
            'min': round(umc[col].min(), 4),
            'max': round(umc[col].max(), 4),
            'range': round(umc[col].max() - umc[col].min(), 4)
        })
    desc = pd.DataFrame(desc_rows)
    desc.to_csv(tbl_dir / "seoul_umc_v7_descriptives.csv", index=False, encoding=CSV_ENCODING)
    print(f"    seoul_umc_v7_descriptives.csv")

    print(f"\n  {year}년 완료!")
    return fig_dir, tbl_dir


# ================================================================
# 공통 코드북 생성
# ================================================================
def generate_codebook():
    """코드북 CSV (EUC-KR)"""
    print(f"\n{'='*60}")
    print("  코드북 생성 (공통)")
    print(f"{'='*60}")

    tbl_dir = OUT / "tables"
    tbl_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        ['district_code', 'District code (sequential 5-digit)', '-', '-', '11010-11250, 25 districts in Seoul', '', ''],
        ['district', 'District name', '-', '-', '', '', ''],
        ['year', 'Reference year', '-', '-', '2023 or 2024', '', ''],
        ['', '', '', '', '', '', ''],
        ['[Raw Indicators - Connectivity]', '', '', '', '', '', ''],
        ['station_density_4g', '4G base station density (living pop.)', 'Connectivity', 'Spectrum Resource Management System', 'Unique coords / (daytime living pop / 1000)', 'stations/1K pop', 'Deduplicated coords'],
        ['station_density_5g', '5G base station density (living pop.)', 'Connectivity', 'Spectrum Resource Management System', 'Unique coords / (daytime living pop / 1000)', 'stations/1K pop', 'Deduplicated coords'],
        ['download_speed', 'Avg. download speed', 'Connectivity', 'NIA Communication Quality (CQ)', 'Mean of measurement points per district (annual)', 'Mbps', 'Higher is better'],
        ['living_pop_daytime', 'Daytime living population (09-18h avg)', 'Connectivity (denominator)', 'Seoul Living Population Data', 'Monthly 1st-day daytime census block sum -> district -> 12-month avg', 'persons', 'Denominator for station density'],
        ['', '', '', '', '', '', ''],
        ['[Raw Indicators - Available for Use]', '', '', '', '', '', ''],
        ['mobile_data_usage', 'Mobile data usage', 'Available for Use', 'SKT Telecom Data', 'Pop-weighted district avg -> 12-month avg', 'GB/person', ''],
        ['online_service_days', 'Online service usage days (4 categories)', 'Available for Use', 'SKT Telecom Data', 'Finance+Shopping+Video+Delivery pop-weighted sum', 'days/month', ''],
        ['wifi_density', 'Public WiFi per 1K total pop', 'Available for Use', 'Local Admin License Data', 'WiFi locations / total pop * 1000', 'per 1K pop', ''],
        ['', '', '', '', '', '', ''],
        ['[Raw Indicators - Affordability]', '', '', '', '', '', ''],
        ['delinq_rate', 'Telecom fee delinquency rate (3-month)', 'Affordability', 'SKT Telecom Data', 'Pop-weighted district avg -> 12-month avg', '%', 'Higher is worse (reverse-normalized)'],
        ['avg_income', 'District avg monthly income', 'Affordability', 'Seoul Commercial Analysis Service', 'District-level avg monthly income', 'KRW/month', 'Higher is better'],
        ['', '', '', '', '', '', ''],
        ['[Raw Indicators - Devices]', '', '', '', '', '', ''],
        ['device_home_core', 'Core digital devices owned at home', 'Devices', 'Seoul Digital Competency Survey 2023', 'Desktop+Laptop+Tablet ownership sum, weighted avg', 'types (0-3)', 'Excl. smartphone'],
        ['device_use_core', 'Core digital devices used personally', 'Devices', 'Seoul Digital Competency Survey 2023', 'Desktop+Laptop+Smartphone+Tablet sum, weighted avg', 'types (0-4)', 'Actual usage'],
        ['', '', '', '', '', '', ''],
        ['[Raw Indicators - Digital Skills]', '', '', '', '', '', ''],
        ['skill_q4', 'Basic smart device operation ability', 'Digital Skills', 'Seoul Digital Competency Survey 2023', 'Q4_1-6 sum(24pt)/24, weighted avg', 'ratio (0-1)', ''],
        ['skill_q5b', 'Digital service usage ability', 'Digital Skills', 'Seoul Digital Competency Survey 2023', 'Q5B_1-10 sum(40pt)/40, weighted avg', 'ratio (0-1)', ''],
        ['skill_q6b', 'Smart device activity proficiency', 'Digital Skills', 'Seoul Digital Competency Survey 2023', 'Q6B_1-7 sum(28pt)/28, weighted avg', 'ratio (0-1)', ''],
        ['skill_q7', 'Cyber activity capability', 'Digital Skills', 'Seoul Digital Competency Survey 2023', 'Q7_1-5 sum(20pt)/20, weighted avg', 'ratio (0-1)', ''],
        ['', '', '', '', '', '', ''],
        ['[Raw Indicators - Safety]', '', '', '', '', '', ''],
        ['safety_behavior', 'Digital security practice behavior', 'Safety', 'Seoul Digital Competency Survey 2023', 'Q10_1-7 sum(28pt)/28, weighted avg', 'ratio (0-1)', ''],
        ['safety_awareness', 'Digital security awareness', 'Safety', 'Seoul Digital Competency Survey 2023', 'Q10_8-10 sum(12pt)/12, weighted avg', 'ratio (0-1)', ''],
        ['', '', '', '', '', '', ''],
        ['[Normalized Indicators (n_ prefix)]', '', '', '', '', '', ''],
        ['n_station_density_4g ~ n_safety_awareness', 'Min-Max normalization of raw indicators', 'Respective', 'Computed', 'Min-Max within 25 districts', '0-1', 'delinq_rate only: reverse direction'],
        ['', '', '', '', '', '', ''],
        ['[Dimension Scores (score_ prefix)]', '', '', '', '', '', ''],
        ['score_Infrastructure', 'Connectivity dimension score', 'Connectivity', 'Computed', 'mean(n_4g_density, n_5g_density, n_dl_speed)', '0-1', 'Equal weight avg of 3 indicators'],
        ['score_Available_for_Use', 'Available for Use dimension score', 'Available for Use', 'Computed', 'mean(n_mobile_data, n_online_svc, n_wifi)', '0-1', 'Equal weight avg of 3 indicators'],
        ['score_Affordability', 'Affordability dimension score', 'Affordability', 'Computed', 'mean(n_avg_income, n_delinq_rate)', '0-1', 'Equal weight avg of 2 indicators'],
        ['score_Devices', 'Devices dimension score', 'Devices', 'Computed', 'mean(n_device_home, n_device_use)', '0-1', 'Equal weight avg of 2 indicators'],
        ['score_Digital_Skills', 'Digital Skills dimension score', 'Digital Skills', 'Computed', 'mean(n_q4, n_q5b, n_q6b, n_q7)', '0-1', 'Equal weight avg of 4 indicators'],
        ['score_Safety', 'Safety dimension score', 'Safety', 'Computed', 'mean(n_behavior, n_awareness)', '0-1', 'Equal weight avg of 2 indicators'],
        ['', '', '', '', '', '', ''],
        ['[Composite Score]', '', '', '', '', '', ''],
        ['score_UMC', 'UMC composite score', '-', 'Computed', 'mean(6 dimension scores)', '0-1', 'Equal weight avg of 6 dimensions'],
    ]

    header = ['Variable', 'Description', 'UMC Dimension', 'Data Source', 'Calculation', 'Scale/Unit', 'Note']
    cb = pd.DataFrame(rows, columns=header)
    cb.to_csv(tbl_dir / "codebook_umc_v7.csv", index=False, encoding=CSV_ENCODING)
    print(f"  codebook_umc_v7.csv (EUC-KR)")


# ================================================================
# 실행
# ================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("UMC v7 시각화 - 연도별 개별 산출")
    print("=" * 60)

    for yr in [2023, 2024]:
        generate_year_outputs(yr)

    generate_codebook()

    print(f"\n{'='*60}")
    print("전체 완료!")
    print("=" * 60)

    # 산출물 목록
    for yr in [2023, 2024]:
        fig_dir = OUT / "figures" / str(yr)
        tbl_dir = OUT / "tables" / str(yr)
        print(f"\n{yr}년 figures ({fig_dir}):")
        for f in sorted(fig_dir.glob("*.png")):
            size = f.stat().st_size / 1024
            print(f"  {f.name} ({size:.0f} KB)")
        print(f"{yr}년 tables ({tbl_dir}):")
        for f in sorted(tbl_dir.glob("*.csv")):
            print(f"  {f.name}")

    print(f"\n공통 tables ({OUT / 'tables'}):")
    for f in sorted((OUT / "tables").glob("codebook*.csv")):
        print(f"  {f.name}")
