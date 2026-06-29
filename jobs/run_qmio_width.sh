#!/bin/bash
#SBATCH -J latency_qmio_width
#SBATCH -p qpu
#SBATCH --mem-per-cpu=4G
#SBATCH -c 1
#SBATCH -t 01:00:00
#SBATCH -o output/raw/latency_qmio_width_%j.out
#SBATCH -e output/raw/latency_qmio_width_%j.err

# Run only the QMIO width_scaling probe.
# Safe to re-run — appends to existing DB, does not overwrite.
# Submit from repo root: sbatch jobs/run_qmio_width.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "========================================="
echo " QPU Latency Benchmark — QMIO width scaling"
echo " SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo "========================================="

module purge || true
module load qmio/hpc gcc/12.3.0 qmio-tools/0.2.1-python-3.11.9 qiskit/1.2.4-python-3.11.9 || true

echo ""
echo "Running: configs/probes/width_scaling_qmio.yaml"
echo "START $(date +%s.%N)"

python -m latency_benchmark.run_experiment \
    --config configs/probes/width_scaling_qmio.yaml \
    --date-stamp

echo "END $(date +%s.%N)"
echo "========================================="
echo " Done — $(date)"
echo "========================================="