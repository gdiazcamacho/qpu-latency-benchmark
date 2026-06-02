from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class TimingJobRecord:
    backend: str
    experiment_name: str
    timestamp: str

    n_circuits: int
    circuit_family: str
    logical_depth: int
    n_qubits: int
    shots: int
    repetition: int

    transpiled_depth_mean: Optional[float]
    transpiled_depth_max: Optional[int]

    walltime_total: Optional[float]
    walltime_backend_run: Optional[float]
    walltime_result_wait: Optional[float]

    slurm_job_id: Optional[str]
    success: int
    error_message: Optional[str]
    metadata_json: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
