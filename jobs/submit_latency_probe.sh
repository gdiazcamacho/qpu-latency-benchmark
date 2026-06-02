#!/bin/bash
#SBATCH -J latency_probe
#SBATCH -p qpu
#SBATCH --mem-per-cpu=4G
#SBATCH -c 1
#SBATCH -t 02:00:00
#SBATCH -o output/raw/latency_probe_%j.out
#SBATCH -e output/raw/latency_probe_%j.err

set -euo pipefail

CONFIG=${1:-configs/probes/batch_scaling_qmio.yaml}

echo "SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
echo "CONFIG=${CONFIG}"
echo "START_EPOCH=$(date +%s.%N)"

module purge || true
module load qmio/hpc gcc/12.3.0 qmio-tools/0.2.1-python-3.11.9 qiskit/1.2.4-python-3.11.9 || true

python -m timing_benchmark.run_experiment --config "${CONFIG}"

echo "END_EPOCH=$(date +%s.%N)"
