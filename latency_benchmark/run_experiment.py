import argparse
from pathlib import Path
import yaml

from latency_benchmark.core.orchestrator import TimingOrchestrator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    # Make paths relative to the current working directory.
    Path(config["output_db"]).parent.mkdir(parents=True, exist_ok=True)

    orchestrator = TimingOrchestrator(config)
    orchestrator.run()


if __name__ == "__main__":
    main()
