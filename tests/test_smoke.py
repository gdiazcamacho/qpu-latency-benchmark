"""End-to-end smoke test on the local `fake` backend.

Runs one tiny sweep per axis through the real CLI and checks that every
point lands in the SQLite database as a successful job. No credentials or
hardware access needed.
"""
import sqlite3
import subprocess
import sys

import pytest

CASES = [
    ("qft", "width", "2,4"),
    ("single_qubit", "shot", "10,100"),
    ("single_qubit", "batch", "1,2"),
    ("single_qubit", "depth", "0,8"),
]


@pytest.mark.parametrize("family,axis,values", CASES)
def test_fake_sweep(tmp_path, family, axis, values):
    db = tmp_path / "smoke.sqlite"
    subprocess.run(
        [sys.executable, "-m", "latency_benchmark.run_experiment",
         "--backend", "fake", "--family", family, "--axis", axis,
         "--values", values, "--repetitions", "1", "--output-db", str(db)],
        check=True,
    )
    n, ok = sqlite3.connect(db).execute(
        "select count(*), sum(success) from timing_jobs").fetchone()
    assert n == len(values.split(","))
    assert ok == n
