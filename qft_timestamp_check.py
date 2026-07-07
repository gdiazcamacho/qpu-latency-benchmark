"""
Check whether QExa20 wait time correlates with submission order / wall-clock
time (queue congestion drifting during the run) rather than n_qubits.
"""
import sqlite3
import pandas as pd

DB = "output/db/timing_results_2026-07-06.sqlite"

con = sqlite3.connect(DB)
df = pd.read_sql_query(
    "SELECT id, timestamp, n_qubits, repetition, walltime_result_wait, walltime_total "
    "FROM timing_jobs WHERE experiment_name='qft_inverse_qexa20' AND success=1 "
    "ORDER BY id",
    con,
)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["elapsed_s"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds()

print(df[["id", "elapsed_s", "n_qubits", "repetition", "walltime_result_wait"]].to_string(index=False))
print(f"\nCorrelation (wait vs elapsed time):   {df['walltime_result_wait'].corr(df['elapsed_s']):.3f}")
print(f"Correlation (wait vs n_qubits):        {df['walltime_result_wait'].corr(df['n_qubits']):.3f}")
print(f"Correlation (wait vs row insertion id): {df['walltime_result_wait'].corr(df['id']):.3f}")
