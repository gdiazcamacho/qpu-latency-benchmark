"""Fit a simple linear model to one-dimensional latency probes."""

import argparse
import numpy as np

from timing_benchmark.analysis.load_results import load_timing_jobs

SWEEP_TO_COLUMN = {
    "n_circuits": "n_circuits",
    "logical_depth": "logical_depth",
    "shots": "shots",
    "n_qubits": "n_qubits",
}


def main():
    parser = argparse.ArgumentParser(description="Fit T = a + b*x for a one-dimensional timing probe.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--experiment-name", default=None, dest="experiment_name")
    parser.add_argument("--experiment-type", default=None, dest="experiment_type")
    parser.add_argument("--x", default=None, help="Override x-axis column")
    args = parser.parse_args()

    df = load_timing_jobs(args.db)
    df = df[(df["success"] == 1) & df["walltime_total"].notna()].copy()
    if args.backend:
        df = df[df["backend"] == args.backend]
    if args.experiment_name:
        df = df[df["experiment_name"] == args.experiment_name]
    if args.experiment_type:
        df = df[df["experiment_type"] == args.experiment_type]

    if len(df) < 3:
        raise SystemExit(f"Need at least 3 rows; got {len(df)}.")

    inferred = df["sweep_variable"].dropna().iloc[0] if df["sweep_variable"].notna().any() else None
    xcol = args.x or SWEEP_TO_COLUMN.get(inferred, inferred)
    if xcol not in df.columns:
        raise SystemExit(f"Cannot fit x={xcol!r}; available columns: {list(df.columns)}")

    y = df["walltime_total"].to_numpy(float)
    x = df[xcol].to_numpy(float)
    X = np.column_stack([np.ones(len(df)), x])
    coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    print(f"Rows: {len(df)}")
    print(f"Model: T = intercept + slope*{xcol}")
    print(f"intercept_s: {coef[0]:.6f}")
    print(f"slope_s_per_{xcol}: {coef[1]:.9f}")
    print(f"r2: {r2:.6f}")


if __name__ == "__main__":
    main()
