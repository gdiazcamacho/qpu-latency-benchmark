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


def test_external_adapter_via_backend_config(tmp_path):
    """A backend config outside the repo can name any importable adapter class."""
    cfg = tmp_path / "mybackend.yaml"
    cfg.write_text(
        "backend: mybackend\n"
        "adapter: latency_benchmark.backends.fake:FakeBackendAdapter\n"
        f"output_db: {tmp_path / 'unused.sqlite'}\n"
        "backend_options: {}\n"
    )
    db = tmp_path / "ext.sqlite"
    subprocess.run(
        [sys.executable, "-m", "latency_benchmark.run_experiment",
         "--backend-config", str(cfg), "--family", "single_qubit", "--axis", "shot",
         "--values", "10", "--repetitions", "1", "--output-db", str(db)],
        check=True,
    )
    backend, ok = sqlite3.connect(db).execute(
        "select backend, success from timing_jobs").fetchone()
    assert (backend, ok) == ("mybackend", 1)
