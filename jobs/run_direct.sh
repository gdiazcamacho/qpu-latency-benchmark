#!/bin/bash
# Generic direct runner for REST-API backends that don't need a SLURM
# allocation (qexa20, via MQSS). Forwards all arguments to run_experiment.
#
# Run from repo root, e.g.:
#   bash jobs/run_direct.sh --backend qexa20 --family qft --axis width
#   bash jobs/run_direct.sh --backend qexa20 --family single_qubit --axis batch --values 1 --repetitions 20
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -f .env ]; then
    echo "Loading credentials from .env"
    set -a
    source .env
    set +a
else
    echo "WARNING: .env not found — MQSS_TOKEN must already be in environment"
fi

if [ -z "${MQSS_TOKEN:-}" ]; then
    echo "ERROR: MQSS_TOKEN is not set. Aborting."
    exit 1
fi

echo "========================================="
echo " QPU Latency Benchmark — direct run"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo " Args: $*"
echo "========================================="

echo "START $(date +%s.%N)"
python -m latency_benchmark.run_experiment "$@" --date-stamp
echo "END $(date +%s.%N)"
echo "========================================="
echo " Done — $(date)"
echo "========================================="
