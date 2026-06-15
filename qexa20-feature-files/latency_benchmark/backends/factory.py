from .fake import FakeBackendAdapter
from .qmio import QmioBackendAdapter
from .qexa20 import QExa20BackendAdapter


def make_backend_adapter(name: str, options: dict):
    if name == "fake":
        return FakeBackendAdapter(**options)
    if name == "qmio":
        return QmioBackendAdapter(**options)
    if name == "qexa20":
        return QExa20BackendAdapter(**options)
    raise ValueError(f"Unknown backend: {name}")
