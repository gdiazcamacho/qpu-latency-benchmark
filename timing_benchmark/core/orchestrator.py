import json
import os
import time
from datetime import datetime, timezone
from statistics import mean
from typing import Dict

from qiskit import transpile

from .database import TimingDatabase
from .models import TimingJobRecord
from timing_benchmark.experiments.builders.synthetic_circuits import build_circuit_batch
from timing_benchmark.experiments.strategies.matrix import expand_matrix
from timing_benchmark.backends.factory import make_backend_adapter


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
        points = expand_matrix(self.config["matrix"])
        print(f"Running {len(points)} timing matrix points on backend={self.backend_name}")

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
            # Some custom backends may not support qiskit transpile cleanly.
            # Fall back to raw circuits, but record the issue.
            circuits_to_run = circuits
            transpiled_depths = [c.depth() for c in circuits]
            print(f"Transpile warning: {exc}", flush=True)

        walltime_backend_run = None
        walltime_result_wait = None
        walltime_total = None
        success = 0
        error_message = None
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

            metadata["job_id"] = getattr(job, "job_id", lambda: None)()
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
        self.db.save_job(record)
