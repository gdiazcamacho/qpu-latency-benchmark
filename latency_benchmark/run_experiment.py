"""
Unified CLI entrypoint for latency probes.

Usage:
    python -m latency_benchmark.run_experiment \\
        --backend qmio --family qft --axis width

    python -m latency_benchmark.run_experiment \\
        --backend qexa20 --family single_qubit --axis batch \\
        --values 1,2,4,8 --repetitions 5

    # Legacy: run an explicit YAML config directly (old-style probes still work)
    python -m latency_benchmark.run_experiment --config configs/probes/foo.yaml
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml

from latency_benchmark.core.orchestrator import TimingOrchestrator
from latency_benchmark.experiments.config_builder import build_probe_config


def _parse_values(raw: str):
    """Parse a comma-separated CLI values string into ints (falling back
    to floats, then raw strings, per item)."""
    out = []
    for item in raw.split(","):
        item = item.strip()
        try:
            out.append(int(item))
        except ValueError:
            try:
                out.append(float(item))
            except ValueError:
                out.append(item)
    return out


def main():
    parser = argparse.ArgumentParser()

    # New-style: family/axis/backend
    parser.add_argument("--backend", choices=["qmio", "qexa20", "fake"])
    parser.add_argument("--family", choices=["single_qubit", "qft", "qft_no_swap", "measure_only"])
    parser.add_argument("--axis", choices=["batch", "shot", "width", "depth"])
    parser.add_argument("--values", default=None, help="Comma-separated override for the sweep values, e.g. 2,4,6,8")
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--shots", type=int, default=None, help="Override fixed shots control")
    parser.add_argument("--n-qubits", type=int, default=None, dest="n_qubits", help="Override fixed n_qubits control")
    parser.add_argument("--randomize-order", dest="randomize_order", action="store_true", default=None)
    parser.add_argument("--no-randomize-order", dest="randomize_order", action="store_false")
    parser.add_argument("--ir-formats", default=None, help="LOCAL diagnostic: comma-separated formats whose serialization cost to time (qasm2,qasm3,qir). Does not change what is submitted. Opt-in, off by default.")
    parser.add_argument("--wire-format", default=None, dest="wire_format",
                         help="Format actually SUBMITTED to the backend (e.g. qasm2, qasm3 on qmio). Changes real submission time. Only for backends whose adapter supports it; appended to experiment_name so per-format runs don't collide.")
    parser.add_argument("--experiment-name", default=None, dest="experiment_name")

    # Legacy: explicit YAML config path
    parser.add_argument("--config", default=None, help="Path to an explicit YAML config (bypasses --backend/--family/--axis).")

    parser.add_argument("--output-db", default=None, dest="output_db")
    parser.add_argument("--date-stamp", action="store_true", dest="date_stamp")
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config = yaml.safe_load(f)
    else:
        missing = [n for n, v in [("--backend", args.backend), ("--family", args.family), ("--axis", args.axis)] if v is None]
        if missing:
            parser.error(f"Missing required arguments: {', '.join(missing)} (or use --config for a legacy YAML run)")

        overrides = {}
        if args.shots is not None:
            overrides["shots"] = args.shots
        if args.n_qubits is not None:
            overrides["n_qubits"] = args.n_qubits

        config = build_probe_config(
            backend=args.backend,
            family=args.family,
            axis=args.axis,
            values=_parse_values(args.values) if args.values else None,
            repetitions=args.repetitions,
            randomize_order=args.randomize_order,
            overrides=overrides,
            experiment_name=args.experiment_name,
            wire_format=args.wire_format,
        )
        if args.ir_formats:
            config["ir_formats"] = [f.strip() for f in args.ir_formats.split(",")]

    today = datetime.now().strftime("%Y-%m-%d")
    if args.output_db:
        config["output_db"] = args.output_db.replace("{date}", today)
    elif args.date_stamp:
        p = Path(config["output_db"])
        config["output_db"] = str(p.parent / f"{p.stem}_{today}{p.suffix}")

    db_path = Path(config["output_db"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Output DB: {db_path}")

    # Reproducibility: dump the fully-resolved config for this run.
    raw_dir = Path("output/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = raw_dir / f"resolved_config_{datetime.now().strftime('%Y-%m-%dT%H%M%S')}.yaml"
    with open(resolved_path, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)
    print(f"Resolved config: {resolved_path}")

    orchestrator = TimingOrchestrator(config)
    orchestrator.run()


if __name__ == "__main__":
    main()