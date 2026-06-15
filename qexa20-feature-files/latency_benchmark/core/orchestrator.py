"""
Timing benchmark orchestrator.

Runs the full experiment matrix, times each job, and stores results in SQLite.
QExa20 backends additionally extract per-circuit timing events if available.
"""

import json
import os
import time
from datetime import datetime, timezone
from statistics import mean
from typing import Dict

from qiskit import transpile

from .database import TimingDatabase
from .models import TimingJobRecord
from latency_benchmark.experiments.builders.synthetic_circuits import build_circuit_batch
from latency_benchmark.experiments.strategies.matrix import expand_experiment
from latency_benchmark.backends.factory import make_backend_adapter


class TimingOrchestrator:
    def __init__(self, config: Dict):
        self.config = config
        self.db = TimingDatabase(config["output_db"])
        self.backend_name = config["backend"]
        self.backend_adapter = make_backend_adapter(
            self.backend_name,
            config.get("backend_options", {}),
        )
        self.backend = self.backend_adapter.get_backend()

    def run(self):
        points = expand_experiment(self.config)
        experiment_type = self.config.get("experiment_type", self.config.get("matrix", {}).get("experiment_type", "full_matrix"))
        print(f"Running {len(points)} {experiment_type} points on backend={self.backend_name}")

        for idx, point in enumerate(points, start=1):
            print(f"[{idx}/{len(points)}] {point}", flush=True)
            self._run_point(point)

    def _run_point(self, point: Dict):
        circuits = build_circuit_batch(
            n_circuits=point["n_circuits"],
            n_qubits=point["n_qubits"],
            depth=point["logical_depth"],
            circuit_family=point["circuit_family"],
        )

        transpiled_depths = None
        try:
            tcirc = transpile(circuits, backend=self.backend)
            transpiled_depths = [c.depth() for c in tcirc]
            circuits_to_run = tcirc
        except Exception as exc:
            circuits_to_run = circuits
            transpiled_depths = [c.depth() for c in circuits]
            print(f"Transpile warning: {exc}", flush=True)

        walltime_backend_run = None
        walltime_result_wait = None
        walltime_total = None
        success = 0
        error_message = None
        result = None
        job = None
        metadata = {
            "point": point,
            "backend_metadata": self.backend_adapter.metadata(),
        }

        t0 = time.perf_counter()
        try:
            job = self.backend.run(circuits_to_run, shots=point["shots"])
            t1 = time.perf_counter()
            result = job.result()
            t2 = time.perf_counter()

            walltime_backend_run = t1 - t0
            walltime_result_wait = t2 - t1
            walltime_total = t2 - t0
            success = 1

            job_id = None
            try:
                job_id = job.job_id() if callable(job.job_id) else job.job_id
            except Exception:
                pass
            metadata["job_id"] = job_id
            metadata["result_type"] = type(result).__name__

        except Exception as exc:
            t2 = time.perf_counter()
            walltime_total = t2 - t0
            error_message = repr(exc)
            print(f"ERROR: {error_message}", flush=True)

        record = TimingJobRecord(
            backend=self.backend_name,
            experiment_name=self.config["experiment_name"],
            timestamp=datetime.now(timezone.utc).isoformat(),

            n_circuits=point["n_circuits"],
            circuit_family=point["circuit_family"],
            logical_depth=point["logical_depth"],
            n_qubits=point["n_qubits"],
            shots=point["shots"],
            repetition=point["repetition"],

            transpiled_depth_mean=float(mean(transpiled_depths)) if transpiled_depths else None,
            transpiled_depth_max=int(max(transpiled_depths)) if transpiled_depths else None,

            walltime_total=walltime_total,
            walltime_backend_run=walltime_backend_run,
            walltime_result_wait=walltime_result_wait,

            slurm_job_id=os.environ.get("SLURM_JOB_ID"),
            success=success,
            error_message=error_message,
            metadata_json=json.dumps(metadata, default=str),
        )
        job_db_id = self.db.save_job(record)

        # QExa20: extract per-circuit timing events if the adapter supports it
        if success and result is not None and hasattr(self.backend_adapter, "extract_timing_events"):
            events = self.backend_adapter.extract_timing_events(result, job_db_id)
            if events:
                self.db.save_timing_events(events)
                print(f"  Stored {len(events)} timing events for job db_id={job_db_id}", flush=True)
