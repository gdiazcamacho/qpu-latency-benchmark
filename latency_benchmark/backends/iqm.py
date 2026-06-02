"""
IQM backend adapter.

IQM Resonance provides rich per-circuit timing events via job.result().
This adapter captures them and stores them in the timing_events table,
enabling the linear_N_qt model (T = T0 + alpha*N + beta*estimated_QT).

Setup
-----
Install the IQM Qiskit provider:
    pip install qiskit-iqm

Set environment variables or pass options in iqm_timing.yaml:
    IQM_TOKEN  — bearer token for IQM Resonance
    url        — backend URL (e.g. https://cocos.resonance.meetiqm.com/helios)

Timing events extracted
-----------------------
For each circuit in the result, if `result.results[i].header` or the
IQM-specific metadata contains timing fields, they are stored as
`timing_events` rows with:
    event_name  : e.g. "compile", "execute", "readout"
    timestamp   : ISO string if available
    duration    : seconds
"""

import os
from typing import Any, Dict, Optional

from .base import BackendAdapter


class IQMBackendAdapter(BackendAdapter):
    name = "iqm"

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None, **kwargs):
        self.url = url or os.environ.get("IQM_SERVER_URL", "")
        self.token = token or os.environ.get("IQM_TOKEN", "")
        self.options = kwargs
        self._backend = None

    def get_backend(self):
        if self._backend is not None:
            return self._backend

        if not self.url:
            raise RuntimeError(
                "IQM backend URL not set. Provide 'url' in iqm_timing.yaml or set "
                "IQM_SERVER_URL environment variable."
            )

        try:
            from iqm.qiskit_iqm import IQMProvider
        except ImportError as exc:
            raise ImportError(
                "qiskit-iqm is not installed. Run: pip install qiskit-iqm"
            ) from exc

        provider = IQMProvider(self.url)
        self._backend = provider.get_backend()
        return self._backend

    def metadata(self) -> Dict[str, Any]:
        meta = {"url": self.url}
        if self._backend is not None:
            try:
                cfg = self._backend.configuration()
                meta["backend_name"] = cfg.backend_name
                meta["n_qubits"] = cfg.n_qubits
            except Exception:
                pass
        return meta

    def extract_timing_events(self, result, job_db_id: int) -> list:
        """
        Parse IQM result object for per-circuit timing metadata.

        Returns a list of dicts ready for insertion into timing_events.
        IQM stores timing in result.results[i].header.metadata or
        as calibration/execution timestamps depending on SDK version.
        Adapt the field names below to match your SDK version.
        """
        events = []
        if result is None:
            return events

        for i, exp_result in enumerate(getattr(result, "results", [])):
            header = getattr(exp_result, "header", None)
            if header is None:
                continue
            metadata = getattr(header, "metadata", {}) or {}

            # IQM SDK >= 15: timing keys may be 'compile_time', 'execution_time', etc.
            for key in ("compile_time", "execution_time", "readout_time", "total_time"):
                val = metadata.get(key)
                if val is not None:
                    events.append({
                        "timing_job_id": job_db_id,
                        "circuit_index": i,
                        "event_name": key,
                        "timestamp": None,
                        "duration": float(val),
                    })

        return events
