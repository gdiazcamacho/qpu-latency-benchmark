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
