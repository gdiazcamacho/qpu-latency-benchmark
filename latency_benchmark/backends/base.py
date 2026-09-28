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

    def supports_ir_formats(self) -> bool:
        """Whether this backend's run() path accepts a specific,
        caller-chosen wire format at submission time, such that the choice
        affects real submitted walltime -- not just local serialization
        cost.

        Adapters returning True must also implement wire_formats() and
        honour backend_options.wire_format in run_options().

        Note this is distinct from experiments/ir_formats.py, which
        measures LOCAL serialization cost only and works regardless of
        this flag, since it never touches actual submission.
        """
        return False

    def wire_formats(self):
        """Wire formats this adapter can submit in, if supports_ir_formats().

        Returns an empty tuple by default. The first entry should be the
        backend's own default (i.e. what you get without setting
        wire_format at all).
        """
        return ()

    def run_options(self) -> Dict[str, Any]:
        """Extra keyword arguments to pass to backend.run().

        Lets an adapter inject backend-specific submission flags (e.g.
        QMIO's output_qasm3) without the orchestrator needing to know
        anything about a particular platform's client API.
        """
        return {}