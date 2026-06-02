import random
from typing import Dict, Iterable, List


def expand_matrix(matrix_cfg: Dict) -> List[Dict]:
    points = []

    for n_circuits in matrix_cfg["n_circuits"]:
        for depth in matrix_cfg["depths"]:
            for shots in matrix_cfg["shots"]:
                for n_qubits in matrix_cfg["n_qubits"]:
                    for repetition in range(int(matrix_cfg.get("repetitions", 1))):
                        points.append({
                            "n_circuits": int(n_circuits),
                            "logical_depth": int(depth),
                            "shots": int(shots),
                            "n_qubits": int(n_qubits),
                            "repetition": int(repetition),
                            "circuit_family": matrix_cfg.get("circuit_family", "single_qubit_layers"),
                        })

    if matrix_cfg.get("randomize_order", False):
        random.shuffle(points)

    return points
