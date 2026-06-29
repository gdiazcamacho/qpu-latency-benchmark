#!/bin/bash
#SBATCH -J latency_qmio
#SBATCH -p qpu
#SBATCH --mem-per-cpu=4G
#SBATCH -c 1
#SBATCH -t 02:00:00
#SBATCH -o output/raw/latency_qmio_%j.out
#SBATCH -e output/raw/latency_qmio_%j.err

# Run all four QMIO latency probes sequentially in one SLURM job.
# Submit from the repo root: sbatch jobs/run_qmio.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "========================================="
echo " QPU Latency Benchmark — QMIO backend"
echo " SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo "========================================="

module purge || true
module load qmio/hpc gcc/12.3.0 qmio-tools/0.2.1-python-3.11.9 qiskit/1.2.4-python-3.11.9 || true

run_probe() {
    local config="$1"
    echo ""
    echo "-----------------------------------------"
    echo "Running: $config"
    echo "START $(date +%s.%N)"
    echo "-----------------------------------------"
    python -m latency_benchmark.run_experiment --config "$config" --date-stamp
    echo "END $(date +%s.%N)"
}

run_probe configs/probes/batch_scaling_qmio.yaml
run_probe configs/probes/depth_scaling_qmio.yaml
run_probe configs/probes/shot_scaling_qmio.yaml
run_probe configs/probes/width_scaling_qmio.yaml

echo ""
echo "========================================="
echo " All QMIO probes done — $(date)"
echo "========================================="
