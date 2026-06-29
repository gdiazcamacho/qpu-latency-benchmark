import argparse
from datetime import datetime
from pathlib import Path
import yaml

from latency_benchmark.core.orchestrator import TimingOrchestrator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument(
        "--output-db",
        default=None,
        dest="output_db",
        help=(
            "Override output_db path from the config. "
            "Use {date} as a placeholder for today's date (YYYY-MM-DD), "
            "e.g. output/db/results_{date}.sqlite"
        ),
    )
    parser.add_argument(
        "--date-stamp",
        action="store_true",
        dest="date_stamp",
        help=(
            "Auto-append today's date to the DB filename, e.g. "
            "timing_results_2026-06-15.sqlite. Ignored if --output-db is given."
        ),
    )
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    today = datetime.now().strftime("%Y-%m-%d")

    if args.output_db:
        # Explicit override — honour {date} placeholder if present.
        config["output_db"] = args.output_db.replace("{date}", today)
    elif args.date_stamp:
        # Auto-stamp: insert date before the .sqlite extension.
        p = Path(config["output_db"])
        config["output_db"] = str(p.parent / f"{p.stem}_{today}{p.suffix}")

    db_path = Path(config["output_db"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Output DB: {db_path}")

    orchestrator = TimingOrchestrator(config)
    orchestrator.run()


if __name__ == "__main__":
    main()
