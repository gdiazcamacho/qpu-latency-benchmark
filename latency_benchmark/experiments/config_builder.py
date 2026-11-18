"""Builds a fully-resolved probe config from three orthogonal inputs:

  1. a backend file (configs/backends/<backend>.yaml) -- connection/
     credentials/calibration, stable properties of the hardware
  2. a (family, axis) default sweep (axis_defaults.py) -- "what's normal"
  3. CLI overrides -- "what's different this time"

This replaces the old one-YAML-per-probe layout: 3 backend files instead
of dozens of near-duplicate probe YAMLs.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from latency_benchmark.experiments.axis_defaults import get_axis_default

BACKENDS_DIR = Path(__file__).resolve().parents[2] / "configs" / "backends"


def load_backend_config(backend: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
    """Load a backend config.

    Lookup order: an explicit ``path``; then <name>.yaml in the directory
    named by $LATENCY_BENCHMARK_BACKENDS_DIR; then this repo's
    configs/backends/<name>.yaml.
    """
    if path is not None:
        candidates = [Path(path)]
    else:
        if backend is None:
            raise ValueError("Need a backend name or a backend config path")
        candidates = []
        extra = os.environ.get("LATENCY_BENCHMARK_BACKENDS_DIR")
        if extra:
            candidates.append(Path(extra) / f"{backend}.yaml")
        candidates.append(BACKENDS_DIR / f"{backend}.yaml")
    for candidate in candidates:
        if candidate.exists():
            with open(candidate) as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("No backend config at " + " or ".join(str(c) for c in candidates))


def build_probe_config(
    backend: Optional[str],
    family: str,
    axis: str,
    values: Optional[List[Any]] = None,
    repetitions: Optional[int] = None,
    randomize_order: Optional[bool] = None,
    overrides: Optional[Dict[str, Any]] = None,
    experiment_name: Optional[str] = None,
    wire_format: Optional[str] = None,
    backend_config: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a full config dict, ready for expand_probe()/TimingOrchestrator.

    `overrides` sets fixed controls not being swept (e.g. {"shots": 5000}
    for a width probe), taking precedence over the axis default.

    `wire_format` overrides backend_options.wire_format, selecting the
    submission format for backends whose adapter supports it. It is not a
    sweep axis: it's categorical, so comparing formats means running the
    same family/axis once per format and comparing the resulting
    experiments (see plot_backend_comparison.py's --experiments). The
    format is appended to experiment_name so those runs don't collide in
    the database.

    `backend_config` is a path to a backend YAML outside this repo (e.g. a
    collaborator's own QPU); when given, `backend` may be None and is taken
    from that file.
    """
    backend_cfg = load_backend_config(backend, path=backend_config)
    backend = backend_cfg["backend"]
    axis_default = get_axis_default(family, axis)
    overrides = overrides or {}

    sweep_key = axis_default["sweep"]
    sweep_values = values if values is not None else axis_default["values"]

    controls = {
        k: v for k, v in axis_default.items() if k not in ("sweep", "values")
    }
    controls.update(overrides)
    controls["circuit_family"] = family

    backend_options = dict(backend_cfg.get("backend_options", {}))
    if wire_format is not None:
        backend_options["wire_format"] = wire_format

    name = experiment_name or f"{family}_{axis}_{backend}"
    if experiment_name is None and wire_format is not None:
        name = f"{name}_{wire_format}"

    config = {
        "experiment_name": name,
        "experiment_type": f"{family}_{axis}",
        "backend": backend_cfg["backend"],
        "output_db": backend_cfg["output_db"],
        "backend_options": backend_options,
        "sweep": {sweep_key: sweep_values},
        "controls": controls,
        "repetitions": repetitions if repetitions is not None else 3,
        "randomize_order": randomize_order if randomize_order is not None else True,
    }
    if backend_cfg.get("adapter"):
        config["adapter"] = backend_cfg["adapter"]
    return config