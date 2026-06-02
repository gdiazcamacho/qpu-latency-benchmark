import argparse
import numpy as np
import pandas as pd

from timing_benchmark.analysis.load_results import load_timing_jobs


def fit_linear_model(df: pd.DataFrame):
    good = df[(df["success"] == 1) & df["walltime_total"].notna()].copy()

    if len(good) < 3:
        raise ValueError("Need at least 3 successful timing rows to fit model.")

    # Model: T = a + b*N + c*N*depth
    y = good["walltime_total"].to_numpy(dtype=float)
    N = good["n_circuits"].to_numpy(dtype=float)
    d = good["logical_depth"].to_numpy(dtype=float)

    X = np.column_stack([
        np.ones(len(good)),
        N,
        N * d,
    ])

    coef, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef

    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return {
        "T0_fixed_job_overhead": coef[0],
        "alpha_per_circuit_overhead": coef[1],
        "beta_per_circuit_depth_scaling": coef[2],
        "r2": r2,
        "n_rows": len(good),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--experiment-name", default=None)
    args = parser.parse_args()

    df = load_timing_jobs(args.db)

    if args.backend:
        df = df[df["backend"] == args.backend]
    if args.experiment_name:
        df = df[df["experiment_name"] == args.experiment_name]

    print(f"Loaded {len(df)} rows")

    result = fit_linear_model(df)
    print("\nModel: T = T0 + alpha*N + beta*N*depth\n")
    for k, v in result.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
