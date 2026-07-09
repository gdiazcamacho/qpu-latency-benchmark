import os

from .base import BackendAdapter


class QExa20BackendAdapter(BackendAdapter):
    """Adapter for QExa-family systems accessed via the MQSS Qiskit adapter.

    Despite the class/module name (kept for the current target system,
    QExa20 at LRZ), this adapter is generic over any MQSS-exposed backend:
    the concrete system is selected via `backend_name` (or `system_name`),
    e.g. "QExa20", "QExa35", etc.

    Submission notes
    -----------------
    QExa20/MQP does not accept batched circuit submission cleanly: circuits
    must be transpiled and submitted one at a time (see
    `supports_batch_submission`). This adapter therefore only constructs the
    backend and exposes transpile/run helpers; the orchestrator drives the
    per-circuit submission loop.
    """

    name = "qexa20"

    def __init__(self, **kwargs):
        self.options = kwargs
        self._backend = None

    def get_backend(self):
        if self._backend is None:
            from mqss.qiskit_adapter import MQSSQiskitAdapter

            token = (
                self.options.get("token")
                or os.environ.get("MQSS_TOKEN")
                or os.environ.get("QEXA20_TOKEN")
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

            # MQSSQiskitAdapter(token, *, hpcqc=None, base_url=None).
            # hpcqc is intentionally not passed: it routes resource-info
            # lookups through a RabbitMQ broker that is not reachable from
            # this environment. Omitting it uses the REST-only path, which
            # is sufficient for circuit submission.
            adapter_kwargs = {"token": token}

            base_url = self.options.get("base_url")
            if base_url is None:
                url = self.options.get("url") or os.environ.get("MQSS_URL")
                port = self.options.get("port") or os.environ.get("MQSS_PORT")
                if url:
                    base_url = f"{url}:{port}" if port else url
            if base_url:
                adapter_kwargs["base_url"] = base_url

            mqss_adapter = MQSSQiskitAdapter(**adapter_kwargs)
            self._backend = mqss_adapter.get_backend(backend_name)

        return self._backend

    def metadata(self):
        safe_options = dict(self.options)
        safe_options.pop("token", None)
        return {"backend_options": safe_options}

    def supports_batch_submission(self) -> bool:
        return False

    def transpile_circuit(self, circuit, backend, optimization_level: int = 0,
                           initial_layout=None, decompose_to_basis: bool = False,
                           seed_transpiler=None):
        """Transpile a single circuit for submission to QExa20.

        Decomposes to the backend's native basis via Qiskit's transpiler.
        optimization_level defaults to 0 (matches prior working configuration
        for this platform); a per-circuit initial_layout may be taken from
        circuit.metadata["initial_layout"] if present, falling back to the
        adapter-level default.

        seed_transpiler pins the routing pass's random seed. Without this,
        routing algorithms (used at any optimization_level for sparse
        coupling maps) are stochastic and can produce meaningfully
        different depths for the identical circuit across separate
        process invocations -- confirmed on this project when a repeat
        transpile of the same n=8 QFT circuit gave depth 742 in one run
        and 541 in another. Always pass an explicit seed for reproducible,
        comparable depth measurements.

        If decompose_to_basis is True, an additional transpile pass to
        basis_gates=["u", "cx"] is applied. This works around a known issue
        where Qiskit serializes parametrized custom gates (e.g. "r_<addr>")
        with unique names baked into the gate definition; MQP's server-side
        transpiler can fail on these with "Bit is not in the circuit". This
        is opt-in (backend_options.decompose_to_basis: true) since it has not
        been confirmed necessary against all MQSS client versions.
        """
        from qiskit import transpile

        circuit_layout = None
        if circuit.metadata:
            circuit_layout = circuit.metadata.get("initial_layout")
        layout = circuit_layout if circuit_layout is not None else initial_layout

        tqc = transpile(
            circuit,
            backend=backend,
            initial_layout=layout,
            optimization_level=optimization_level,
            seed_transpiler=seed_transpiler,
        )

        if decompose_to_basis:
            tqc = transpile(
                tqc,
                basis_gates=["u", "cx"],
                optimization_level=0,
                seed_transpiler=seed_transpiler,
            )

        return tqc
