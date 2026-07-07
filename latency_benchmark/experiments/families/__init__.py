"""Circuit family registry.

A "family" groups related circuit builders and declares which sweep axes
are structurally valid for it. This is the single place that answers
"can I sweep depth for this family?" -- consulted by matrix.py to reject
nonsensical configs (e.g. sweeping logical_depth for the entangling
family, where depth is derived from n_qubits, not independently settable)
before they reach circuit building.
"""
from dataclasses import dataclass
from typing import Callable, Dict, Set

from qiskit import QuantumCircuit

from . import single_qubit
from . import entangling

# Axis names match matrix.py's canonical point-dict keys.
AXIS_N_CIRCUITS = "n_circuits"
AXIS_SHOTS = "shots"
AXIS_N_QUBITS = "n_qubits"
AXIS_DEPTH = "logical_depth"


@dataclass(frozen=True)
class FamilySpec:
    name: str
    build_fn: Callable[..., QuantumCircuit]
    valid_axes: Set[str]
    depth_is_independent: bool


FAMILY_REGISTRY: Dict[str, FamilySpec] = {
    "measure_only": FamilySpec(
        name="measure_only",
        build_fn=single_qubit.build_measure_only_circuit,
        valid_axes={AXIS_N_CIRCUITS, AXIS_SHOTS, AXIS_N_QUBITS},
        depth_is_independent=False,  # no gates at all; depth is always 0
    ),
    "single_qubit": FamilySpec(
        name="single_qubit",
        build_fn=single_qubit.build_single_qubit_layer_circuit,
        valid_axes={AXIS_N_CIRCUITS, AXIS_SHOTS, AXIS_N_QUBITS, AXIS_DEPTH},
        depth_is_independent=True,
    ),
    "qft": FamilySpec(
        name="qft",
        build_fn=entangling.build_qft_circuit,
        valid_axes={AXIS_N_CIRCUITS, AXIS_SHOTS, AXIS_N_QUBITS},
        depth_is_independent=False,
    ),
    "qft_no_swap": FamilySpec(
        name="qft_no_swap",
        build_fn=entangling.build_qft_no_swap_circuit,
        valid_axes={AXIS_N_CIRCUITS, AXIS_SHOTS, AXIS_N_QUBITS},
        depth_is_independent=False,
    ),
}


def get_family(name: str) -> FamilySpec:
    if name not in FAMILY_REGISTRY:
        raise ValueError(
            f"Unknown circuit family: {name!r}. "
            f"Available: {sorted(FAMILY_REGISTRY)}"
        )
    return FAMILY_REGISTRY[name]


def build_circuit_batch(n_circuits: int, n_qubits: int, depth: int,
                         circuit_family: str) -> list:
    """Build n_circuits copies of the requested family's circuit.

    Kept as a drop-in replacement for the old synthetic_circuits.py
    function of the same name/signature, so orchestrator.py needs no
    changes beyond the import path.
    """
    spec = get_family(circuit_family)
    base = spec.build_fn(n_qubits=n_qubits, depth=depth)

    circuits = []
    for i in range(n_circuits):
        circ = base.copy()
        circ.name = f"{circuit_family}_nq{n_qubits}_d{depth}_i{i}"
        circuits.append(circ)
    return circuits
