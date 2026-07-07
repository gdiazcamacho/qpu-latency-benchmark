"""Entangling circuit family: Fourier-state prep + inverse QFT.

Unlike the single-qubit family, depth here is NOT an independent parameter
-- it is structurally determined by n_qubits (O(n^2) controlled-phase
gates). FamilySpec.depth_is_independent=False for this family enforces
that at the config-validation layer: sweeping `logical_depth` for
family="qft" is rejected rather than silently ignored.
"""
import numpy as np
from qiskit import QuantumCircuit

# Fixed, non-dyadic phase for Fourier state prep: NOT a multiple of 1/2^n
# for any n_qubits value we use, so no Rz angle collapses to a trivial
# identity after transpilation regardless of circuit size. Intentionally
# not config-driven -- it doesn't affect gate count/depth, only rotation
# angles, so sweeping it would add noise without adding signal.
DEFAULT_THETA = 0.31874


def _fourier_state(circ: QuantumCircuit, theta: float) -> None:
    for i, q in enumerate(circ.qubits):
        circ.h(q)
        circ.rz(theta * 2 * np.pi * 2**i, q)


def _qft_inverse(n: int, include_swaps: bool) -> QuantumCircuit:
    """Inverse QFT, big-endian convention (MSB-first)."""
    circuit = QuantumCircuit(n)
    for j in range(n - 1, -1, -1):
        circuit.h(j)
        for k in range(j - 1, -1, -1):
            circuit.cp(-np.pi / 2 ** (j - k), j, k)
        circuit.barrier()
    if include_swaps:
        for j in range(n // 2):
            circuit.swap(j, n - j - 1)
    return circuit


def build_qft_circuit(n_qubits: int, theta: float = DEFAULT_THETA,
                       include_swaps: bool = True, **_ignored) -> QuantumCircuit:
    """Fourier-encoded state (H + Rz phase ramp) followed by inverse QFT.

    Correctness verified against AerSimulator: the peak measurement outcome
    matches round(theta * 2**n_qubits) % 2**n_qubits under the standard
    Qiskit bitstring convention (qubit n-1 = MSB) when include_swaps=True,
    and under the reversed convention when include_swaps=False -- i.e. the
    swap network does exactly what it's supposed to.
    """
    circuit = QuantumCircuit(n_qubits, n_qubits)
    _fourier_state(circuit, theta)
    circuit.barrier()
    circuit.compose(_qft_inverse(n_qubits, include_swaps), inplace=True)
    circuit.measure(range(n_qubits), range(n_qubits))
    return circuit


def build_qft_no_swap_circuit(n_qubits: int, theta: float = DEFAULT_THETA, **_ignored) -> QuantumCircuit:
    return build_qft_circuit(n_qubits, theta=theta, include_swaps=False)
