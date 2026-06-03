"""
Timing overhead decomposition models.

Supported models
----------------
linear_N      : T = T0 + alpha*N                          (depth-blind)
linear_N_d    : T = T0 + alpha*N + beta*N*depth           (full factorial)
linear_N_qt   : T = T0 + alpha*N + beta*estimated_qt      (IQM-instrumented)
per_circuit   : T/N = alpha + beta*depth  (per-circuit overhead, plotted vs depth)

Selection heuristic: if depth has near-zero coefficient or R² gain < 0.01,
the simpler linear_N model is preferred and a warning is emitted.
"""

import argparse
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from latency_benchmark.analysis.load_results import load_timing_jobs

# ---------------------------------------------------------------------------
# Core fitting helpers
# ---------------------------------------------------------------------------

def _lstsq_fit(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, float]:
    coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return coef, r2


def _good_rows(df: pd.DataFrame, min_rows: int = 3) -> pd.DataFrame:
    good = df[(df["success"] == 1) & df["walltime_total"].notna()].copy()
    if len(good) < min_rows:
        raise ValueError(f"Need at least {min_rows} successful rows; got {len(good)}.")
    return good


# ---------------------------------------------------------------------------
# Model: T = T0 + alpha*N   (depth-blind, preferred for QMIO)
# ---------------------------------------------------------------------------

def fit_linear_N(df: pd.DataFrame) -> Dict:
    """Fit T = T0 + alpha*N, ignoring depth.

    Appropriate when depth has negligible influence on walltime (e.g. QMIO),
    meaning the per-circuit overhead is a pure scheduling cost.
    """
    good = _good_rows(df)
    y = good["walltime_total"].to_numpy(float)
    N = good["n_circuits"].to_numpy(float)
    X = np.column_stack([np.ones(len(good)), N])
    coef, r2 = _lstsq_fit(X, y)
    return {
        "model": "T = T0 + alpha*N",
        "T0_fixed_job_overhead_s": coef[0],
        "alpha_per_circuit_s": coef[1],
        "r2": r2,
        "n_rows": len(good),
        "interpretation": (
            f"Fixed job overhead: {coef[0]:.3f} s | "
            f"Per-circuit overhead: {coef[1]*1000:.1f} ms/circuit"
        ),
    }


# ---------------------------------------------------------------------------
# Model: T = T0 + alpha*N + beta*N*depth   (full factorial)
# ---------------------------------------------------------------------------

def fit_linear_N_depth(df: pd.DataFrame) -> Dict:
    """Fit T = T0 + alpha*N + beta*N*depth.

    The original three-parameter model.  If |beta| is small relative to alpha
    a warning is included.
    """
    good = _good_rows(df)
    y = good["walltime_total"].to_numpy(float)
    N = good["n_circuits"].to_numpy(float)
    d = good["logical_depth"].to_numpy(float)
    X = np.column_stack([np.ones(len(good)), N, N * d])
    coef, r2 = _lstsq_fit(X, y)

    depth_fraction = abs(coef[2]) / (abs(coef[1]) + abs(coef[2]) + 1e-12)
    warning = None
    if depth_fraction < 0.01:
        warning = (
            "beta*N*depth term contributes <1% of per-circuit cost. "
            "Depth is not a significant predictor; prefer fit_linear_N."
        )

    return {
        "model": "T = T0 + alpha*N + beta*N*depth",
        "T0_fixed_job_overhead_s": coef[0],
        "alpha_per_circuit_s": coef[1],
        "beta_per_circuit_depth_s": coef[2],
        "r2": r2,
        "n_rows": len(good),
        "depth_fraction_of_per_circuit_cost": depth_fraction,
        "warning": warning,
    }


# ---------------------------------------------------------------------------
# Model: T = T0 + alpha*N + beta*estimated_quantum_time  (IQM-instrumented)
# ---------------------------------------------------------------------------

def fit_linear_N_qt(df: pd.DataFrame, qt_col: str = "estimated_quantum_time_s") -> Dict:
    """Fit T = T0 + alpha*N + beta*estimated_quantum_time.

    Requires a column with the estimated quantum execution time per job
    (e.g. from IQM's detailed timing events).  Falls back to None if the
    column is absent.
    """
    if qt_col not in df.columns or df[qt_col].isna().all():
        return {
            "model": "T = T0 + alpha*N + beta*QT",
            "error": f"Column '{qt_col}' not available in this dataset.",
        }
    good = _good_rows(df)
    good = good[good[qt_col].notna()]
    if len(good) < 3:
        return {"model": "T = T0 + alpha*N + beta*QT", "error": "Insufficient rows with QT data."}

    y = good["walltime_total"].to_numpy(float)
    N = good["n_circuits"].to_numpy(float)
    qt = good[qt_col].to_numpy(float)
    X = np.column_stack([np.ones(len(good)), N, qt])
    coef, r2 = _lstsq_fit(X, y)
    return {
        "model": "T = T0 + alpha*N + beta*QT",
        "T0_fixed_job_overhead_s": coef[0],
        "alpha_per_circuit_s": coef[1],
        "beta_quantum_time_multiplier": coef[2],
        "r2": r2,
        "n_rows": len(good),
    }


# ---------------------------------------------------------------------------
# Derived metric: per-circuit overhead vs depth
# ---------------------------------------------------------------------------

def compute_per_circuit_overhead(df: pd.DataFrame) -> pd.DataFrame:
    """Compute mean T/N grouped by (n_circuits, logical_depth).

    Returns a DataFrame useful for plotting the depth-sensitivity of the
    per-circuit overhead.
    """
    good = _good_rows(df)
    good = good.copy()
    good["time_per_circuit"] = good["walltime_total"] / good["n_circuits"]
    summary = (
        good.groupby(["n_circuits", "logical_depth"])["time_per_circuit"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    summary.columns = ["n_circuits", "logical_depth", "mean_s", "std_s", "count"]
    return summary


# ---------------------------------------------------------------------------
# Auto-select model
# ---------------------------------------------------------------------------

def auto_fit(df: pd.DataFrame) -> Dict:
    """Automatically choose the best model for the given dataset.

    Fits both linear_N and linear_N_depth; selects the simpler one if the
    depth term adds less than 1% R² improvement.
    """
    r_simple = fit_linear_N(df)
    r_full = fit_linear_N_depth(df)

    r2_gain = r_full["r2"] - r_simple["r2"]
    if r2_gain < 0.01 or r_full.get("warning"):
        chosen = r_simple
        chosen["_selection_reason"] = (
            f"Depth term adds only ΔR²={r2_gain:.4f}; simpler T=T0+alpha*N preferred."
        )
    else:
        chosen = r_full
        chosen["_selection_reason"] = f"Depth adds ΔR²={r2_gain:.4f}; full model preferred."

    return chosen


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fit timing overhead models to benchmark results.")
    parser.add_argument("--db", required=True, help="Path to timing_results.sqlite")
    parser.add_argument("--backend", default=None, help="Filter by backend name")
    parser.add_argument("--experiment-name", default=None, dest="experiment_name")
    parser.add_argument(
        "--model",
        choices=["auto", "linear_N", "linear_N_depth", "linear_N_qt", "all"],
        default="auto",
    )
    args = parser.parse_args()

    df = load_timing_jobs(args.db)
    if args.backend:
        df = df[df["backend"] == args.backend]
    if args.experiment_name:
        df = df[df["experiment_name"] == args.experiment_name]

    print(f"Loaded {len(df)} rows (backend={args.backend}, experiment={args.experiment_name})\n")

    if args.model in ("auto", "all"):
        print("=== AUTO / RECOMMENDED MODEL ===")
        r = auto_fit(df)
        _print_result(r)

    if args.model in ("linear_N", "all"):
        print("\n=== MODEL: T = T0 + alpha*N ===")
        _print_result(fit_linear_N(df))

    if args.model in ("linear_N_depth", "all"):
        print("\n=== MODEL: T = T0 + alpha*N + beta*N*depth ===")
        _print_result(fit_linear_N_depth(df))

    if args.model in ("linear_N_qt", "all"):
        print("\n=== MODEL: T = T0 + alpha*N + beta*QT ===")
        _print_result(fit_linear_N_qt(df))

    print("\n=== PER-CIRCUIT OVERHEAD TABLE ===")
    pco = compute_per_circuit_overhead(df)
    print(pco.to_string(index=False))


def _print_result(d: Dict):
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, float):
            print(f"  {k}: {v:.6f}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
