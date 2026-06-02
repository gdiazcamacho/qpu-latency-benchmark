from abc import ABC, abstractmethod
from typing import Any, Dict


class BackendAdapter(ABC):
    name: str

    @abstractmethod
    def get_backend(self):
        raise NotImplementedError

    def metadata(self) -> Dict[str, Any]:
        return {}
