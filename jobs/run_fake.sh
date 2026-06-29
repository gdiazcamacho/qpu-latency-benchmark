#!/bin/bash
# Run all four fake-backend probes sequentially.
# Fast (seconds total) — no queue, no hardware, no credentials needed.
# Run from the repo root: bash jobs/run_fake.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "========================================="
echo " QPU Latency Benchmark — Fake backend"
echo " $(date)"
echo " Repo: $REPO_ROOT"
echo "========================================="

run_probe() {
    local config="$1"
    echo ""
    echo "-----------------------------------------"
    echo "Running: $config"
    echo "-----------------------------------------"
    python -m latency_benchmark.run_experiment --config "$config" --date-stamp
}

run_probe configs/probes/batch_scaling_fake.yaml
run_probe configs/probes/depth_scaling_fake.yaml
run_probe configs/probes/shot_scaling_fake.yaml
run_probe configs/probes/width_scaling_fake.yaml

echo ""
echo "========================================="
echo " All fake probes done — $(date)"
echo "========================================="
