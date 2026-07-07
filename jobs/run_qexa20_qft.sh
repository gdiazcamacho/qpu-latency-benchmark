#!/bin/bash
# Run only the QExa20 qft_inverse probe.
# Sources .env for MQSS credentials — run from the repo root:
#   bash jobs/run_qexa20_qft.sh
# Safe to re-run — appends to existing DB, does not overwrite.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load MQSS credentials from .env if present
if [ -f .env ]; then
    echo "Loading credentials from .env"
    set -a
    source .env
    set +a
else
    echo "WARNING: .env not found — MQSS_TOKEN must already be in environment"
fi

# Verify token is set before spending time on circuit submissions
if [ -z "${MQSS_TOKEN:-}" ]; then
    echo "ERROR: MQSS_TOKEN is not set. Aborting."
    exit 1
fi

echo "========================================="
echo " QPU Latency Benchmark — QExa20 QFT-inverse probe"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo " MQSS_URL: ${MQSS_URL:-<not set>}"
echo " MQSS_BACKEND: ${MQSS_BACKEND:-QExa20}"
echo "========================================="
echo ""
echo "Running: configs/probes/qft_inverse_qexa20.yaml"
echo "START $(date +%s.%N)"
python -m latency_benchmark.run_experiment \
    --config configs/probes/qft_inverse_qexa20.yaml \
    --date-stamp
echo "END $(date +%s.%N)"
echo "========================================="
echo " Done — $(date)"
echo "========================================="