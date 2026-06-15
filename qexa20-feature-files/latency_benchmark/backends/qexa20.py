import os

from .base import BackendAdapter


class QExa20BackendAdapter(BackendAdapter):
    """Adapter for QExa-family systems accessed via the MQSS Qiskit adapter.

    Despite the class/module name (kept for the current target system,
    QExa20 at LRZ), this adapter is generic over any MQSS-exposed backend:
    the concrete system is selected via `backend_name` (or `system_name`),
    e.g. "QExa20", "QExa35", etc.
    """

    name = "qexa20"

    def __init__(self, **kwargs):
        self.options = kwargs

    def get_backend(self):
        from mqss.qiskit_adapter import MQSSQiskitAdapter

        token = (
            self.options.get("token")
            or os.environ.get("MQSS_TOKEN")
            or os.environ.get("QEXA20_TOKEN")
        )
        url = (
            self.options.get("url")
            or os.environ.get("MQSS_URL")
            or os.environ.get("QEXA20_URL")
        )
        port = (
            self.options.get("port")
            or os.environ.get("MQSS_PORT")
            or os.environ.get("QEXA20_PORT")
        )
        backend_name = (
            self.options.get("backend_name")
            or self.options.get("system_name")
            or os.environ.get("MQSS_BACKEND")
            or "QExa20"
        )

        if not token:
            raise RuntimeError(
                "QExa20 token missing. Set MQSS_TOKEN (or QEXA20_TOKEN) "
                "or backend_options.token."
            )

        adapter_kwargs = {"token": token}
        if url:
            adapter_kwargs["url"] = url
        if port:
            adapter_kwargs["port"] = int(port)

        adapter = MQSSQiskitAdapter(**adapter_kwargs)
        return adapter.get_backend(backend_name)

    def metadata(self):
        safe_options = dict(self.options)
        safe_options.pop("token", None)
        return {"backend_options": safe_options}
