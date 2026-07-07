"""Builds a fully-resolved probe config from three orthogonal inputs:

  1. a backend file (configs/backends/<backend>.yaml) -- connection/
     credentials/calibration, stable properties of the hardware
  2. a (family, axis) default sweep (axis_defaults.py) -- "what's normal"
  3. CLI overrides -- "what's different this time"

This replaces the old one-YAML-per-probe layout: 3 backend files instead
of dozens of near-duplicate probe YAMLs.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from latency_benchmark.experiments.axis_defaults import get_axis_default

BACKENDS_DIR = Path(__file__).resolve().parents[2] / "configs" / "backends"


def load_backend_config(backend: str) -> Dict[str, Any]:
    path = BACKENDS_DIR / f"{backend}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No backend config at {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def build_probe_config(
    backend: str,
    family: str,
    axis: str,
    values: Optional[List[Any]] = None,
    repetitions: Optional[int] = None,
    randomize_order: Optional[bool] = None,
    overrides: Optional[Dict[str, Any]] = None,
    experiment_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a full config dict, ready for expand_probe()/TimingOrchestrator.

    `overrides` sets fixed controls not being swept (e.g. {"shots": 5000}
    for a width probe), taking precedence over the axis default.
    """
    backend_cfg = load_backend_config(backend)
    axis_default = get_axis_default(family, axis)
    overrides = overrides or {}

    sweep_key = axis_default["sweep"]
    sweep_values = values if values is not None else axis_default["values"]

    controls = {
        k: v for k, v in axis_default.items() if k not in ("sweep", "values")
    }
    controls.update(overrides)
    controls["circuit_family"] = family

    name = experiment_name or f"{family}_{axis}_{backend}"

    config = {
        "experiment_name": name,
        "experiment_type": f"{family}_{axis}",
        "backend": backend_cfg["backend"],
        "output_db": backend_cfg["output_db"],
        "backend_options": backend_cfg.get("backend_options", {}),
        "sweep": {sweep_key: sweep_values},
        "controls": controls,
        "repetitions": repetitions if repetitions is not None else 3,
        "randomize_order": randomize_order if randomize_order is not None else True,
    }
    return config
