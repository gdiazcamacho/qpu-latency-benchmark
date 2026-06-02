"""Parameter expansion for latency characterization experiments.

Two config styles are supported.

Legacy full matrix:

matrix:
  n_circuits: [1, 2]
  depths: [0, 4]
  shots: [1000]
  n_qubits: [2]

Probe style:

experiment_type: shot_scaling
sweep:
  shots: [10, 100, 1000]
controls:
  n_circuits: 1
  depth: 4
  n_qubits: 2

The returned point dictionaries always use the same normalized keys:
    n_circuits, logical_depth, shots, n_qubits, repetition, circuit_family,
    experiment_type, sweep_variable
"""

import random
from typing import Any, Dict, Iterable, List


_CANONICAL_KEYS = {
    "depth": "logical_depth",
    "depths": "logical_depth",
    "logical_depth": "logical_depth",
    "logical_depths": "logical_depth",
    "n_circuit": "n_circuits",
    "n_circuits": "n_circuits",
    "shots": "shots",
    "n_qubit": "n_qubits",
    "n_qubits": "n_qubits",
}

_DEFAULT_POINT = {
    "n_circuits": 1,
    "logical_depth": 0,
    "shots": 1000,
    "n_qubits": 2,
    "circuit_family": "single_qubit_layers",
}


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _canonical_key(key: str) -> str:
    if key not in _CANONICAL_KEYS:
        raise ValueError(f"Unsupported sweep/control key: {key}")
    return _CANONICAL_KEYS[key]


def _normalize_point(point: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(_DEFAULT_POINT)
    out.update(point)

    out["n_circuits"] = int(out["n_circuits"])
    out["logical_depth"] = int(out["logical_depth"])
    out["shots"] = int(out["shots"])
    out["n_qubits"] = int(out["n_qubits"])
    out["repetition"] = int(out.get("repetition", 0))
    out["circuit_family"] = str(out.get("circuit_family", "single_qubit_layers"))
    out["experiment_type"] = str(out.get("experiment_type", "full_matrix"))
    out["sweep_variable"] = out.get("sweep_variable")
    return out


def expand_matrix(matrix_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand the original full-factorial matrix config."""
    points = []
    repetitions = int(matrix_cfg.get("repetitions", 1))

    for n_circuits in matrix_cfg["n_circuits"]:
        for depth in matrix_cfg["depths"]:
            for shots in matrix_cfg["shots"]:
                for n_qubits in matrix_cfg["n_qubits"]:
                    for repetition in range(repetitions):
                        points.append(_normalize_point({
                            "n_circuits": n_circuits,
                            "logical_depth": depth,
                            "shots": shots,
                            "n_qubits": n_qubits,
                            "repetition": repetition,
                            "circuit_family": matrix_cfg.get("circuit_family", "single_qubit_layers"),
                            "experiment_type": matrix_cfg.get("experiment_type", "full_matrix"),
                            "sweep_variable": "full_matrix",
                        }))

    if matrix_cfg.get("randomize_order", False):
        random.shuffle(points)

    return points


def expand_probe(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand a one-dimensional probe config with sweep + controls."""
    experiment_type = config.get("experiment_type", "probe")
    sweep = config.get("sweep", {})
    controls = config.get("controls", {})

    if len(sweep) != 1:
        raise ValueError("Probe configs must define exactly one sweep variable.")

    raw_sweep_key, sweep_values = next(iter(sweep.items()))
    sweep_key = _canonical_key(raw_sweep_key)

    base = {}
    for k, v in controls.items():
        if k in ("repetitions", "randomize_order"):
            continue
        if k == "circuit_family":
            base[k] = v
        else:
            base[_canonical_key(k)] = v

    repetitions = int(config.get("repetitions", controls.get("repetitions", 1)))
    circuit_family = config.get("circuit_family", controls.get("circuit_family", "single_qubit_layers"))
    randomize_order = bool(config.get("randomize_order", controls.get("randomize_order", False)))

    points = []
    for value in _as_list(sweep_values):
        for repetition in range(repetitions):
            point = dict(base)
            point[sweep_key] = value
            point["repetition"] = repetition
            point["circuit_family"] = circuit_family
            point["experiment_type"] = experiment_type
            point["sweep_variable"] = sweep_key
            points.append(_normalize_point(point))

    if randomize_order:
        random.shuffle(points)

    return points


def expand_experiment(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand either legacy matrix configs or new probe configs."""
    if "matrix" in config:
        return expand_matrix(config["matrix"])
    if "sweep" in config and "controls" in config:
        return expand_probe(config)
    raise ValueError("Config must contain either 'matrix' or both 'sweep' and 'controls'.")
