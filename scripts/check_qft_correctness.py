"""
One-time sanity check, NOT part of the timing pipeline: does the QFT
family's Fourier-state-prep + inverse-QFT circuit actually decode theta
correctly on a noiseless simulator?

This validates the algorithm, not latency -- run manually once per new
circuit family (or after editing an existing one), not on every probe run.
Real-hardware noise will spread the measured peak; this only establishes
the ideal (noiseless) baseline to compare against.

Usage: python scripts/check_qft_correctness.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qiskit import transpile
from qiskit_aer import AerSimulator

from latency_benchmark.experiments.families.entangling import (
    DEFAULT_THETA, build_qft_circuit, build_qft_no_swap_circuit,
)


def check(build_fn, n, theta, swap_qubits, shots=4000):
    qc = build_fn(n_qubits=n, theta=theta) if build_fn is build_qft_no_swap_circuit \
        else build_fn(n_qubits=n, theta=theta, include_swaps=swap_qubits)

    backend = AerSimulator()
    tqc = transpile(qc, backend=backend)
    result = backend.run(tqc, shots=shots).result()
    counts = result.get_counts()

    expected_bin = round(theta * 2**n) % 2**n
    peak_bitstring = max(counts, key=counts.get)
    peak_prob = counts[peak_bitstring] / shots

    val_as_printed = int(peak_bitstring, 2)      # qubit n-1 = MSB (Qiskit default print order)
    val_reversed = int(peak_bitstring[::-1], 2)  # qubit 0 = MSB

    print(f"\n--- n={n}, theta={theta}, swap_qubits={swap_qubits} ---")
    print(f"Expected bin: {expected_bin}")
    print(f"Peak outcome: {peak_bitstring} (prob={peak_prob:.3f})")
    print(f"  as-printed (qubit n-1 = MSB): {val_as_printed} "
          f"{'MATCH' if val_as_printed == expected_bin else ''}")
    print(f"  reversed   (qubit 0 = MSB):   {val_reversed} "
          f"{'MATCH' if val_reversed == expected_bin else ''}")


if __name__ == "__main__":
    for n in [4, 6, 8]:
        check(build_qft_circuit, n, DEFAULT_THETA, swap_qubits=True)
    check(build_qft_no_swap_circuit, 6, DEFAULT_THETA, swap_qubits=False)
