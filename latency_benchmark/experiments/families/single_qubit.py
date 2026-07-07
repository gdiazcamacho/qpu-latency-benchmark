"""Single-qubit circuit family: independent single-qubit gates per qubit.

Depth is an independent, freely-settable parameter here -- unlike the
entangling family, these circuits have no qubit-qubit interaction, so
depth and qubit count are orthogonal knobs.
"""
from qiskit import QuantumCircuit


def build_measure_only_circuit(n_qubits: int, **_ignored) -> QuantumCircuit:
    """Minimal circuit: just measurement. Cheapest possible probe --
    useful for isolating orchestration/queue overhead from any gate cost."""
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.measure(range(n_qubits), range(n_qubits))
    return qc


def build_single_qubit_layer_circuit(n_qubits: int, depth: int, **_ignored) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits, n_qubits)

    for layer in range(depth):
        for q in range(n_qubits):
            # Alternating RX/RY avoids compiling the whole thing into a
            # trivial identity too easily.
            if layer % 2 == 0:
                qc.rx(0.5, q)
            else:
                qc.ry(0.5, q)

    qc.measure(range(n_qubits), range(n_qubits))
    return qc
