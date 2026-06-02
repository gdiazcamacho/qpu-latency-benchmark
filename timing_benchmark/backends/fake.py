from qiskit_aer import AerSimulator
from .base import BackendAdapter


class FakeBackendAdapter(BackendAdapter):
    name = "fake"

    def __init__(self, **kwargs):
        self.options = kwargs

    def get_backend(self):
        return AerSimulator()
