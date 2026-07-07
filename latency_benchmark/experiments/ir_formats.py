"""
Measures circuit serialization cost across intermediate representations.

This is decoupled from actual backend submission: it does NOT change what
gets sent to backend.run(), it only measures how expensive it is to produce
each representation from the same (transpiled) circuit. Whether a given
backend's run() call could actually be made to consume one of these formats
directly -- and whether that would change real wire/execution time -- is a
separate, backend-adapter-specific question (see module docstring note below).

Open question, not yet answered: does mqss.qiskit_adapter's
MQSSQiskitBackend.run() accept a pre-serialized payload in a chosen format,
or does it always internally reconvert regardless of input? Check the
adapter's source/signature on the cluster before treating IR format as a
variable that affects actual submitted walltime, not just local compile cost.
"""
import time
from typing import Dict


def measure_serialization_times(circuit, formats=("qasm2", "qasm3")) -> Dict[str, float]:
    """Return {format_name: seconds} for producing each representation.

    formats can include "qasm2", "qasm3", "qir". "qir" requires the
    qiskit-qir / pyqir packages -- not installed by default, skipped with
    a note if unavailable rather than failing the whole probe.
    """
    results = {}

    if "qasm2" in formats:
        from qiskit import qasm2
        t0 = time.perf_counter()
        qasm2.dumps(circuit)
        results["serialize_qasm2"] = time.perf_counter() - t0

    if "qasm3" in formats:
        from qiskit import qasm3
        t0 = time.perf_counter()
        qasm3.dumps(circuit)
        results["serialize_qasm3"] = time.perf_counter() - t0

    if "qir" in formats:
        try:
            from qiskit_qir import to_qir_module
            t0 = time.perf_counter()
            to_qir_module(circuit)
            results["serialize_qir"] = time.perf_counter() - t0
        except ImportError:
            results["serialize_qir"] = None  # not installed; log as skipped, not a failure

    return results
