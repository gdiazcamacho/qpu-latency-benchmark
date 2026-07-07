"""Fit-model registry, keyed by (circuit_family, sweep_axis).

Replaces always-linear fitting with an explicit lookup: single-qubit
probes are linear in every axis; QFT is quadratic in n_qubits (O(n^2)
gate count) but linear in n_circuits/shots at fixed n_qubits. Prevents
the mistake of eyeballing which model to use per probe, made once here
instead of re-derived by hand each time (as we did for the QFT width
probe this session).
"""
import numpy as np


def linear_model(x: np.ndarray, y: np.ndarray) -> dict:
    X = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    r2 = _r2(y, pred)
    return {
        "model": "linear",
        "formula": "T = a + b*x",
        "params": {"a": coef[0], "b": coef[1]},
        "r2": r2,
    }


def quadratic_model(x: np.ndarray, y: np.ndarray) -> dict:
    X = np.column_stack([np.ones(len(x)), x, x**2])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    r2 = _r2(y, pred)
    return {
        "model": "quadratic",
        "formula": "T = a + b*x + c*x^2",
        "params": {"a": coef[0], "b": coef[1], "c": coef[2]},
        "r2": r2,
    }


def _r2(y, pred):
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


# axis names here are matrix.py's canonical sweep_variable values
MODEL_REGISTRY = {
    ("single_qubit", "n_circuits"):    linear_model,
    ("single_qubit", "shots"):         linear_model,
    ("single_qubit", "n_qubits"):      linear_model,
    ("single_qubit", "logical_depth"): linear_model,

    ("measure_only", "n_circuits"): linear_model,
    ("measure_only", "shots"):      linear_model,
    ("measure_only", "n_qubits"):   linear_model,

    ("qft", "n_circuits"): linear_model,
    ("qft", "shots"):      linear_model,
    ("qft", "n_qubits"):   quadratic_model,   # O(n^2) gate count

    ("qft_no_swap", "n_circuits"): linear_model,
    ("qft_no_swap", "shots"):      linear_model,
    ("qft_no_swap", "n_qubits"):   quadratic_model,
}


def get_model(circuit_family: str, sweep_axis: str):
    key = (circuit_family, sweep_axis)
    if key not in MODEL_REGISTRY:
        raise ValueError(
            f"No registered model for circuit_family={circuit_family!r}, "
            f"sweep_axis={sweep_axis!r}. Falling back to linear_model is "
            f"available by calling it directly, but add an explicit entry "
            f"here once you know which model is right -- don't guess."
        )
    return MODEL_REGISTRY[key]
