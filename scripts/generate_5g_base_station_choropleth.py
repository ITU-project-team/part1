#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a report-ready 5G base-station density choropleth for Seoul."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCORES_2024 = ROOT / "output" / "tables" / "seoul_umc_scores_v7_2024.csv"
HELPER_SCRIPT = ROOT / "scripts" / "generate_section31_figures.py"
DEFAULT_OUT = ROOT / "output" / "figures" / "report_refresh_20260528"
DEFAULT_TABLE_OUT = ROOT / "output" / "tables" / "report_refresh_20260528"


def load_helpers():
    spec = importlib.util.spec_from_file_location("section31_helpers", HELPER_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load helper script: {HELPER_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--table-out", type=Path, default=DEFAULT_TABLE_OUT)
    args = parser.parse_args()

    helpers = load_helpers()
    df = pd.read_csv(SCORES_2024)
    required = {"district_code", "district", "station_density_5g", "n_station_density_5g"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {SCORES_2024}: {sorted(missing)}")

    geometry = helpers.load_geometry()
    df = df.sort_values("station_density_5g", ascending=False).copy()
    codes = df["district_code"].tolist()
    values = dict(zip(df["district_code"], df["station_density_5g"]))
    top5 = set(df.head(5)["district_code"])
    bottom5 = set(df.tail(5)["district_code"])
    label_codes = top5 | bottom5

    fig, ax = plt.subplots(figsize=(6.2, 6.35))
    collection = helpers.plot_map(
        ax,
        geometry,
        codes,
        values,
        cmap="cividis",
        vmin=float(df["station_density_5g"].min()),
        vmax=float(df["station_density_5g"].max()),
        label_codes=label_codes,
        linewidth=0.7,
    )
    ax.set_title("5G base-station density by district, 2024", pad=8)
    cbar = fig.colorbar(collection, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("5G base stations per 1,000 daytime living-population units", fontsize=8.3)

    args.out.mkdir(parents=True, exist_ok=True)
    figure_path = args.out / "fig_5g_base_station_density_2024.png"
    helpers.savefig(figure_path)

    args.table_out.mkdir(parents=True, exist_ok=True)
    summary_path = args.table_out / "fig_5g_base_station_density_2024_source.csv"
    df[
        [
            "district_code",
            "district",
            "station_density_5g",
            "n_station_density_5g",
            "living_pop_daytime",
        ]
    ].to_csv(summary_path, index=False)

    print(f"figure={figure_path}")
    print(f"source_table={summary_path}")


if __name__ == "__main__":
    main()
