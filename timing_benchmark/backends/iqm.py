from .base import BackendAdapter


class IQMBackendAdapter(BackendAdapter):
    name = "iqm"

    def __init__(self, **kwargs):
        self.options = kwargs

    def get_backend(self):
        raise NotImplementedError(
            "IQM backend construction is project-specific. "
            "Fill this adapter with your IQM Resonance backend/provider setup."
        )

    def metadata(self):
        return {"backend_options": self.options}
