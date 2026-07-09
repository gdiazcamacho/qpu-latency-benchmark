"""Plot one-dimensional latency probes.

Examples:
    python -m latency_benchmark.analysis.plot_probe --db output/db/timing_results.sqlite --experiment-name shot_scaling_qmio
    python -m latency_benchmark.analysis.plot_probe --db output/db/timing_results.sqlite --backend qmio --experiment-type batch_scaling
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from latency_benchmark.analysis.load_results import load_timing_jobs


SWEEP_TO_COLUMN = {
    "n_circuits": "n_circuits",
    "logical_depth": "logical_depth",
    "shots": "shots",
    "n_qubits": "n_qubits",
    "full_matrix": "n_circuits",
    None: "n_circuits",
}


def main():
    parser = argparse.ArgumentParser(description="Plot one-dimensional timing probe results.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--experiment-name", default=None, dest="experiment_name")
    parser.add_argument("--experiment-type", default=None, dest="experiment_type")
    parser.add_argument("--x", default=None, help="Override x-axis column: n_circuits, logical_depth, shots, n_qubits")
    parser.add_argument("--outdir", default="output/figures")
    args = parser.parse_args()

    df = load_timing_jobs(args.db)
    df = df[(df["success"] == 1) & df["walltime_total"].notna()].copy()

    if args.backend:
        df = df[df["backend"] == args.backend]
    if args.experiment_name:
        df = df[df["experiment_name"] == args.experiment_name]
    if args.experiment_type:
        df = df[df["experiment_type"] == args.experiment_type]

    if df.empty:
        raise SystemExit("No successful rows match the requested filters.")

    inferred = df["sweep_variable"].dropna().iloc[0] if df["sweep_variable"].notna().any() else None
    xcol = args.x or SWEEP_TO_COLUMN.get(inferred, inferred)
    if xcol not in df.columns:
        raise SystemExit(f"Cannot plot x={xcol!r}; available columns: {list(df.columns)}")

    summary = (
        df.groupby(xcol)["walltime_total"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .sort_values(xcol)
    )
    summary["std"] = summary["std"].fillna(0.0)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    plt.figure()
    plt.errorbar(summary[xcol], summary["mean"], yerr=summary["std"], marker="o", capsize=3)
    plt.xlabel(xcol)
    plt.ylabel("Total walltime [s]")
    title_bits = [b for b in [args.experiment_name, args.experiment_type, args.backend] if b]
    plt.title("Timing probe" + (": " + ", ".join(title_bits) if title_bits else ""))
    plt.tight_layout()

    label = args.experiment_name or args.experiment_type or args.backend or "probe"
    outfile = outdir / f"timing_probe_{label}.png"
    plt.savefig(outfile, dpi=200)
    print(f"Saved {outfile}")
    print("\nGrouped data:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
