# -*- coding: utf-8 -*-
"""
UMC Report Figures — Grayscale Academic Style
=============================================
Generates publication-ready grayscale figures for the UMC report.
All labels in English, Arial font, 300 DPI.

Output: Part 1/output/figures/report/
  fig_report_heatmap.png
  fig_report_bar_umc.png
  fig_report_bar_stacked.png
  fig_report_radar.png
  fig_report_map_umc.png
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import warnings
warnings.filterwarnings('ignore')

try:
    import geopandas as gpd
    HAS_GEO = True
except ImportError:
    HAS_GEO = False

from pathlib import Path

# ── Paths ──
ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "output" / "tables"
OUT = ROOT / "output" / "figures" / "report"
GIS_PATH = ROOT / "data" / "gis" / "Seoul" / "Seoul.shp"
OUT.mkdir(parents=True, exist_ok=True)

# ── Style ──
plt.rcParams.update({
    'font.family': 'Arial',
    'axes.unicode_minus': False,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.edgecolor': '#333333',
    'axes.labelcolor': '#222222',
    'xtick.color': '#333333',
    'ytick.color': '#333333',
    'text.color': '#222222',
})

# ── District names ──
GU_NAME = {
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
dim_short = ['Connect.', 'Avail.', 'Afford.', 'Devices', 'Skills', 'Safety']

# ── Load data (2024) ──
umc = pd.read_csv(RESULT / "seoul_umc_scores_v7_2024.csv")
umc['district_name'] = umc['district_code'].map(GU_NAME)

# Grayscale palette for 6 dimensions (light to dark)
GRAY6 = ['#E8E8E8', '#C0C0C0', '#969696', '#6E6E6E', '#484848', '#222222']
# Hatch patterns for stacked bar
HATCHES = ['', '///', '\\\\\\', 'xxx', '...', '+++']

# ================================================================
# Fig 1: Heatmap (25 districts × 6 dimensions)
# ================================================================
print("[1/5] Heatmap...")
umc_sorted = umc.sort_values('score_UMC', ascending=True)
data = umc_sorted[dim_cols].values
districts = umc_sorted['district_name'].values

fig, ax = plt.subplots(figsize=(8, 10))
im = ax.imshow(data, cmap='Greys', aspect='auto', vmin=0, vmax=1)
ax.set_yticks(range(len(districts)))
ax.set_yticklabels(districts, fontsize=9)
ax.set_xticks(range(len(dim_short)))
ax.set_xticklabels(dim_short, fontsize=9, rotation=45, ha='right')

for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        val = data[i, j]
        color = 'white' if val > 0.55 else 'black'
        ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                fontsize=7, color=color, fontweight='medium')

cbar = fig.colorbar(im, ax=ax, shrink=0.5, label='Score (0\u20131)')
cbar.ax.tick_params(labelsize=8)

ax.set_xlabel('')
ax.set_ylabel('')
plt.tight_layout()
plt.savefig(OUT / "fig_report_heatmap.png", bbox_inches='tight', facecolor='white')
plt.close()
print(f"  -> {OUT / 'fig_report_heatmap.png'}")

# ================================================================
# Fig 2: UMC Composite Score Bar Chart
# ================================================================
print("[2/5] Bar chart...")
umc_sorted = umc.sort_values('score_UMC', ascending=True)
y = np.arange(len(umc_sorted))

fig, ax = plt.subplots(figsize=(8, 9))

# Gradient grayscale based on score
norm = plt.Normalize(vmin=umc_sorted['score_UMC'].min() - 0.05,
                     vmax=umc_sorted['score_UMC'].max() + 0.05)
colors = [plt.cm.Greys(norm(v)) for v in umc_sorted['score_UMC']]

bars = ax.barh(y, umc_sorted['score_UMC'], color=colors,
               edgecolor='#555555', linewidth=0.5)
ax.set_yticks(y)
ax.set_yticklabels(umc_sorted['district_name'], fontsize=9)
ax.set_xlabel('UMC Composite Score', fontsize=10)
ax.set_xlim(0, 0.82)

# Mean line
mean_val = umc_sorted['score_UMC'].mean()
ax.axvline(mean_val, color='#444444', linestyle='--', linewidth=1, alpha=0.7)
ax.text(mean_val + 0.005, len(umc_sorted) - 0.5, f'Mean = {mean_val:.3f}',
        fontsize=8, color='#444444', va='top')

for i, v in enumerate(umc_sorted['score_UMC']):
    ax.text(v + 0.008, i, f'{v:.3f}', va='center', fontsize=7.5, color='#333333')

plt.tight_layout()
plt.savefig(OUT / "fig_report_bar_umc.png", bbox_inches='tight', facecolor='white')
plt.close()
print(f"  -> {OUT / 'fig_report_bar_umc.png'}")

# ================================================================
# Fig 3: Stacked Bar (Dimension Decomposition)
# ================================================================
print("[3/5] Stacked bar...")
umc_sorted = umc.sort_values('score_UMC', ascending=True)
districts = umc_sorted['district_name'].values
y = np.arange(len(districts))

fig, ax = plt.subplots(figsize=(9, 9))
left = np.zeros(len(districts))

for idx, (col, label, gray, hatch) in enumerate(
        zip(dim_cols, dim_short, GRAY6, HATCHES)):
    # Each dimension contributes 1/6 of total
    vals = umc_sorted[col].values / 6.0
    ax.barh(y, vals, left=left, color=gray, edgecolor='#444444',
            linewidth=0.4, hatch=hatch, label=label)
    left += vals

ax.set_yticks(y)
ax.set_yticklabels(districts, fontsize=9)
ax.set_xlabel('Contribution to UMC Composite Score', fontsize=10)
ax.set_xlim(0, 0.75)

# Legend
ax.legend(loc='lower right', fontsize=8, frameon=True, framealpha=0.9,
          edgecolor='#CCCCCC', ncol=2)

plt.tight_layout()
plt.savefig(OUT / "fig_report_bar_stacked.png", bbox_inches='tight', facecolor='white')
plt.close()
print(f"  -> {OUT / 'fig_report_bar_stacked.png'}")

# ================================================================
# Fig 4: Radar Chart (Top 3 vs Bottom 3)
# ================================================================
print("[4/5] Radar chart...")
umc_ranked = umc.sort_values('score_UMC', ascending=False)
top3 = umc_ranked.head(3)
bot3 = umc_ranked.tail(3)

categories = ['Connectivity', 'Available\nfor Use', 'Affordability',
              'Devices', 'Digital\nSkills', 'Safety']
N = len(categories)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]  # close

fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

# Style configs
top_styles = [
    {'color': '#222222', 'ls': '-',  'marker': 'o', 'lw': 2.0},
    {'color': '#555555', 'ls': '--', 'marker': 's', 'lw': 1.5},
    {'color': '#777777', 'ls': '-.', 'marker': '^', 'lw': 1.5},
]
bot_styles = [
    {'color': '#999999', 'ls': '-',  'marker': 'D', 'lw': 1.5},
    {'color': '#AAAAAA', 'ls': '--', 'marker': 'v', 'lw': 1.2},
    {'color': '#CCCCCC', 'ls': '-.', 'marker': 'x', 'lw': 1.2},
]

legend_handles = []

for i, (_, row) in enumerate(top3.iterrows()):
    vals = row[dim_cols].values.tolist()
    vals += vals[:1]
    s = top_styles[i]
    ax.plot(angles, vals, color=s['color'], linestyle=s['ls'],
            linewidth=s['lw'], marker=s['marker'], markersize=5)
    ax.fill(angles, vals, color=s['color'], alpha=0.04)
    legend_handles.append(Line2D([0], [0], color=s['color'], linestyle=s['ls'],
                                 marker=s['marker'], markersize=5, linewidth=s['lw'],
                                 label=f"{row['district_name']} ({row['score_UMC']:.3f})"))

for i, (_, row) in enumerate(bot3.iterrows()):
    vals = row[dim_cols].values.tolist()
    vals += vals[:1]
    s = bot_styles[i]
    ax.plot(angles, vals, color=s['color'], linestyle=s['ls'],
            linewidth=s['lw'], marker=s['marker'], markersize=5)
    ax.fill(angles, vals, color=s['color'], alpha=0.04)
    legend_handles.append(Line2D([0], [0], color=s['color'], linestyle=s['ls'],
                                 marker=s['marker'], markersize=5, linewidth=s['lw'],
                                 label=f"{row['district_name']} ({row['score_UMC']:.3f})"))

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=9)
ax.set_ylim(0, 1)
ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=7, color='#888888')
ax.yaxis.grid(True, color='#DDDDDD', linewidth=0.5)
ax.xaxis.grid(True, color='#CCCCCC', linewidth=0.5)
ax.spines['polar'].set_color('#CCCCCC')

# Separator label
legend_handles.insert(3, Line2D([0], [0], color='none', label='─── Bottom 3 ───'))
legend_handles.insert(0, Line2D([0], [0], color='none', label='─── Top 3 ───'))

ax.legend(handles=legend_handles, loc='upper right', bbox_to_anchor=(1.35, 1.1),
          fontsize=8, frameon=True, framealpha=0.95, edgecolor='#CCCCCC')

plt.tight_layout()
plt.savefig(OUT / "fig_report_radar.png", bbox_inches='tight', facecolor='white')
plt.close()
print(f"  -> {OUT / 'fig_report_radar.png'}")

# ================================================================
# Fig 5: Choropleth Map (UMC Composite Score)
# ================================================================
if HAS_GEO and GIS_PATH.exists():
    print("[5/5] Choropleth map...")
    seoul = gpd.read_file(str(GIS_PATH), encoding='cp949')
    seoul['district_code'] = seoul['SIGUNGU_CD'].astype(int)
    seoul = seoul.merge(umc[['district_code', 'score_UMC', 'district_name']],
                        on='district_code', how='left')

    fig, ax = plt.subplots(figsize=(8, 8))
    seoul.plot(column='score_UMC', cmap='Greys', linewidth=0.6,
              edgecolor='#444444', ax=ax, legend=False, vmin=0.25, vmax=0.72)

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap='Greys',
                                norm=plt.Normalize(vmin=0.25, vmax=0.72))
    sm._A = []
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.02)
    cbar.set_label('UMC Composite Score', fontsize=10)
    cbar.ax.tick_params(labelsize=8)

    # District labels
    for _, row in seoul.iterrows():
        centroid = row.geometry.centroid
        name = row.get('district_name', '')
        score = row.get('score_UMC', 0)
        text_color = 'white' if score > 0.55 else '#222222'
        ax.annotate(name, xy=(centroid.x, centroid.y),
                   ha='center', va='center', fontsize=6,
                   color=text_color, fontweight='medium')

    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(OUT / "fig_report_map_umc.png", bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  -> {OUT / 'fig_report_map_umc.png'}")
else:
    print("[5/5] Skipped (geopandas or shapefile not available)")

print("\nDone! All report figures saved to:", OUT)
