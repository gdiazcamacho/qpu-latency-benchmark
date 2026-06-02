import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from timing_benchmark.analysis.load_results import load_timing_jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--outdir", default="output/figures")
    parser.add_argument("--backend", default=None)
    args = parser.parse_args()

    df = load_timing_jobs(args.db)
    df = df[(df["success"] == 1) & df["walltime_total"].notna()].copy()

    if args.backend:
        df = df[df["backend"] == args.backend]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for depth, group in df.groupby("logical_depth"):
        grouped = group.groupby("n_circuits")["walltime_total"].mean().reset_index()
        plt.plot(grouped["n_circuits"], grouped["walltime_total"], marker="o", label=f"depth={depth}")

    plt.xlabel("Number of circuits in job")
    plt.ylabel("Total walltime [s]")
    plt.title("Timing overhead matrix")
    plt.legend()
    plt.tight_layout()

    outfile = outdir / "walltime_vs_ncircuits.png"
    plt.savefig(outfile, dpi=200)
    print(f"Saved {outfile}")


if __name__ == "__main__":
    main()
