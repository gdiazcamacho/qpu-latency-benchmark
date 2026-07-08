"""
Verifies whether transpile() is actually doing coupling-map-aware routing
for a given backend, by checking that every two-qubit gate in the
transpiled circuit acts on a pair of PHYSICAL qubits that is a real edge
in the backend's coupling map.

If any two-qubit gate violates the coupling map, real hardware-aware
routing is NOT happening -- the reported "transpiled depth" does not
reflect real connectivity constraints and should not be trusted as a
connectivity comparison.

Run on the cluster (needs the real backend object):
    python check_routing.py qmio
    python check_routing.py qexa20
"""
import sys
sys.path.insert(0, ".")

from qiskit import transpile
from latency_benchmark.experiments.families import build_circuit_batch
from latency_benchmark.backends.factory import make_backend_adapter
import yaml


def check(backend_name):
    with open(f"configs/backends/{backend_name}.yaml") as f:
        cfg = yaml.safe_load(f)

    adapter = make_backend_adapter(backend_name, cfg.get("backend_options", {}))
    backend = adapter.get_backend()

    # Try to pull the real coupling map for reference
    coupling_map = None
    try:
        coupling_map = set(map(tuple, backend.coupling_map))
    except Exception:
        try:
            coupling_map = set(map(tuple, backend.configuration().coupling_map))
        except Exception:
            print("WARNING: could not extract coupling_map from backend object directly.")

    circuit = build_circuit_batch(1, 8, 0, "qft")[0]
    opt_level = cfg.get("backend_options", {}).get("optimization_level", 0)
    seed = cfg.get("backend_options", {}).get("seed_transpiler", 42)

    # Mirror the orchestrator's ACTUAL transpile path exactly, not a
    # simplified reimplementation. This matters: QExa20's real path goes
    # through backend_adapter.transpile_circuit(), which does a SECOND
    # transpile pass (forcing basis_gates=["u","cx"]) when
    # decompose_to_basis=True is set. Calling plain transpile() once here
    # instead would silently test a different pipeline than production
    # uses, making any depth comparison meaningless -- this was the actual
    # cause of an apparent 576-vs-40 "nondeterminism" that was really just
    # two different pipelines being compared.
    if hasattr(adapter, "transpile_circuit"):
        decompose_to_basis = cfg.get("backend_options", {}).get("decompose_to_basis", False)
        tqc = adapter.transpile_circuit(
            circuit, backend,
            optimization_level=opt_level,
            decompose_to_basis=decompose_to_basis,
            seed_transpiler=seed,
        )
    else:
        tqc = transpile(circuit, backend=backend, optimization_level=opt_level, seed_transpiler=seed)

    print(f"Backend: {backend_name}, optimization_level={opt_level}")
    if coupling_map is not None:
        cm_sorted = tuple(sorted(coupling_map))
        print(f"Coupling map size: {len(cm_sorted)} edges")
        print(f"Coupling map hash: {hash(cm_sorted)}")
        print(f"Coupling map (sorted): {cm_sorted}")
    print(f"Transpiled depth: {tqc.depth()}")
    print(f"Coupling map available: {coupling_map is not None}")

    violations = 0
    two_q_gates = 0
    for instr in tqc.data:
        if instr.operation.num_qubits == 2:
            two_q_gates += 1
            q0 = tqc.find_bit(instr.qubits[0]).index
            q1 = tqc.find_bit(instr.qubits[1]).index
            if coupling_map is not None:
                if (q0, q1) not in coupling_map and (q1, q0) not in coupling_map:
                    violations += 1

    print(f"Two-qubit gates: {two_q_gates}")
    print(f"Coupling-map violations: {violations}")
    if coupling_map is not None:
        if violations == 0:
            print("=> Real routing appears to be happening correctly.")
        else:
            print("=> REAL ROUTING IS NOT HAPPENING -- transpile is ignoring the coupling map!")


if __name__ == "__main__":
    check(sys.argv[1])