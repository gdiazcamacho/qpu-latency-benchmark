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
from latency_benchmark.experiments.families import build_circuit_batch
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
        # Optional, opt-in, off by default: local circuit serialization
        # cost per format (e.g. ["qasm2", "qasm3"]). Decoupled diagnostic --
        # never affects walltime_total or what's actually submitted. See
        # experiments/ir_formats.py for details and open questions.
        self.ir_formats = config.get("ir_formats", [])

        # Fail loudly rather than silently ignoring a requested wire
        # format on a backend that can't honour it -- a silently-ignored
        # experimental control produces results that look meaningful but
        # aren't.
        requested_wire_format = config.get("backend_options", {}).get("wire_format")
        if requested_wire_format is not None and not self.backend_adapter.supports_ir_formats():
            raise ValueError(
                f"backend_options.wire_format={requested_wire_format!r} was requested, but the "
                f"{self.backend_name!r} adapter does not support caller-chosen wire formats "
                f"(supports_ir_formats() is False), so the setting would be silently ignored. "
                f"Remove it, or implement wire-format support in that adapter."
            )

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

        if getattr(self.backend_adapter, "supports_batch_submission", lambda: True)():
            self._run_point_batched(point, circuits)
        else:
            self._run_point_per_circuit(point, circuits)

    def _run_point_batched(self, point: Dict, circuits):
        # Read from backend_options so both submission paths (batched here,
        # per-circuit in _run_point_per_circuit) use the same explicit,
        # config-visible optimization_level -- previously this path had no
        # override at all and silently used Qiskit's own default (level 2),
        # while the per-circuit path defaulted to 0. That mismatch made any
        # transpiled-depth comparison between backends using different
        # submission paths (e.g. QMIO vs QExa20) meaningless: depth
        # differences reflected the optimization-level mismatch, not real
        # hardware connectivity. Both configs/backends/*.yaml now set this
        # explicitly to the same value for fair comparison.
        optimization_level = self.config.get("backend_options", {}).get("optimization_level", 0)
        seed_transpiler = self.config.get("backend_options", {}).get("seed_transpiler", 42)

        transpiled_depths = None
        try:
            tcirc = transpile(circuits, backend=self.backend, optimization_level=optimization_level,
                              seed_transpiler=seed_transpiler)
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
            "submission_mode": "batched",
        }

        # Diagnostic only, never affects walltime_total: measure local
        # serialization cost on one representative circuit if requested.
        ir_times = self._measure_ir_times(circuits_to_run)

        run_kwargs = self.backend_adapter.run_options()

        t0 = time.perf_counter()
        try:
            job = self.backend.run(circuits_to_run, shots=point["shots"], **run_kwargs)
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

        self._save_record(point, transpiled_depths, walltime_total,
                          walltime_backend_run, walltime_result_wait,
                          success, error_message, metadata, result,
                          ir_times=ir_times)

    def _run_point_per_circuit(self, point: Dict, circuits):
        """Submit and time circuits one at a time.

        Used for backends (e.g. QExa20 via MQSS) that do not support batched
        circuit submission. walltime_backend_run / walltime_result_wait /
        walltime_total are accumulated as the sum across all circuits in the
        point, so that T = T0 + alpha*N remains comparable to batched
        backends: the total cost still scales with N, even though it is
        measured as N sequential calls instead of one batched call.
        """
        optimization_level = self.config.get("backend_options", {}).get("optimization_level", 0)
        initial_layout = self.config.get("backend_options", {}).get("initial_layout")
        decompose_to_basis = self.config.get("backend_options", {}).get("decompose_to_basis", False)
        seed_transpiler = self.config.get("backend_options", {}).get("seed_transpiler", 42)

        transpiled_depths = []
        transpiled_circuits = []
        try:
            for circ in circuits:
                if hasattr(self.backend_adapter, "transpile_circuit"):
                    tqc = self.backend_adapter.transpile_circuit(
                        circ, self.backend,
                        optimization_level=optimization_level,
                        initial_layout=initial_layout,
                        decompose_to_basis=decompose_to_basis,
                        seed_transpiler=seed_transpiler,
                    )
                else:
                    tqc = transpile(circ, backend=self.backend,
                                     optimization_level=optimization_level,
                                     initial_layout=initial_layout,
                                     seed_transpiler=seed_transpiler)
                transpiled_circuits.append(tqc)
                transpiled_depths.append(tqc.depth())
        except Exception as exc:
            transpiled_circuits = list(circuits)
            transpiled_depths = [c.depth() for c in circuits]
            print(f"Transpile warning: {exc}", flush=True)

        walltime_backend_run = 0.0
        walltime_result_wait = 0.0
        success = 0
        error_message = None
        last_result = None
        job_ids = []
        metadata = {
            "point": point,
            "backend_metadata": self.backend_adapter.metadata(),
            "submission_mode": "per_circuit",
        }

        # Diagnostic only, never affects walltime_total.
        ir_times = self._measure_ir_times(transpiled_circuits)

        run_kwargs = self.backend_adapter.run_options()

        t_point_start = time.perf_counter()
        try:
            for tqc in transpiled_circuits:
                t0 = time.perf_counter()
                job = self.backend.run(tqc, shots=point["shots"], **run_kwargs)
                t1 = time.perf_counter()
                result = job.result()
                t2 = time.perf_counter()

                walltime_backend_run += (t1 - t0)
                walltime_result_wait += (t2 - t1)
                last_result = result

                try:
                    job_id = job.job_id() if callable(job.job_id) else job.job_id
                except Exception:
                    job_id = None
                job_ids.append(job_id)

            success = 1
            metadata["job_ids"] = job_ids
            metadata["result_type"] = type(last_result).__name__ if last_result is not None else None

        except Exception as exc:
            error_message = repr(exc)
            print(f"ERROR: {error_message}", flush=True)

        t_point_end = time.perf_counter()
        walltime_total = (
            (walltime_backend_run + walltime_result_wait)
            if success
            else (t_point_end - t_point_start)
        )

        self._save_record(point, transpiled_depths, walltime_total,
                          walltime_backend_run if success else None,
                          walltime_result_wait if success else None,
                          success, error_message, metadata, last_result,
                          ir_times=ir_times)

    def _measure_ir_times(self, circuits) -> Dict:
        """Diagnostic only: local serialization cost for one representative
        circuit, if ir_formats was requested. Never affects walltime_total
        or what's actually submitted to the backend."""
        if not self.ir_formats or not circuits:
            return {}
        from latency_benchmark.experiments.ir_formats import measure_serialization_times
        try:
            return measure_serialization_times(circuits[0], formats=self.ir_formats)
        except Exception as exc:
            print(f"IR-format timing warning: {exc}", flush=True)
            return {}

    def _save_record(self, point: Dict, transpiled_depths, walltime_total,
                      walltime_backend_run, walltime_result_wait,
                      success, error_message, metadata, result, ir_times=None):

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

        # IR-format serialization diagnostics, if requested (opt-in, off by default)
        if ir_times:
            events = [
                {"timing_job_id": job_db_id, "circuit_index": 0, "event_name": name, "duration": dur}
                for name, dur in ir_times.items() if dur is not None
            ]
            if events:
                self.db.save_timing_events(events)