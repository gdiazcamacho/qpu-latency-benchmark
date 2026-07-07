"""Fit the registered model (linear or quadratic) for a one-dimensional
latency probe, selected automatically via analysis/models.py's
(circuit_family, sweep_axis) registry.
"""
import argparse

from latency_benchmark.analysis.load_results import load_timing_jobs
from latency_benchmark.analysis.models import get_model, linear_model

SWEEP_TO_COLUMN = {
    "n_circuits": "n_circuits",
    "logical_depth": "logical_depth",
    "shots": "shots",
    "n_qubits": "n_qubits",
}


def main():
    parser = argparse.ArgumentParser(description="Fit the registered model for a timing probe.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--experiment-name", default=None, dest="experiment_name")
    parser.add_argument("--experiment-type", default=None, dest="experiment_type")
    parser.add_argument("--x", default=None, help="Override x-axis column")
    parser.add_argument("--force-linear", action="store_true", dest="force_linear",
                         help="Ignore the model registry and force a linear fit.")
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

    inferred_axis = df["sweep_variable"].dropna().iloc[0] if df["sweep_variable"].notna().any() else None
    inferred_family = df["circuit_family"].dropna().iloc[0] if df["circuit_family"].notna().any() else None
    xcol = args.x or SWEEP_TO_COLUMN.get(inferred_axis, inferred_axis)
    if xcol not in df.columns:
        raise SystemExit(f"Cannot fit x={xcol!r}; available columns: {list(df.columns)}")

    y = df["walltime_total"].to_numpy(float)
    x = df[xcol].to_numpy(float)

    if args.force_linear or inferred_family is None:
        fit_fn = linear_model
    else:
        try:
            fit_fn = get_model(inferred_family, inferred_axis)
        except ValueError as e:
            print(f"Warning: {e} Falling back to linear.")
            fit_fn = linear_model

    result = fit_fn(x, y)

    print(f"Rows: {len(df)}")
    print(f"circuit_family: {inferred_family}  sweep_axis: {inferred_axis}")
    print(f"Model: {result['model']}  ({result['formula']})")
    for name, val in result["params"].items():
        print(f"  {name} = {val:.6f}")
    print(f"r2: {result['r2']:.6f}")


if __name__ == "__main__":
    main()
