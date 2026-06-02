import sqlite3
from pathlib import Path
from typing import List, Optional
from .models import TimingJobRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS timing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    backend TEXT,
    experiment_name TEXT,
    timestamp TEXT,

    n_circuits INTEGER,
    circuit_family TEXT,
    logical_depth INTEGER,
    n_qubits INTEGER,
    shots INTEGER,
    repetition INTEGER,

    transpiled_depth_mean REAL,
    transpiled_depth_max INTEGER,

    walltime_total REAL,
    walltime_backend_run REAL,
    walltime_result_wait REAL,

    slurm_job_id TEXT,
    success INTEGER,
    error_message TEXT,

    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS timing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timing_job_id INTEGER REFERENCES timing_jobs(id),
    circuit_index INTEGER,
    event_name TEXT,
    timestamp TEXT,
    duration REAL
);
"""


class TimingDatabase:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_schema(self):
        with self._connect() as con:
            con.executescript(SCHEMA)

    def save_job(self, record: TimingJobRecord) -> int:
        data = record.to_dict()
        columns = list(data.keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO timing_jobs ({', '.join(columns)}) VALUES ({placeholders})"
        with self._connect() as con:
            cur = con.execute(sql, [data[c] for c in columns])
            return int(cur.lastrowid)

    def save_timing_events(self, events: List[dict]):
        """Insert a batch of timing event dicts into timing_events."""
        if not events:
            return
        keys = ["timing_job_id", "circuit_index", "event_name", "timestamp", "duration"]
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT INTO timing_events ({', '.join(keys)}) VALUES ({placeholders})"
        rows = [[e.get(k) for k in keys] for e in events]
        with self._connect() as con:
            con.executemany(sql, rows)
