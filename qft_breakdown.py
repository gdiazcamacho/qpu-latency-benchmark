"""
Diagnostic: split walltime into backend_run vs result_wait, per n_qubits,
to check whether QExa20's near-zero R2 on the linear n_qubits fit is due to
a large, roughly-constant per-circuit queue overhead swamping the
circuit-size signal.
"""
import sqlite3
import pandas as pd

DB = "output/db/timing_results_2026-07-06.sqlite"

con = sqlite3.connect(DB)
df = pd.read_sql_query(
    "SELECT n_qubits, transpiled_depth_mean, walltime_backend_run, "
    "walltime_result_wait, walltime_total "
    "FROM timing_jobs WHERE experiment_name='qft_inverse_qexa20' AND success=1",
    con,
)
print("=== QExa20: per n_qubits breakdown ===")
print(df.groupby("n_qubits")[
    ["transpiled_depth_mean", "walltime_backend_run",
     "walltime_result_wait", "walltime_total"]
].agg(["mean", "std"]))

print("\n=== QExa20: overall mean run vs wait (is one dominant and roughly constant?) ===")
print(df[["walltime_backend_run", "walltime_result_wait"]].agg(["mean", "std"]))
