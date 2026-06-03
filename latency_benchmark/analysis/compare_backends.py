"""
Cross-backend timing comparison.

Produces a side-by-side comparison of timing models across all backends in
the database, and a unified comparison figure showing:
  - Fitted alpha (per-circuit overhead) per backend
  - T0 (fixed job overhead) per backend
  - Walltime vs N curves overlaid
"""

import argparse
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from latency_benchmark.analysis.load_results import load_timing_jobs
from latency_benchmark.analysis.fit_models import auto_fit, fit_linear_N


BACKEND_COLORS = {
    "iqm": "#2196F3",
    "qmio": "#FF5722",
    "fake": "#9E9E9E",
}


def compare_all_backends(df: pd.DataFrame) -> pd.DataFrame:
    """Fit auto model for each backend and return a summary DataFrame."""
    rows = []
    for backend, grp in df[df["success"] == 1].groupby("backend"):
        if len(grp) < 3:
            continue
        try:
            fit = auto_fit(grp)
            rows.append({
                "backend": backend,
                "model": fit.get("model", "?"),
                "T0_s": fit.get("T0_fixed_job_overhead_s"),
                "alpha_ms_per_circuit": fit.get("alpha_per_circuit_s", 0) * 1000,
                "beta_ms_per_circuit_depth": fit.get("beta_per_circuit_depth_s", 0) * 1000,
                "r2": fit.get("r2"),
                "n_rows": fit.get("n_rows"),
                "note": fit.get("_selection_reason", ""),
            })
        except Exception as exc:
            rows.append({"backend": backend, "error": str(exc)})
    return pd.DataFrame(rows)


def plot_comparison(df: pd.DataFrame, outdir: Path):
    good = df[(df["success"] == 1) & df["walltime_total"].notna()].copy()
    backends = sorted(good["backend"].unique())

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Cross-backend Timing Comparison", fontsize=13, fontweight="bold")

    # Panel 1: Walltime vs N per backend (depth-averaged)
    ax = axes[0]
    for b in backends:
        bdf = good[good["backend"] == b]
        agg = bdf.groupby("n_circuits")["walltime_total"].mean()
        color = BACKEND_COLORS.get(b, "black")
        ax.plot(agg.index, agg.values, marker="o", label=b, color=color, linewidth=1.8)

        # Overlay fit
        fit = auto_fit(bdf)
        N_range = np.linspace(agg.index.min(), agg.index.max(), 200)
        T0 = fit.get("T0_fixed_job_overhead_s", 0)
        alpha = fit.get("alpha_per_circuit_s", 0)
        ax.plot(N_range, T0 + alpha * N_range, "--", color=color, linewidth=1.2, alpha=0.7)

    ax.set_xlabel("N circuits in batch")
    ax.set_ylabel("Total walltime [s]")
    ax.set_title("Walltime vs N (depth-averaged)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 2: Per-circuit overhead bar chart
    ax = axes[1]
    summary = compare_all_backends(good)
    summary_valid = summary.dropna(subset=["alpha_ms_per_circuit"])
    colors = [BACKEND_COLORS.get(b, "grey") for b in summary_valid["backend"]]
    bars = ax.bar(summary_valid["backend"], summary_valid["alpha_ms_per_circuit"], color=colors)
    ax.set_ylabel("α — per-circuit overhead [ms/circuit]")
    ax.set_title("Per-circuit overhead (α)")
    ax.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, summary_valid["alpha_ms_per_circuit"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{val:.1f} ms", ha="center", va="bottom", fontsize=9)

    # Panel 3: Fixed job overhead bar chart
    ax = axes[2]
    summary_valid2 = summary.dropna(subset=["T0_s"])
    colors2 = [BACKEND_COLORS.get(b, "grey") for b in summary_valid2["backend"]]
    bars2 = ax.bar(summary_valid2["backend"], summary_valid2["T0_s"] * 1000, color=colors2)
    ax.set_ylabel("T₀ — fixed job overhead [ms]")
    ax.set_title("Fixed overhead (T₀)")
    ax.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars2, summary_valid2["T0_s"] * 1000):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{val:.1f} ms", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    outfile = outdir / "backend_comparison.png"
    fig.savefig(outfile, dpi=180)
    plt.close(fig)
    print(f"Saved {outfile}")


def main():
    parser = argparse.ArgumentParser(description="Compare timing overhead across backends.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--outdir", default="output/figures")
    args = parser.parse_args()

    df = load_timing_jobs(args.db)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("=== PER-BACKEND MODEL SUMMARY ===\n")
    summary = compare_all_backends(df[df["success"] == 1])
    print(summary.to_string(index=False))

    plot_comparison(df, outdir)


if __name__ == "__main__":
    main()
