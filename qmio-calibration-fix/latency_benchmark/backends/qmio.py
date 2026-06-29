import glob
import os

from .base import BackendAdapter


# Default location for CESGA QMIO calibration files, named like
# 2026_03_13__12_00_01.json, sorted lexicographically == chronologically.
DEFAULT_CALIBRATION_DIR = "/opt/cesga/qmio/hpc/calibrations"
CALIBRATION_GLOB = "*.json"


def find_latest_calibration_file(directory: str = DEFAULT_CALIBRATION_DIR) -> str:
    """Return the path to the most recent calibration JSON in `directory`.

    Calibration files are named like `YYYY_MM_DD__HH_MM_SS.json`, so a plain
    lexicographic sort is equivalent to chronological order.
    """
    pattern = os.path.join(directory, CALIBRATION_GLOB)
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise RuntimeError(
            f"No calibration files found in {directory!r} (pattern {pattern!r})."
        )
    return candidates[-1]


class QmioBackendAdapter(BackendAdapter):
    name = "qmio"

    def __init__(self, **kwargs):
        self.options = kwargs

    def get_backend(self):
        from qmiotools.integrations.qiskitqmio import QmioBackend

        calibration_file = self.options.get("calibration_file")
        calibration_dir = self.options.get("calibration_dir", DEFAULT_CALIBRATION_DIR)

        if not calibration_file:
            calibration_file = find_latest_calibration_file(calibration_dir)

        return QmioBackend(calibration_file=calibration_file)

    def metadata(self):
        return {"backend_options": self.options}
