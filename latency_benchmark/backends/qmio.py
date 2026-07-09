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


class QmioBackendAdapter(BackendAdapter):
    name = "qmio"

    def __init__(self, **kwargs):
        self.options = kwargs
        self._resolved_calibration_file = None

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
        return meta
