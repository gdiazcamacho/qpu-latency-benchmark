from .fake import FakeBackendAdapter
from .qmio import QmioBackendAdapter
from .iqm import IQMBackendAdapter


def make_backend_adapter(name: str, options: dict):
    if name == "fake":
        return FakeBackendAdapter(**options)
    if name == "qmio":
        return QmioBackendAdapter(**options)
    if name == "iqm":
        return IQMBackendAdapter(**options)
    raise ValueError(f"Unknown backend: {name}")
