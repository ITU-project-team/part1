#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a report-ready 5G base-station density choropleth for Section 2.3.1.

Reuses the GIS-free map machinery and district geometry from
generate_section31_figures.py. Reads district-level aggregate values only
(no raw base-station coordinates), so no protected raw data is touched.

Source: Cellular Base Station Data, Spectrum Resource Mgmt System.
Each physical site counted once, matched to a common Seoul district code,
and converted to a density per 1,000 daytime living population.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from generate_section31_figures import (
    DEFAULT_OUT,
    DIGITAL_DESERT_CODES,
    GU_NAME,
    MUTED_INK,
    SCORES_2024,
    add_desert_outline,
    load_geometry,
    plot_map,
    savefig,
)

DENSITY_COL = "station_density_5g"
TITLE = "5G base-station density by district, 2024"
COLORBAR_LABEL = "5G base stations per 1,000 daytime living population"
SOURCE_NOTE = (
    "Source: Cellular Base Station Data, Spectrum Resource Mgmt System. "
    "Each physical site counted once and population-adjusted."
)


def load_density(scores_path: Path) -> pd.DataFrame:
    df = pd.read_csv(scores_path).copy()
    df.loc[:, "district_code"] = df["district_code"].astype(int)
    if DENSITY_COL not in df.columns:
        raise KeyError(f"{DENSITY_COL} not found in {scores_path}")
    return df


def figure_5g_map(df: pd.DataFrame, geometry, out: Path) -> Path:
    codes = df["district_code"].tolist()
    values = dict(zip(df["district_code"], df[DENSITY_COL]))
    top5 = set(df.nlargest(5, DENSITY_COL)["district_code"])
    label_codes = top5 | DIGITAL_DESERT_CODES

    fig, ax = plt.subplots(figsize=(6.1, 6.3))
    collection = plot_map(
        ax,
        geometry,
        codes,
        values,
        cmap="Blues",
        vmin=float(df[DENSITY_COL].min()),
        vmax=float(df[DENSITY_COL].max()),
        label_codes=label_codes,
    )
    add_desert_outline(ax, geometry)
    ax.set_title(TITLE, pad=8)
    ax.text(
        0.0,
        -0.03,
        "Hatched districts: provisional Digital Deserts (bottom-five composite index).",
        transform=ax.transAxes,
        fontsize=9,
        color=MUTED_INK,
    )
    cbar = fig.colorbar(collection, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label(COLORBAR_LABEL, fontsize=8.5)
    target = out / "fig_5g_density_map_2024.png"
    savefig(target)
    return target


def main() -> None:
    out = DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    df = load_density(SCORES_2024)
    geometry = load_geometry()
    missing = set(df["district_code"]) - set(geometry)
    if missing:
        raise ValueError(f"districts missing geometry: {sorted(missing)}")
    target = figure_5g_map(df, geometry, out)
    print(f"5G choropleth written: {target}")
    print(SOURCE_NOTE)
    ranked = df.sort_values(DENSITY_COL, ascending=False)
    top = ranked.iloc[0]
    bottom = ranked.iloc[-1]
    print(
        f"Range (district-level aggregate): "
        f"{GU_NAME.get(int(top['district_code']), top['district_code'])} "
        f"{top[DENSITY_COL]:.3f} -> "
        f"{GU_NAME.get(int(bottom['district_code']), bottom['district_code'])} "
        f"{bottom[DENSITY_COL]:.3f}"
    )


if __name__ == "__main__":
    main()
