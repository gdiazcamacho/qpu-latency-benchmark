"""
Visualization module for quantum timing overhead analysis.

Produces a multi-panel figure:
  Panel A – Walltime vs N (per depth), with fitted T=T0+alpha*N line
  Panel B – Per-circuit overhead vs N (depth-colour coded)
  Panel C – Timing component breakdown: walltime_backend_run vs walltime_result_wait
  Panel D – Residual analysis (observed vs predicted)
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

from timing_benchmark.analysis.load_results import load_timing_jobs
from timing_benchmark.analysis.fit_models import fit_linear_N, fit_linear_N_depth, auto_fit


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _depth_cmap(depths):
    unique = sorted(set(depths))
    cmap = cm.get_cmap("viridis", len(unique))
    return {d: cmap(i) for i, d in enumerate(unique)}


# ---------------------------------------------------------------------------
# Individual panel functions
# ---------------------------------------------------------------------------

def _panel_walltime_vs_N(ax, df, fit: dict):
    depth_col = _depth_cmap(df["logical_depth"].unique())
    for depth, grp in df.groupby("logical_depth"):
        agg = grp.groupby("n_circuits")["walltime_total"].mean()
        ax.plot(agg.index, agg.values, marker="o", color=depth_col[depth],
                label=f"depth={depth}", linewidth=1.4, markersize=5)

    # Overlay fitted line
    N_range = np.linspace(df["n_circuits"].min(), df["n_circuits"].max(), 200)
    T0 = fit.get("T0_fixed_job_overhead_s", 0)
    alpha = fit.get("alpha_per_circuit_s", 0)
    ax.plot(N_range, T0 + alpha * N_range, "k--", linewidth=1.8,
            label=f"fit: T₀={T0:.2f}s, α={alpha*1000:.0f}ms/circ")

    ax.set_xlabel("N circuits in batch")
    ax.set_ylabel("Total walltime [s]")
    ax.set_title(f"A  Walltime vs batch size  (R²={fit.get('r2', float('nan')):.4f})")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)


def _panel_per_circuit(ax, df):
    df = df.copy()
    df["tpc"] = df["walltime_total"] / df["n_circuits"]
    depth_col = _depth_cmap(df["logical_depth"].unique())
    for depth, grp in df.groupby("logical_depth"):
        agg = grp.groupby("n_circuits")["tpc"].mean()
        ax.plot(agg.index, agg.values * 1000, marker="s", color=depth_col[depth],
                label=f"depth={depth}", linewidth=1.2, markersize=4)

    ax.set_xlabel("N circuits in batch")
    ax.set_ylabel("Time per circuit [ms]")
    ax.set_title("B  Per-circuit overhead vs batch size")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)


def _panel_component_breakdown(ax, df):
    """Stacked bar of backend_run vs result_wait by n_circuits (depth-averaged)."""
    agg = df.groupby("n_circuits")[["walltime_backend_run", "walltime_result_wait"]].mean()
    N = agg.index.to_numpy()
    run = agg["walltime_backend_run"].fillna(0).to_numpy()
    wait = agg["walltime_result_wait"].fillna(0).to_numpy()

    ax.bar(N, run, label="backend.run() call", color="#4C72B0", width=N * 0.15)
    ax.bar(N, wait, bottom=run, label="job.result() wait", color="#DD8452", width=N * 0.15)
    ax.set_xlabel("N circuits in batch")
    ax.set_ylabel("Walltime [s]")
    ax.set_title("C  Timing component breakdown")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    # Annotate fraction
    for i, n in enumerate(N):
        total = run[i] + wait[i]
        if total > 0:
            frac = run[i] / total
            ax.text(n, total + total * 0.02, f"{frac:.0%}", ha="center", fontsize=7)


def _panel_residuals(ax, df, fit: dict):
    T0 = fit.get("T0_fixed_job_overhead_s", 0)
    alpha = fit.get("alpha_per_circuit_s", 0)
    beta = fit.get("beta_per_circuit_depth_s", 0)

    N = df["n_circuits"].to_numpy(float)
    d = df["logical_depth"].to_numpy(float)
    y = df["walltime_total"].to_numpy(float)
    pred = T0 + alpha * N + beta * N * d
    resid = y - pred

    ax.scatter(pred, resid, alpha=0.6, s=25, c=d, cmap="viridis")
    ax.axhline(0, color="k", linewidth=1)
    ax.set_xlabel("Predicted walltime [s]")
    ax.set_ylabel("Residual [s]")
    ax.set_title("D  Residuals: observed − predicted")
    ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Main figure composer
# ---------------------------------------------------------------------------

def plot_timing_summary(df, outdir: Path, backend_name: str = ""):
    good = df[(df["success"] == 1) & df["walltime_total"].notna()].copy()
    if len(good) < 3:
        print("Not enough data to plot.")
        return

    fit = auto_fit(good)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        f"Quantum Job Timing Overhead Analysis  —  backend: {backend_name or 'all'}",
        fontsize=13, fontweight="bold"
    )

    _panel_walltime_vs_N(axes[0, 0], good, fit)
    _panel_per_circuit(axes[0, 1], good)
    _panel_component_breakdown(axes[1, 0], good)
    _panel_residuals(axes[1, 1], good, fit)

    plt.tight_layout()
    outfile = outdir / f"timing_overview_{backend_name or 'all'}.png"
    fig.savefig(outfile, dpi=180)
    plt.close(fig)
    print(f"Saved {outfile}")

    # Also save individual walltime vs N (backward compat)
    fig2, ax2 = plt.subplots(figsize=(7, 4))
    _panel_walltime_vs_N(ax2, good, fit)
    fig2.tight_layout()
    compat_file = outdir / "walltime_vs_ncircuits.png"
    fig2.savefig(compat_file, dpi=180)
    plt.close(fig2)
    print(f"Saved {compat_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--outdir", default="output/figures")
    parser.add_argument("--backend", default=None)
    args = parser.parse_args()

    df = load_timing_jobs(args.db)
    if args.backend:
        df = df[df["backend"] == args.backend]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Plot each backend separately if multiple
    backends = df["backend"].unique()
    for b in backends:
        plot_timing_summary(df[df["backend"] == b], outdir, backend_name=b)

    if len(backends) > 1:
        plot_timing_summary(df, outdir, backend_name="combined")


if __name__ == "__main__":
    main()
