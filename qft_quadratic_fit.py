"""
Quadratic fit T = a + b*n_qubits + c*n_qubits^2 for the QFT-inverse probe.

Rationale: transpiled circuit depth for inverse-QFT scales as O(n^2)
(n(n-1)/2 controlled-phase gates), so if walltime tracks circuit execution
cost rather than a flat per-job overhead, a quadratic term should improve
the fit meaningfully over pure linear -- this is the QFT-specific analogue
of your existing linear_N vs linear_N_depth model-selection logic.
"""
import sqlite3
import numpy as np
import pandas as pd

DB = "output/db/timing_results_2026-07-06.sqlite"


def fit_quadratic(experiment_name, db=DB):
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT n_qubits, walltime_total FROM timing_jobs "
        "WHERE experiment_name=? AND success=1",
        con, params=(experiment_name,),
    )
    if len(df) < 4:
        print(f"{experiment_name}: not enough rows ({len(df)})")
        return

    n = df["n_qubits"].to_numpy(float)
    y = df["walltime_total"].to_numpy(float)

    # Linear fit
    X_lin = np.column_stack([np.ones(len(n)), n])
    coef_lin, *_ = np.linalg.lstsq(X_lin, y, rcond=None)
    pred_lin = X_lin @ coef_lin
    r2_lin = 1 - np.sum((y - pred_lin) ** 2) / np.sum((y - y.mean()) ** 2)

    # Quadratic fit
    X_quad = np.column_stack([np.ones(len(n)), n, n**2])
    coef_quad, *_ = np.linalg.lstsq(X_quad, y, rcond=None)
    pred_quad = X_quad @ coef_quad
    r2_quad = 1 - np.sum((y - pred_quad) ** 2) / np.sum((y - y.mean()) ** 2)

    print(f"\n=== {experiment_name} (n={len(df)} rows) ===")
    print(f"Linear:    T = {coef_lin[0]:.3f} + {coef_lin[1]:.4f}*n         | R2={r2_lin:.4f}")
    print(f"Quadratic: T = {coef_quad[0]:.3f} + {coef_quad[1]:.4f}*n + {coef_quad[2]:.4f}*n^2 | R2={r2_quad:.4f}")
    print(f"R2 improvement from quadratic term: {r2_quad - r2_lin:+.4f}")


fit_quadratic("qft_inverse_qmio")
fit_quadratic("qft_inverse_qexa20")
