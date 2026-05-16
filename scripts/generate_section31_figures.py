#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate refreshed Section 3.1 report figures without optional GIS packages."""

from __future__ import annotations

import argparse
import math
import random
import struct
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "output" / "figures" / "report_refresh_20260516"
SCORES_2024 = ROOT / "output" / "tables" / "seoul_umc_scores_v7_2024.csv"
SHP_PATH = ROOT / "data" / "gis" / "Seoul" / "Seoul.shp"
DBF_PATH = ROOT / "data" / "gis" / "Seoul" / "Seoul.dbf"

CSV_TO_GIS_CODE = {
    11010: 11110,
    11020: 11140,
    11030: 11170,
    11040: 11200,
    11050: 11215,
    11060: 11230,
    11070: 11260,
    11080: 11290,
    11090: 11305,
    11100: 11320,
    11110: 11350,
    11120: 11380,
    11130: 11410,
    11140: 11440,
    11150: 11470,
    11160: 11500,
    11170: 11530,
    11180: 11545,
    11190: 11560,
    11200: 11590,
    11210: 11620,
    11220: 11650,
    11230: 11680,
    11240: 11710,
    11250: 11740,
}

GU_NAME = {
    11010: "Jongno",
    11020: "Jung",
    11030: "Yongsan",
    11040: "Seongdong",
    11050: "Gwangjin",
    11060: "Dongdaemun",
    11070: "Jungnang",
    11080: "Seongbuk",
    11090: "Gangbuk",
    11100: "Dobong",
    11110: "Nowon",
    11120: "Eunpyeong",
    11130: "Seodaemun",
    11140: "Mapo",
    11150: "Yangcheon",
    11160: "Gangseo",
    11170: "Guro",
    11180: "Geumcheon",
    11190: "Yeongdeungpo",
    11200: "Dongjak",
    11210: "Gwanak",
    11220: "Seocho",
    11230: "Gangnam",
    11240: "Songpa",
    11250: "Gangdong",
}

DIMENSIONS = [
    ("score_Infrastructure", "Connectivity"),
    ("score_Available_for_Use", "Available\nfor Use"),
    ("score_Affordability", "Affordability"),
    ("score_Devices", "Devices"),
    ("score_Digital_Skills", "Digital\nSkills"),
    ("score_Safety", "Safety"),
]

DIGITAL_DESERT_CODES = {11070, 11100, 11090, 11170, 11110}

INK = "#222222"
MUTED_INK = "#555555"
GRID = "#d9d9d9"
MAP_EDGE = "#686868"
TOP_COLOR = "#8a4f4f"
DESERT_COLOR = "#4f637a"
OTHER_COLOR = "#aeb6bf"

CLUSTER_COLORS = {
    "High-High": "#8a4f4f",
    "Low-Low": "#4f637a",
    "High-Low": "#c49a6c",
    "Low-High": "#7b9a9a",
    "Not significant": "#f1f1ef",
}

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 8.5,
        "axes.titlesize": 9,
        "axes.titleweight": "normal",
        "axes.labelsize": 9,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.7,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "legend.frameon": True,
        "legend.edgecolor": "#bdbdbd",
        "legend.framealpha": 1.0,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 300,
    }
)


def read_dbf(path: Path) -> list[dict[str, str]]:
    data = path.read_bytes()
    n_records = struct.unpack("<I", data[4:8])[0]
    header_len = struct.unpack("<H", data[8:10])[0]
    record_len = struct.unpack("<H", data[10:12])[0]
    fields = []
    pos = 32
    while data[pos] != 0x0D:
        raw_name = data[pos : pos + 11].split(b"\x00", 1)[0]
        name = raw_name.decode("ascii", errors="ignore")
        ftype = chr(data[pos + 11])
        flen = data[pos + 16]
        fields.append((name, ftype, flen))
        pos += 32
    records = []
    pos = header_len
    for _ in range(n_records):
        rec = data[pos : pos + record_len]
        pos += record_len
        if rec[:1] == b"*":
            continue
        offset = 1
        values = {}
        for name, _ftype, flen in fields:
            raw = rec[offset : offset + flen]
            offset += flen
            values[name] = raw.decode("cp949", errors="ignore").strip()
        records.append(values)
    return records


def read_shp_polygons(path: Path) -> list[list[np.ndarray]]:
    raw = path.read_bytes()
    pos = 100
    shapes = []
    while pos < len(raw):
        if pos + 8 > len(raw):
            break
        _rec_no, rec_len_words = struct.unpack(">2i", raw[pos : pos + 8])
        pos += 8
        rec_len = rec_len_words * 2
        content = raw[pos : pos + rec_len]
        pos += rec_len
        if len(content) < 44:
            continue
        shape_type = struct.unpack("<i", content[:4])[0]
        if shape_type == 0:
            shapes.append([])
            continue
        if shape_type not in {5, 15, 25, 31}:
            raise ValueError(f"Unsupported shapefile shape type: {shape_type}")
        num_parts = struct.unpack("<i", content[36:40])[0]
        num_points = struct.unpack("<i", content[40:44])[0]
        parts_start = 44
        points_start = parts_start + num_parts * 4
        parts = list(struct.unpack(f"<{num_parts}i", content[parts_start:points_start]))
        points = np.frombuffer(content[points_start : points_start + num_points * 16], dtype="<f8")
        points = points.reshape(num_points, 2)
        parts.append(num_points)
        rings = [points[parts[i] : parts[i + 1]].copy() for i in range(num_parts)]
        shapes.append(rings)
    return shapes


def ring_area(points: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def ring_centroid(points: np.ndarray) -> tuple[float, float]:
    area = ring_area(points)
    if abs(area) < 1e-12:
        return float(points[:, 0].mean()), float(points[:, 1].mean())
    x = points[:, 0]
    y = points[:, 1]
    cross = x * np.roll(y, -1) - np.roll(x, -1) * y
    cx = np.sum((x + np.roll(x, -1)) * cross) / (6 * area)
    cy = np.sum((y + np.roll(y, -1)) * cross) / (6 * area)
    return float(cx), float(cy)


def load_geometry() -> dict[int, dict[str, object]]:
    records = read_dbf(DBF_PATH)
    shapes = read_shp_polygons(SHP_PATH)
    if len(records) != len(shapes):
        raise ValueError(f"DBF/SHP length mismatch: {len(records)} vs {len(shapes)}")
    geometry = {}
    gis_to_csv = {v: k for k, v in CSV_TO_GIS_CODE.items()}
    for record, rings in zip(records, shapes):
        gis_code = int(record["SIGUNGU_CD"])
        csv_code = gis_code if gis_code in GU_NAME else gis_to_csv[gis_code]
        largest = max(rings, key=lambda r: abs(ring_area(r)))
        geometry[csv_code] = {
            "rings": rings,
            "centroid": ring_centroid(largest),
            "bounds": (
                min(float(r[:, 0].min()) for r in rings),
                min(float(r[:, 1].min()) for r in rings),
                max(float(r[:, 0].max()) for r in rings),
                max(float(r[:, 1].max()) for r in rings),
            ),
        }
    return geometry


def build_neighbors(geometry: dict[int, dict[str, object]]) -> dict[int, set[int]]:
    vertex_to_codes: dict[tuple[float, float], set[int]] = defaultdict(set)
    for code, item in geometry.items():
        for ring in item["rings"]:
            for x, y in ring:
                vertex_to_codes[(round(float(x), 3), round(float(y), 3))].add(code)
    neighbors = {code: set() for code in geometry}
    for codes in vertex_to_codes.values():
        if len(codes) > 1:
            for a in codes:
                neighbors[a].update(c for c in codes if c != a)
    if any(len(v) == 0 for v in neighbors.values()):
        centroids = {k: np.array(v["centroid"]) for k, v in geometry.items()}
        for code in neighbors:
            if neighbors[code]:
                continue
            distances = sorted(
                (float(np.linalg.norm(centroids[code] - centroids[other])), other)
                for other in neighbors
                if other != code
            )
            neighbors[code].update(other for _dist, other in distances[:4])
    return neighbors


def row_standardized_weights(codes: list[int], neighbors: dict[int, set[int]]) -> np.ndarray:
    idx = {code: i for i, code in enumerate(codes)}
    w = np.zeros((len(codes), len(codes)), dtype=float)
    for code in codes:
        valid = [n for n in neighbors[code] if n in idx]
        if not valid:
            continue
        i = idx[code]
        for n in valid:
            w[i, idx[n]] = 1.0 / len(valid)
    return w


def global_moran(x: np.ndarray, w: np.ndarray, seed: int = 20260516, permutations: int = 999) -> tuple[float, float]:
    z = x - x.mean()
    denom = float(np.sum(z**2))
    s0 = float(w.sum())
    observed = len(x) / s0 * float(z @ w @ z) / denom
    rng = random.Random(seed)
    simulated = []
    z_list = list(z)
    for _ in range(permutations):
        rng.shuffle(z_list)
        zp = np.array(z_list)
        simulated.append(len(x) / s0 * float(zp @ w @ zp) / denom)
    extreme = sum(abs(v) >= abs(observed) for v in simulated)
    p_value = (extreme + 1) / (permutations + 1)
    return observed, p_value


def lisa_clusters(
    x: np.ndarray,
    w: np.ndarray,
    seed: int = 20260516,
    permutations: int = 999,
    alpha: float = 0.10,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    z = x - x.mean()
    std = z.std(ddof=0)
    if std == 0:
        return ["Not significant"] * len(x), np.zeros(len(x)), np.ones(len(x)), np.zeros(len(x))
    z = z / std
    lag = w @ z
    local_i = z * lag
    rng = random.Random(seed)
    sims = np.zeros((permutations, len(x)), dtype=float)
    z_list = list(z)
    for r in range(permutations):
        rng.shuffle(z_list)
        zp = np.array(z_list)
        sims[r, :] = zp * (w @ zp)
    p_values = np.array([(np.sum(np.abs(sims[:, i]) >= abs(local_i[i])) + 1) / (permutations + 1) for i in range(len(x))])
    clusters = []
    for zi, li, pv in zip(z, lag, p_values):
        if pv > alpha:
            clusters.append("Not significant")
        elif zi >= 0 and li >= 0:
            clusters.append("High-High")
        elif zi < 0 and li < 0:
            clusters.append("Low-Low")
        elif zi >= 0 and li < 0:
            clusters.append("High-Low")
        else:
            clusters.append("Low-High")
    return clusters, local_i, p_values, lag


def make_patches(geometry: dict[int, dict[str, object]], codes: list[int]) -> tuple[list[MplPolygon], list[int]]:
    patches = []
    patch_codes = []
    for code in codes:
        for ring in geometry[code]["rings"]:
            patches.append(MplPolygon(ring, closed=True))
            patch_codes.append(code)
    return patches, patch_codes


def set_map_limits(ax, geometry: dict[int, dict[str, object]]) -> None:
    xs0, ys0, xs1, ys1 = [], [], [], []
    for item in geometry.values():
        x0, y0, x1, y1 = item["bounds"]
        xs0.append(x0)
        ys0.append(y0)
        xs1.append(x1)
        ys1.append(y1)
    pad_x = (max(xs1) - min(xs0)) * 0.04
    pad_y = (max(ys1) - min(ys0)) * 0.04
    ax.set_xlim(min(xs0) - pad_x, max(xs1) + pad_x)
    ax.set_ylim(min(ys0) - pad_y, max(ys1) + pad_y)
    ax.set_aspect("equal")
    ax.axis("off")


def plot_map(
    ax,
    geometry: dict[int, dict[str, object]],
    codes: list[int],
    values: dict[int, float] | None = None,
    *,
    cmap="viridis",
    vmin=None,
    vmax=None,
    colors: dict[int, str] | None = None,
    label_codes: set[int] | None = None,
    linewidth: float = 0.7,
):
    patches, patch_codes = make_patches(geometry, codes)
    if colors is not None:
        facecolors = [colors[c] for c in patch_codes]
        collection = PatchCollection(patches, facecolor=facecolors, edgecolor=MAP_EDGE, linewidth=linewidth)
        ax.add_collection(collection)
    else:
        vals = np.array([values[c] for c in patch_codes], dtype=float)
        collection = PatchCollection(patches, cmap=cmap, edgecolor=MAP_EDGE, linewidth=linewidth)
        collection.set_array(vals)
        if vmin is not None or vmax is not None:
            collection.set_clim(vmin, vmax)
        ax.add_collection(collection)
    set_map_limits(ax, geometry)
    if label_codes:
        for code in sorted(label_codes):
            x, y = geometry[code]["centroid"]
            ax.text(
                x,
                y,
                GU_NAME[code],
                ha="center",
                va="center",
                fontsize=7.5,
                weight="normal",
                color=INK,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")],
            )
    return collection


def add_desert_outline(ax, geometry: dict[int, dict[str, object]]) -> None:
    patches, _codes = make_patches(geometry, sorted(DIGITAL_DESERT_CODES))
    collection = PatchCollection(patches, facecolor="none", edgecolor=INK, linewidth=1.2, hatch="////")
    ax.add_collection(collection)


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()


def figure_01_map(df: pd.DataFrame, geometry: dict[int, dict[str, object]], out: Path) -> None:
    codes = df["district_code"].tolist()
    values = dict(zip(df["district_code"], df["score_UMC"]))
    label_codes = set(df.nsmallest(5, "rank_UMC")["district_code"]) | DIGITAL_DESERT_CODES
    fig, ax = plt.subplots(figsize=(6.1, 6.3))
    collection = plot_map(ax, geometry, codes, values, cmap="cividis", vmin=0.25, vmax=0.72, label_codes=label_codes)
    add_desert_outline(ax, geometry)
    ax.set_title("Composite index by district, 2024", pad=8)
    ax.text(
        0.0,
        -0.03,
        "Hatched districts: provisional Digital Deserts (bottom-five composite index).",
        transform=ax.transAxes,
        fontsize=9,
        color=MUTED_INK,
    )
    cbar = fig.colorbar(collection, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("UMC composite score (0-1)", fontsize=8.5)
    savefig(out / "fig01_umc_composite_map_2024.png")


def figure_02_rank(df: pd.DataFrame, out: Path) -> None:
    d = df.sort_values("score_UMC", ascending=True).copy()
    colors = [DESERT_COLOR if c in DIGITAL_DESERT_CODES else OTHER_COLOR for c in d["district_code"]]
    top_codes = set(d.tail(5)["district_code"])
    colors = [TOP_COLOR if c in top_codes else col for c, col in zip(d["district_code"], colors)]
    fig, ax = plt.subplots(figsize=(3.45, 3.25))
    y = np.arange(len(d))
    ax.barh(y, d["score_UMC"], color=colors, edgecolor=INK, linewidth=0.35)
    ax.set_yticks(y)
    ax.set_yticklabels([GU_NAME[c] for c in d["district_code"]], fontsize=4.8)
    ax.axvline(d["score_UMC"].mean(), color=INK, linestyle="--", linewidth=0.8)
    ax.text(d["score_UMC"].mean() + 0.004, len(d) - 0.8, f"Mean {d['score_UMC'].mean():.3f}", fontsize=5.2)
    for yi, value, code in zip(y, d["score_UMC"], d["district_code"]):
        if code in top_codes or code in DIGITAL_DESERT_CODES:
            ax.text(value + 0.006, yi, f"{value:.3f}", va="center", fontsize=4.7)
    ax.set_xlim(0.24, 0.74)
    ax.set_xlabel("UMC composite score (0-1)")
    ax.set_title("Composite score ranking, 2024", fontsize=7.8, pad=5)
    ax.grid(axis="x", color=GRID, linewidth=0.5)
    ax.spines[["top", "right", "left"]].set_visible(False)
    legend = [
        Patch(facecolor=TOP_COLOR, edgecolor=INK, label="Top five"),
        Patch(facecolor=DESERT_COLOR, edgecolor=INK, label="Digital Deserts"),
        Patch(facecolor=OTHER_COLOR, edgecolor=INK, label="Other districts"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=5.6, borderpad=0.35, labelspacing=0.35, handlelength=1.2)
    savefig(out / "fig02_umc_ranked_scores_2024.png")


def figure_03_heatmap(df: pd.DataFrame, out: Path) -> None:
    d = df.sort_values("score_UMC", ascending=False).copy()
    cols = [c for c, _label in DIMENSIONS]
    labels = [label.replace("\n", " ") for _c, label in DIMENSIONS]
    data = d[cols].to_numpy()
    fig, ax = plt.subplots(figsize=(3.65, 3.05))
    im = ax.imshow(data, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=4.8)
    ax.set_yticks(np.arange(len(d)))
    ax.set_yticklabels([GU_NAME[c] for c in d["district_code"]], fontsize=4.8)
    ax.set_title("Dimension scores by district, 2024", fontsize=7.8, pad=5)
    ax.set_xlabel("UMC dimension")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Dimension score (0-1)", fontsize=6.0)
    cbar.ax.tick_params(labelsize=5.5)
    savefig(out / "fig03_dimension_heatmap_2024.png")


def figure_04_profiles(df: pd.DataFrame, out: Path) -> None:
    top5 = df.nsmallest(5, "rank_UMC")
    desert = df[df["district_code"].isin(DIGITAL_DESERT_CODES)]
    city = df
    labels = [label.replace("\n", " ") for _c, label in DIMENSIONS]
    x = np.arange(len(DIMENSIONS))
    top_vals = [top5[c].mean() for c, _label in DIMENSIONS]
    desert_vals = [desert[c].mean() for c, _label in DIMENSIONS]
    city_vals = [city[c].mean() for c, _label in DIMENSIONS]
    fig, ax = plt.subplots(figsize=(6.2, 3.7))
    ax.plot(x, top_vals, color=TOP_COLOR, linewidth=1.8, marker="o", markersize=4.5, label="Top-five districts")
    ax.plot(x, city_vals, color=INK, linewidth=1.4, marker="o", markersize=4.0, linestyle="--", label="City mean")
    ax.plot(x, desert_vals, color=DESERT_COLOR, linewidth=1.8, marker="o", markersize=4.5, label="Digital Deserts")
    for vals, color in [(top_vals, TOP_COLOR), (city_vals, INK), (desert_vals, DESERT_COLOR)]:
        for xi, yi in zip(x, vals):
            ax.text(xi, yi + 0.025, f"{yi:.2f}", ha="center", va="bottom", fontsize=8, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 1.04)
    ax.set_ylabel("Mean dimension score (0-1)")
    ax.set_title("Mean dimension profiles, 2024", pad=8)
    ax.grid(axis="y", color=GRID, linewidth=0.5)
    ax.legend(loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    savefig(out / "fig04_dimension_profiles_2024.png")


def figure_05_lisa(df: pd.DataFrame, geometry: dict[int, dict[str, object]], neighbors: dict[int, set[int]], out: Path) -> pd.DataFrame:
    codes = sorted(df["district_code"].tolist())
    w = row_standardized_weights(codes, neighbors)
    indexed = df.set_index("district_code").loc[codes]
    variables = [("score_UMC", "Composite")] + DIMENSIONS
    stats = []
    cluster_by_var = {}
    details_by_var = {}
    for var, label in variables:
        x = indexed[var].to_numpy(dtype=float)
        moran_i, p_global = global_moran(x, w)
        clusters, local_i, p_local, lag = lisa_clusters(x, w)
        cluster_by_var[var] = dict(zip(codes, clusters))
        z = (x - x.mean()) / x.std(ddof=0)
        details_by_var[var] = {
            "z": z,
            "lag": lag,
            "local_i": local_i,
            "p_local": p_local,
            "clusters": clusters,
        }
        stats.append(
            {
                "variable": var,
                "label": label.replace("\n", " "),
                "global_moran_i": moran_i,
                "global_p_perm": p_global,
                "hh": clusters.count("High-High"),
                "ll": clusters.count("Low-Low"),
                "hl": clusters.count("High-Low"),
                "lh": clusters.count("Low-High"),
            }
        )
    stats_df = pd.DataFrame(stats)

    # Main Figure 5: composite Moran scatterplot + LISA cluster map.
    composite = details_by_var["score_UMC"]
    composite_clusters = cluster_by_var["score_UMC"]
    composite_stats = stats_df[stats_df["variable"] == "score_UMC"].iloc[0]
    point_colors = [CLUSTER_COLORS[c] for c in composite["clusters"]]
    sig_codes = {code for code, cluster in composite_clusters.items() if cluster != "Not significant"}

    fig, (ax_scatter, ax_map) = plt.subplots(1, 2, figsize=(6.6, 3.65), gridspec_kw={"width_ratios": [1.0, 1.18]})
    ax_scatter.scatter(composite["z"], composite["lag"], s=62, c=point_colors, edgecolor=INK, linewidth=0.55, zorder=3)
    fit_x = np.linspace(composite["z"].min() - 0.3, composite["z"].max() + 0.3, 100)
    ax_scatter.plot(fit_x, composite_stats["global_moran_i"] * fit_x, color=INK, linewidth=1.0, label="Moran slope")
    ax_scatter.axhline(0, color="#7a7a7a", linewidth=0.7)
    ax_scatter.axvline(0, color="#7a7a7a", linewidth=0.7)
    ax_scatter.set_xlabel("Standardized 2024 UMC score")
    ax_scatter.set_ylabel("Spatial lag of standardized UMC")
    ax_scatter.set_title("A. Moran scatterplot", pad=7)
    ax_scatter.grid(color=GRID, linewidth=0.45)
    label_offsets = {
        11130: (12, 10),
        11140: (10, -2),
        11030: (10, -12),
        11070: (8, 6),
        11100: (8, -4),
        11090: (8, -4),
        11110: (8, 8),
        11220: (8, 8),
    }
    for code, x_val, y_val, cluster in zip(codes, composite["z"], composite["lag"], composite["clusters"]):
        if cluster == "Not significant":
            continue
        ax_scatter.annotate(
            GU_NAME[code],
            (x_val, y_val),
            xytext=label_offsets.get(code, (6, 6)),
            textcoords="offset points",
            fontsize=6.2,
        )
    ax_scatter.text(
        0.03,
        0.97,
        f"Global Moran's I = {composite_stats['global_moran_i']:.3f}\nPermutation p = {composite_stats['global_p_perm']:.3f}",
        transform=ax_scatter.transAxes,
        ha="left",
        va="top",
        fontsize=7.2,
        bbox={"facecolor": "white", "edgecolor": "#bdbdbd", "boxstyle": "square,pad=0.30"},
    )

    colors = {code: CLUSTER_COLORS[composite_clusters[code]] for code in codes}
    plot_map(ax_map, geometry, codes, colors=colors, label_codes=sig_codes, linewidth=0.75)
    ax_map.set_title("B. LISA cluster map", pad=7)
    handles = [Patch(facecolor=color, edgecolor=INK, label=label) for label, color in CLUSTER_COLORS.items()]
    fig.subplots_adjust(bottom=0.23, top=0.84, wspace=0.15)
    fig.legend(handles=handles, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.035))
    fig.suptitle("UMC spatial autocorrelation diagnostics, 2024", fontsize=9.5, fontweight="normal", y=0.965)
    fig.text(
        0.5,
        0.125,
        "Queen contiguity weights; local clusters use alpha=0.10 with 999 random permutations.",
        ha="center",
        fontsize=6.6,
        color=MUTED_INK,
    )
    savefig(out / "fig05_lisa_spatial_autocorrelation_2024.png")

    # Supplemental dimension panel for the same Figure 5 family.
    dim_vars = DIMENSIONS
    fig, axes = plt.subplots(2, 3, figsize=(6.6, 4.9))
    panel_letters = ["A", "B", "C", "D", "E", "F"]
    for ax, (var, label), letter in zip(axes.ravel(), dim_vars, panel_letters):
        colors = {code: CLUSTER_COLORS[cluster_by_var[var][code]] for code in codes}
        sig_codes_dim = {code for code, cluster in cluster_by_var[var].items() if cluster != "Not significant"}
        plot_map(ax, geometry, codes, colors=colors, label_codes=sig_codes_dim, linewidth=0.55)
        row = stats_df[stats_df["variable"] == var].iloc[0]
        ax.set_title(f"{letter}. {label.replace(chr(10), ' ')}\nI={row['global_moran_i']:.2f}, p={row['global_p_perm']:.2f}", fontsize=7.5, fontweight="normal", pad=3)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.20, wspace=0.05, hspace=0.26)
    fig.legend(handles=handles, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.035), fontsize=6.8)
    fig.text(0.5, 0.11, "Queen contiguity weights; 999 permutations; local alpha = 0.10.", ha="center", fontsize=6.6, color=MUTED_INK)
    savefig(out / "fig05b_lisa_dimension_panels_2024.png")
    return stats_df


def run(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SCORES_2024).copy()
    df.loc[:, "district_code"] = df["district_code"].astype(int)
    if len(df) != 25:
        raise ValueError(f"Expected 25 districts, got {len(df)}")
    geometry = load_geometry()
    missing_geom = set(df["district_code"]) - set(geometry)
    if missing_geom:
        raise ValueError(f"Missing geometry for district codes: {sorted(missing_geom)}")
    neighbors = build_neighbors(geometry)
    neighbor_counts = {code: len(neighbors[code]) for code in sorted(neighbors)}
    figure_01_map(df, geometry, out)
    figure_02_rank(df, out)
    figure_03_heatmap(df, out)
    figure_04_profiles(df, out)
    stats = figure_05_lisa(df, geometry, neighbors, out)
    stats.to_csv(out / "fig05_lisa_moran_stats_2024.csv", index=False)
    print(f"Output directory: {out}")
    print("Generated:")
    for path in sorted(out.iterdir()):
        print(f"  {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    print("Neighbor counts:")
    print(", ".join(f"{GU_NAME[c]}={n}" for c, n in neighbor_counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(args.out)


if __name__ == "__main__":
    main()
