"""Default sweep values per (family, axis) combination.

This is the single table a collaborator edits to change "what's normal"
for a given probe -- CLI --values/--repetitions/etc. override these for
one-off custom runs without needing a new file.

Each entry's "sweep" key names the point-dict field that gets swept
(matches matrix.py's canonical keys); "values" is the default sweep list;
any other keys are fixed controls for that axis.
"""
from typing import Any, Dict, Tuple

AxisKey = Tuple[str, str]  # (family, axis)

AXIS_DEFAULTS: Dict[AxisKey, Dict[str, Any]] = {
    ("single_qubit", "batch"): {
        "sweep": "n_circuits", "values": [1, 2, 4, 8, 16, 32],
        "n_qubits": 2, "shots": 1000, "logical_depth": 4,
    },
    ("single_qubit", "shot"): {
        "sweep": "shots", "values": [10, 100, 1000, 10000],
        "n_qubits": 2, "n_circuits": 1, "logical_depth": 4,
    },
    ("single_qubit", "width"): {
        "sweep": "n_qubits", "values": [1, 2, 4, 8, 16],
        "n_circuits": 1, "shots": 1000, "logical_depth": 4,
    },
    ("single_qubit", "depth"): {
        "sweep": "logical_depth", "values": [0, 1, 2, 4, 8, 16, 32, 64],
        "n_qubits": 2, "n_circuits": 1, "shots": 1000,
    },

    ("qft", "batch"): {
        "sweep": "n_circuits", "values": [1, 2, 4, 8],
        "n_qubits": 6, "shots": 1000,
    },
    ("qft", "shot"): {
        "sweep": "shots", "values": [10, 100, 1000, 10000],
        "n_qubits": 6, "n_circuits": 1,
    },
    ("qft", "width"): {
        "sweep": "n_qubits", "values": [2, 4, 6, 8, 10],
        "n_circuits": 1, "shots": 1000,
    },

    ("qft_no_swap", "batch"): {
        "sweep": "n_circuits", "values": [1, 2, 4, 8],
        "n_qubits": 6, "shots": 1000,
    },
    ("qft_no_swap", "shot"): {
        "sweep": "shots", "values": [10, 100, 1000, 10000],
        "n_qubits": 6, "n_circuits": 1,
    },
    ("qft_no_swap", "width"): {
        "sweep": "n_qubits", "values": [2, 4, 6, 8, 10],
        "n_circuits": 1, "shots": 1000,
    },

    # measure_only is used for cheap/queue-noise-style probes: any axis
    # works, but it has no depth of its own (depth_is_independent=False),
    # so "depth" is intentionally absent here -- consistent with the
    # family registry's validation.
    ("measure_only", "batch"): {
        "sweep": "n_circuits", "values": [1, 2, 4, 8, 16, 32],
        "n_qubits": 1, "shots": 1000,
    },
    ("measure_only", "shot"): {
        "sweep": "shots", "values": [10, 100, 1000, 10000],
        "n_qubits": 1, "n_circuits": 1,
    },
    ("measure_only", "width"): {
        "sweep": "n_qubits", "values": [1, 2, 4, 8, 16],
        "n_circuits": 1, "shots": 1000,
    },
}


def get_axis_default(family: str, axis: str) -> Dict[str, Any]:
    key = (family, axis)
    if key not in AXIS_DEFAULTS:
        valid_axes = sorted({a for (f, a) in AXIS_DEFAULTS if f == family})
        raise ValueError(
            f"No default sweep for family={family!r}, axis={axis!r}. "
            f"Valid axes for {family!r}: {valid_axes}"
        )
    return AXIS_DEFAULTS[key]
