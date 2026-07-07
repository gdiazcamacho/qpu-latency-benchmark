from abc import ABC, abstractmethod
from typing import Any, Dict


class BackendAdapter(ABC):
    name: str

    @abstractmethod
    def get_backend(self):
        raise NotImplementedError

    def metadata(self) -> Dict[str, Any]:
        return {}

    def supports_batch_submission(self) -> bool:
        """Whether backend.run() accepts a list of circuits in one call.

        Most Qiskit-like backends do. Some platforms (e.g. QExa20 via MQSS)
        require circuits to be submitted one at a time due to server-side
        QASM serialization limitations. Adapters for such platforms should
        override this to return False.
        """
        return True

    def supports_ir_formats(self) -> bool:
        """Whether this backend's run() path can be made to accept a
        specific, caller-chosen intermediate representation (QASM2/QASM3/
        QIR) at submission time, such that the choice could affect real
        wire/execution walltime -- not just local serialization cost.

        Defaults to False everywhere. This is a placeholder seam: no
        adapter currently implements format-controlled submission. Before
        flipping this to True for a given backend, confirm the underlying
        client library (e.g. mqss.qiskit_adapter, qmio-tools) actually
        accepts a chosen format rather than always reconverting internally
        regardless of what's passed in. Local serialization-cost
        measurement (see experiments/ir_formats.py) works regardless of
        this flag, since it never touches actual submission.
        """
        return False
