#!/bin/bash
#SBATCH -J timing_qmio
#SBATCH -p qpu
#SBATCH --mem-per-cpu=4G
#SBATCH -c 1
#SBATCH -t 02:00:00
#SBATCH -o output/raw/timing_qmio_%j.out
#SBATCH -e output/raw/timing_qmio_%j.err

set -euo pipefail

echo "SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
echo "START_EPOCH=$(date +%s.%N)"

# Adjust modules to your active CESGA/QMIO setup.
module purge || true
module load qmio/hpc gcc/12.3.0 qmio-tools/0.2.1-python-3.11.9 qiskit/1.2.4-python-3.11.9 || true

python -m latency_benchmark.run_experiment --config configs/qmio_timing.yaml

echo "END_EPOCH=$(date +%s.%N)"
