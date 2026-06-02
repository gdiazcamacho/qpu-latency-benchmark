from .base import BackendAdapter


class QmioBackendAdapter(BackendAdapter):
    name = "qmio"

    def __init__(self, **kwargs):
        self.options = kwargs

    def get_backend(self):
        from qmiotools.integrations.qiskitqmio import QmioBackend

        # First robust version: no constructor kwargs.
        return QmioBackend()

    def metadata(self):
        return {"backend_options": self.options}