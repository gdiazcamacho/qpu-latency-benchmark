"""
Overlay comparison plot: transpiled depth and walltime vs sweep value,
across two or more experiments (typically the same family/axis run on
different backends).

Usage:
    python -m latency_benchmark.analysis.plot_backend_comparison \\
        --db output/db/timing_results_2026-07-08.sqlite \\
        --experiments qft_width_qmio,qft_width_qexa20 \\
        --labels QMIO,QExa20 \\
        --output output/figures/qft_width_comparison.png
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from latency_benchmark.analysis.load_results import load_timing_jobs

SWEEP_TO_COLUMN = {
    "n_circuits": "n_circuits",
    "logical_depth": "logical_depth",
    "shots": "shots",
    "n_qubits": "n_qubits",
}

COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--experiments", required=True, help="Comma-separated experiment_name values to overlay")
    parser.add_argument("--labels", default=None, help="Comma-separated display labels, same order as --experiments (defaults to experiment names)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    experiments = [e.strip() for e in args.experiments.split(",")]
    labels = [l.strip() for l in args.labels.split(",")] if args.labels else experiments

    df_all = load_timing_jobs(args.db)
    df_all = df_all[(df_all["success"] == 1) & df_all["walltime_total"].notna()]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for i, (exp, label) in enumerate(zip(experiments, labels)):
        df = df_all[df_all["experiment_name"] == exp]
        if df.empty:
            print(f"Warning: no rows for experiment_name={exp!r}, skipping.")
            continue

        axis = df["sweep_variable"].dropna().iloc[0] if df["sweep_variable"].notna().any() else None
        xcol = SWEEP_TO_COLUMN.get(axis, axis)
        if xcol not in df.columns:
            print(f"Warning: sweep column {xcol!r} not found for {exp!r}, skipping.")
            continue

        g = df.groupby(xcol).agg(
            depth_mean=("transpiled_depth_mean", "mean"),
            wall_mean=("walltime_total", "mean"),
            wall_std=("walltime_total", "std"),
        ).reset_index()

        color = COLORS[i % len(COLORS)]
        axes[0].plot(g[xcol], g["depth_mean"], "o-", color=color, label=label)
        axes[1].errorbar(g[xcol], g["wall_mean"], yerr=g["wall_std"], fmt="o-",
                          color=color, label=label, capsize=3)
        last_xcol = xcol

    axes[0].set_xlabel(last_xcol)
    axes[0].set_ylabel("Transpiled depth")
    axes[0].set_title("Transpiled depth")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].set_xlabel(last_xcol)
    axes[1].set_ylabel("walltime_total (s)")
    axes[1].set_title("Walltime")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output, dpi=150)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
