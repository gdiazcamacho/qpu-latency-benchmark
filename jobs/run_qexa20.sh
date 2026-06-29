#!/bin/bash
# Run all QExa20 latency probes (including extended sweep points).
# Sources .env for MQSS credentials — run from the repo root:
#   bash jobs/run_qexa20.sh
#
# Probe order (smallest → largest total circuit submissions):
#   shot_scaling       :  12 submissions  (base)
#   shot_scaling_ext   :   3 submissions  (100000 shots)
#   width_scaling      :  15 submissions
#   depth_scaling      :  24 submissions
#   batch_scaling      :  45 submissions  (N=1..8)
#   batch_scaling_ext  : 144 submissions  (N=16,32)  ← longest, run last
#
# Total: ~243 circuit submissions to QExa20.
# At ~3-10s/job depending on queue, expect 15-45 min wall time.

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
echo " QPU Latency Benchmark — QExa20 backend"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo " MQSS_URL: ${MQSS_URL:-<not set>}"
echo " MQSS_BACKEND: ${MQSS_BACKEND:-QExa20}"
echo "========================================="

run_probe() {
    local config="$1"
    echo ""
    echo "-----------------------------------------"
    echo "Running: $config"
    echo "START $(date +%s.%N)"
    echo "-----------------------------------------"
    python -m latency_benchmark.run_experiment --config "$config" --date-stamp
    local exit_code=$?
    echo "END $(date +%s.%N)"
    if [ $exit_code -ne 0 ]; then
        echo "WARNING: probe exited with code $exit_code — continuing"
    fi
    return 0
}

# Base probes (already have some data — these add more repetitions/points)
run_probe configs/probes/shot_scaling_qexa20.yaml
run_probe configs/probes/width_scaling_qexa20.yaml
run_probe configs/probes/depth_scaling_qexa20.yaml
run_probe configs/probes/batch_scaling_qexa20.yaml

# Extended probes (fill gaps vs fake/qmio sweep ranges)
run_probe configs/probes/shot_scaling_qexa20_ext.yaml
run_probe configs/probes/batch_scaling_qexa20_ext.yaml

echo ""
echo "========================================="
echo " All QExa20 probes done — $(date)"
echo "========================================="
