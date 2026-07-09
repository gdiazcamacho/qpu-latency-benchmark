#!/bin/bash
#SBATCH -p qpu
#SBATCH --mem-per-cpu=4G
#SBATCH -c 1
#SBATCH -t 01:00:00
#SBATCH -o output/raw/%x_%j.out
#SBATCH -e output/raw/%x_%j.err
# ============================================================================
# SITE-SPECIFIC -- this script is written for CESGA's SLURM cluster.
# If you are running this at a different site, you will need to edit:
#   - #SBATCH -p qpu          (the partition/queue name for your cluster)
#   - the `module load` line below (your site's module names/versions for
#     Python, Qiskit, and any backend-specific client library)
#   - -t 01:00:00              (increase if your sweeps run long; a QMIO
#     job hitting this limit mid-sweep fails SILENTLY -- points after the
#     cutoff are simply missing from the DB, with no error row logged)
# Everything else (REPO_ROOT resolution, argument forwarding, resolved-config
# dump) is generic and should work unchanged at any SLURM site.
# ============================================================================
# Generic SLURM runner for backends needing a QPU-attached compute node
# (qmio, fake). Forwards all arguments to run_experiment.
#
# Submit from repo root, e.g.:
#   sbatch -J qft_width_qmio jobs/run_slurm.sh --backend qmio --family qft --axis width
#   sbatch -J sq_batch_qmio jobs/run_slurm.sh --backend qmio --family single_qubit --axis batch --values 1,2,4,8
set -euo pipefail

# SLURM copies this script to /var/spool/slurmd before executing it, so
# BASH_SOURCE no longer points at the real file under sbatch -- use
# SLURM_SUBMIT_DIR (the directory sbatch was invoked from) instead, with
# a BASH_SOURCE-based fallback for direct/interactive invocation.
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    REPO_ROOT="$SLURM_SUBMIT_DIR"
else
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$REPO_ROOT"

echo "========================================="
echo " QPU Latency Benchmark — SLURM run"
echo " SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo " Args: $*"
echo "========================================="

module purge || true
# SITE-SPECIFIC: CESGA module names/versions -- edit for your cluster.
module load qmio/hpc gcc/12.3.0 qmio-tools/0.2.1-python-3.11.9 qiskit/1.2.4-python-3.11.9 || true

echo "START $(date +%s.%N)"
python -m latency_benchmark.run_experiment "$@" --date-stamp
echo "END $(date +%s.%N)"
echo "========================================="
echo " Done — $(date)"
echo "========================================="
