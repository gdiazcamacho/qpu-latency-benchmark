"""Backend adapter lookup.

Built-in adapters are imported lazily, so a missing optional client library
(e.g. qiskit-aer, mqss-qiskit) only matters for the backend that needs it.

External adapters: a backend config may name any importable class with
``adapter: "package.module:ClassName"``. The class is instantiated with
``backend_options`` as keyword arguments, exactly like the built-ins. This
lets other groups add a QPU without editing this package.
"""
import importlib


def _builtin(name: str):
    if name == "fake":
        from .fake import FakeBackendAdapter
        return FakeBackendAdapter
    if name == "qmio":
        from .qmio import QmioBackendAdapter
        return QmioBackendAdapter
    if name == "qexa20":
        from .qexa20 import QExa20BackendAdapter
        return QExa20BackendAdapter
    return None


def _import_adapter(path: str):
    module_name, sep, class_name = path.partition(":")
    if not sep or not module_name or not class_name:
        raise ValueError(f"adapter must look like 'package.module:ClassName', got {path!r}")
    return getattr(importlib.import_module(module_name), class_name)


def make_backend_adapter(name: str, options: dict, adapter: str = None):
    cls = _import_adapter(adapter) if adapter else _builtin(name)
    if cls is None:
        raise ValueError(
            f"Unknown backend: {name!r}. Use one of fake/qmio/qexa20, or set "
            f"'adapter: package.module:ClassName' in the backend config."
        )
    return cls(**(options or {}))
