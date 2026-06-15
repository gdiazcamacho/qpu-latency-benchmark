import os

from .base import BackendAdapter

class QExaBackendAdapter(BackendAdapter):
    name = "qexa"

    def __init__(self, **kwargs):
        self.options = kwargs

    def get_backend(self):
        from mqss.qiskit_adapter import MQSSQiskitAdapter

        token = self.options.get("token") or os.environ.get("QEXA_TOKEN")
        url = self.options.get("url") or os.environ.get("QEXA_URL")
        port = self.options.get("port") or os.environ.get("QEXA_PORT")
        backend_name = self.options.get("backend_name", "QExa20")

        if token is None:
            raise RuntimeError("QExa token missing. Set QEXA_TOKEN or backend_options.token.")

        adapter_kwargs = {
            "token": token,
            "hpcqc": self.options.get("hpcqc", True),
        }

        if url:
            adapter_kwargs["url"] = url
        if port:
            adapter_kwargs["port"] = int(port)

        adapter = MQSSQiskitAdapter(**adapter_kwargs)
        backends = adapter.backends(name=backend_name)

        if not backends:
            raise RuntimeError(f"No QExa backend found with name={backend_name!r}")

        return backends[0]

    def metadata(self):
        safe_options = dict(self.options)
        safe_options.pop("token", None)
        return {"backend_options": safe_options}