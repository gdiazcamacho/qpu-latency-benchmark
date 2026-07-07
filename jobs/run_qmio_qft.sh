#!/bin/bash
#SBATCH -J latency_qmio_qft
#SBATCH -p qpu
#SBATCH --mem-per-cpu=4G
#SBATCH -c 1
#SBATCH -t 01:00:00
#SBATCH -o output/raw/latency_qmio_qft_%j.out
#SBATCH -e output/raw/latency_qmio_qft_%j.err
# Run only the QMIO qft_inverse probe.
# Safe to re-run — appends to existing DB, does not overwrite.
# Submit from repo root: sbatch jobs/run_qmio_qft.sh
set -euo pipefail
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    REPO_ROOT="$SLURM_SUBMIT_DIR"
else
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$REPO_ROOT"
echo "========================================="
echo " QPU Latency Benchmark — QMIO QFT-inverse probe"
echo " SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo "========================================="
module purge || true
module load qmio/hpc gcc/12.3.0 qmio-tools/0.2.1-python-3.11.9 qiskit/1.2.4-python-3.11.9 || true
echo ""
echo "Running: configs/probes/qft_inverse_qmio.yaml"
echo "START $(date +%s.%N)"
python -m latency_benchmark.run_experiment \
    --config configs/probes/qft_inverse_qmio.yaml \
    --date-stamp
echo "END $(date +%s.%N)"
echo "========================================="
echo " Done — $(date)"
echo "========================================="