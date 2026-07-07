from typing import List
import numpy as np
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


def qft_inverse_probe(n, theta=0.31874, include_swaps=True):
    """
    Inverse QFT probe circuit: Fourier-encoded state (H + Rz phase ramp)
    followed by inverse QFT, in big-endian convention.

    Parameters
    ----------
    n : int
        Number of qubits (width parameter for this probe).
    theta : float
        Fixed phase for state prep. Should NOT be a multiple of 1/2^n,
        to avoid trivial (identity-collapsing) Rz angles after transpilation.
        Default 0.31874 is a fixed, non-dyadic constant -- do not sweep this;
        it doesn't affect gate count/depth, only rotation angles.
    include_swaps : bool
        Whether to include the final SWAP network. Run both True/False
        variants per n to isolate permutation-network cost from the
        core algorithmic (H + controlled-phase) cost.

    Returns
    -------
    QuantumCircuit
    """
    circuit = QuantumCircuit(n, n)

    # --- state preparation: Fourier-encoded state with fixed phase ---
    for i, q in enumerate(circuit.qubits):
        circuit.h(q)
        circuit.rz(theta * 2 * np.pi * 2**i, q)
    circuit.barrier()

    # --- inverse QFT, big-endian, MSB-first ---
    for j in range(n - 1, -1, -1):
        circuit.h(j)
        for k in range(j - 1, -1, -1):
            circuit.cp(-np.pi / 2 ** (j - k), j, k)
        circuit.barrier()

    if include_swaps:
        for j in range(n // 2):
            circuit.swap(j, n - j - 1)

    circuit.measure(range(n), range(n))
    return circuit

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
    elif circuit_family == "qft_inverse":
        # theta is a fixed, non-dyadic constant (not a multiple of 1/2^n_qubits)
        # so no Rz angle collapses to a trivial identity after transpilation.
        # It is intentionally not config-driven: it doesn't affect gate count
        # or depth, only rotation angles, so sweeping it would add noise
        # without adding signal.
        base = qft_inverse_probe(n_qubits, theta=0.31874, include_swaps=True)
    elif circuit_family == "qft_inverse_no_swaps":
        base = qft_inverse_probe(n_qubits, theta=0.31874, include_swaps=False)
    else:
        raise ValueError(f"Unknown circuit family: {circuit_family}")

    circuits = []
    for i in range(n_circuits):
        circ = base.copy()
        circ.name = f"{circuit_family}_nq{n_qubits}_d{depth}_i{i}"
        circuits.append(circ)

    return circuits