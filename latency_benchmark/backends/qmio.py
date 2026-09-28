import os
import re

from .base import BackendAdapter


# Default location for CESGA QMIO calibration files, named like
# 2026_03_13__12_00_01.json, sorted lexicographically == chronologically.
DEFAULT_CALIBRATION_DIR = "/opt/cesga/qmio/hpc/calibrations"

# Only match timestamped calibration snapshots (YYYY_MM_DD__HH_MM_SS.json).
# The calibrations directory also contains other files such as
# calib_exceptions.json, which are not full calibration snapshots and must
# not be picked up by "latest file" discovery.
CALIBRATION_FILENAME_RE = re.compile(r"^\d{4}_\d{2}_\d{2}__\d{2}_\d{2}_\d{2}\.json$")


def find_latest_calibration_file(directory: str = DEFAULT_CALIBRATION_DIR) -> str:
    """Return the path to the most recent calibration JSON in `directory`.

    Calibration snapshots are named like `YYYY_MM_DD__HH_MM_SS.json`, so a
    plain lexicographic sort over filenames matching that pattern is
    equivalent to chronological order. Other files in the calibrations
    directory (e.g. calib_exceptions.json) are ignored.
    """
    if not os.path.isdir(directory):
        raise RuntimeError(f"Calibration directory not found: {directory!r}.")

    candidates = sorted(
        f for f in os.listdir(directory) if CALIBRATION_FILENAME_RE.match(f)
    )
    if not candidates:
        raise RuntimeError(
            f"No timestamped calibration files (YYYY_MM_DD__HH_MM_SS.json) "
            f"found in {directory!r}."
        )
    return os.path.join(directory, candidates[-1])


# Wire formats QMIO's QmioBackend.run() can submit in. "qasm2" is the
# client library's own default (no flag passed); "qasm3" is selected via
# run(..., output_qasm3=True).
#
# QIR is deliberately NOT here. QMIO can accept QIR, but only through a
# different submission path entirely: QmioRuntimeService().backend("qpu")
# with raw bitcode from qiskit_qir.to_qir_module(), rather than
# QmioBackend.run(). That needs a separate adapter, not a run() flag --
# see wire_formats() docstring.
QMIO_WIRE_FORMATS = ("qasm2", "qasm3")


class QmioBackendAdapter(BackendAdapter):
    name = "qmio"

    def __init__(self, **kwargs):
        self.options = kwargs
        self._resolved_calibration_file = None

        wire_format = self.options.get("wire_format", "qasm2")
        if wire_format not in QMIO_WIRE_FORMATS:
            raise ValueError(
                f"Unsupported wire_format {wire_format!r} for qmio. "
                f"Supported: {list(QMIO_WIRE_FORMATS)}. "
                f"(QIR requires a separate submission path via "
                f"QmioRuntimeService and is not available as a run() flag.)"
            )
        self.wire_format = wire_format

    def supports_ir_formats(self) -> bool:
        """QMIO's QmioBackend.run() genuinely honours a caller-chosen wire
        format via output_qasm3, and the choice measurably changes real
        submission time -- not just local serialization cost.

        Measured on QMIO hardware (single-qubit randomized-benchmarking
        circuits, submission call timed directly): QASM3 cost roughly 3x
        the submission time of QASM2 at ~600-gate depth (10.1s vs 3.2s),
        and the gap widened with circuit size rather than staying a fixed
        offset. Submission time with no flag set matched QASM2's almost
        exactly, indicating QASM2 is the client's internal default.
        """
        return True

    def wire_formats(self):
        """Wire formats selectable via backend_options.wire_format.

        QIR is absent by design: QMIO does accept QIR, but through
        QmioRuntimeService + qiskit_qir bitcode rather than
        QmioBackend.run(), so it can't be expressed as a run() flag and
        would need its own adapter (a "qmio_qir" backend). Worth doing --
        QIR measured ~1.6x FASTER than QASM2 at the same depth in the
        same experiment referenced above -- but it is a separate
        submission path, not a variant of this one.
        """
        return QMIO_WIRE_FORMATS

    def run_options(self):
        # QmioBackend.run() defaults to its internal QASM2 path when
        # output_qasm3 is not passed, so only set the flag for qasm3
        # rather than passing output_qasm3=False explicitly (keeps the
        # default path byte-identical to not using this feature at all).
        if self.wire_format == "qasm3":
            return {"output_qasm3": True}
        return {}

    def get_backend(self):
        from qmiotools.integrations.qiskitqmio import QmioBackend

        calibration_file = self.options.get("calibration_file")
        calibration_dir = self.options.get("calibration_dir", DEFAULT_CALIBRATION_DIR)

        if not calibration_file:
            calibration_file = find_latest_calibration_file(calibration_dir)

        # Record what was ACTUALLY resolved and loaded, not just the config
        # value (which may be null/"auto"). Without this, metadata_json
        # can't distinguish runs on different calibration snapshots --
        # relevant since calibration drift can shift which physical qubits
        # are excluded, changing routing distance and therefore depth.
        self._resolved_calibration_file = calibration_file

        return QmioBackend(calibration_file=calibration_file)

    def metadata(self):
        meta = {"backend_options": self.options}
        if self._resolved_calibration_file:
            meta["resolved_calibration_file"] = self._resolved_calibration_file
        meta["wire_format"] = self.wire_format
        return meta