# Timing Overheads Benchmark

Benchmark to estimate hidden fixed, per-circuit, and execution-dependent overheads in batched quantum jobs.

The benchmark varies:

- number of circuits per job, `n_circuits`
- synthetic circuit depth, `depth`
- shots
- circuit family
- backend

A simple model is:

```text
T_job(N, d, S) = T0 + alpha * N + beta * N * S * d
```

or, when an estimated quantum duration is available:

```text
T_job = T0 + alpha * n_circuits + beta * estimated_quantum_time
```

## First run

Dry-run/fake backend:

```bash
python -m timing_benchmark.run_experiment --config configs/fake_timing.yaml
```

Analyze:

```bash
python -m timing_benchmark.analysis.fit_models --db output/db/timing_results.sqlite
```

## QMIO run

Edit `configs/qmio_timing.yaml`, then submit:

```bash
sbatch jobs/submit_qmio_timing.sh
```

## Main outputs

The SQLite table `timing_jobs` stores one row per submitted job/matrix point.
The IQM-specific table `timing_events` can store detailed per-event timestamps if available.
