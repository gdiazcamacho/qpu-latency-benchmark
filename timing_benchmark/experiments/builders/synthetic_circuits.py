from typing import List
from qiskit import QuantumCircuit


def build_single_qubit_layer_circuit(n_qubits: int, depth: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits, n_qubits)

    for layer in range(depth):
        for q in range(n_qubits):
            # Alternating RX/RY avoids compiling the whole thing into a trivial identity too easily.
            if layer % 2 == 0:
                qc.rx(0.5, q)
            else:
                qc.ry(0.5, q)

    qc.measure(range(n_qubits), range(n_qubits))
    return qc


def build_measure_only_circuit(n_qubits: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.measure(range(n_qubits), range(n_qubits))
    return qc


def build_circuit_batch(
    n_circuits: int,
    n_qubits: int,
    depth: int,
    circuit_family: str,
) -> List[QuantumCircuit]:
    if circuit_family == "measure_only":
        base = build_measure_only_circuit(n_qubits)
    elif circuit_family == "single_qubit_layers":
        base = build_single_qubit_layer_circuit(n_qubits, depth)
    else:
        raise ValueError(f"Unknown circuit family: {circuit_family}")

    circuits = []
    for i in range(n_circuits):
        circ = base.copy()
        circ.name = f"{circuit_family}_nq{n_qubits}_d{depth}_i{i}"
        circuits.append(circ)

    return circuits
