# Timing Overheads Benchmark

Benchmark to characterize and decompose quantum job execution time into:

- **T₀** — fixed per-job overhead (session setup, queue, compilation pipeline)
- **α** — per-circuit overhead (scheduling, classical control, readout per circuit)
- **β** — depth-dependent execution cost (actual quantum time per gate layer)

By running controlled batches of circuits with varying depth and batch size,
and fitting timing models to measured walltimes, the hidden timing structure
of platforms like QMIO can be inferred even without detailed instrumentation.

---

## Model

The general model is:

```
T_job(N, d, S) = T0 + alpha * N + beta * N * d
```

where `N` = number of circuits, `d` = circuit depth, `S` = shots.

When depth is not a significant predictor (as observed on QMIO), the
simplified model is preferred automatically:

```
T_job(N) = T0 + alpha * N          (R² ≈ 0.9998 on QMIO)
```

When IQM provides estimated quantum execution time per job (`QT`):

```
T_job = T0 + alpha * N + beta * QT
```

### QMIO findings (2026-04-29)

| Parameter | Value |
|---|---|
| T₀ (fixed job overhead) | ~0 s (negligible) |
| α (per-circuit overhead) | **871 ms / circuit** |
| Depth sensitivity | **None** (ΔR² < 0.01%) |
| walltime_result_wait fraction | < 0.001% |

**Key insight:** On QMIO, essentially all time is consumed inside `backend.run()`.
The per-circuit overhead of ~871 ms is independent of circuit depth,
suggesting that scheduling/serialization cost dominates over quantum execution time
for shallow circuits (≤16 layers on 2 qubits at 1000 shots).

---

## Project structure

```
timing_overheads/
├── configs/
│   ├── fake_timing.yaml          # Dry-run / Aer simulator
│   ├── qmio_timing.yaml          # QMIO / CESGA SLURM
│   └── iqm_timing.yaml           # IQM Resonance (fill URL/token)
├── jobs/
│   └── submit_qmio_timing.sh     # SLURM job script
├── timing_benchmark/
│   ├── backends/
│   │   ├── base.py               # BackendAdapter ABC
│   │   ├── factory.py            # make_backend_adapter()
│   │   ├── fake.py               # AerSimulator
│   │   ├── qmio.py               # QmioBackend (qmiotools)
│   │   └── iqm.py                # IQM Resonance + timing event extraction
│   ├── core/
│   │   ├── orchestrator.py       # Runs matrix, records results
│   │   ├── database.py           # SQLite: timing_jobs + timing_events
│   │   └── models.py             # TimingJobRecord dataclass
│   ├── experiments/
│   │   ├── builders/
│   │   │   └── synthetic_circuits.py  # measure_only, single_qubit_layers
│   │   └── strategies/
│   │       └── matrix.py         # expand_matrix() — Cartesian product
│   └── analysis/
│       ├── load_results.py       # load_timing_jobs(db_path) → DataFrame
│       ├── fit_models.py         # All timing models + auto-select
│       ├── plot_overheads.py     # 4-panel per-backend figure
│       └── compare_backends.py  # Cross-backend comparison figure
└── output/
    ├── db/timing_results.sqlite
    ├── figures/
    └── raw/                      # SLURM stdout/stderr
```

---

## Quickstart

### Dry run (local, AerSimulator)

```bash
pip install -r requirements.txt
python -m timing_benchmark.run_experiment --config configs/fake_timing.yaml
```

### Analyse and plot

```bash
# Fit models (auto-selects best)
python -m timing_benchmark.analysis.fit_models --db output/db/timing_results.sqlite --model all

# Generate per-backend 4-panel figures
python -m timing_benchmark.analysis.plot_overheads --db output/db/timing_results.sqlite

# Cross-backend comparison
python -m timing_benchmark.analysis.compare_backends --db output/db/timing_results.sqlite
```

### QMIO (CESGA SLURM)

```bash
sbatch jobs/submit_qmio_timing.sh
```

### IQM Resonance

1. Install: `pip install qiskit-iqm`
2. Edit `configs/iqm_timing.yaml` — set `url` and `token`
3. Run: `python -m timing_benchmark.run_experiment --config configs/iqm_timing.yaml`

IQM will additionally populate the `timing_events` table with per-circuit
compile/execute/readout durations, enabling the `linear_N_qt` model.

---

## Adding a new backend

1. Create `timing_benchmark/backends/mybackend.py`:

```python
from .base import BackendAdapter

class MyBackendAdapter(BackendAdapter):
    name = "mybackend"

    def get_backend(self):
        from mylib import MyBackend
        return MyBackend()

    def metadata(self):
        return {"version": "1.0"}
```

2. Register it in `backends/factory.py`:

```python
from .mybackend import MyBackendAdapter

def make_backend_adapter(name, options):
    ...
    if name == "mybackend":
        return MyBackendAdapter(**options)
```

3. Add a config `configs/mybackend_timing.yaml` following the existing pattern.

## Latency probe suite

The project now supports two config styles.

The original `matrix:` style is still supported for full `N × depth` experiments.
For targeted characterization, use the new probe style:

```yaml
experiment_name: shot_scaling_qmio
experiment_type: shot_scaling
backend: qmio
output_db: output/db/timing_results.sqlite

sweep:
  shots: [10, 100, 1000, 10000, 100000]

controls:
  n_circuits: 1
  depth: 4
  n_qubits: 2
  circuit_family: single_qubit_layers

repetitions: 3
randomize_order: true
```

Available probe templates are in `configs/probes/`:

```text
batch_scaling_{fake,qmio,iqm}.yaml
shot_scaling_{fake,qmio,iqm}.yaml
width_scaling_{fake,qmio,iqm}.yaml
depth_scaling_{fake,qmio,iqm}.yaml
```

The intended interpretation is:

```text
Batch scaling:   per-circuit overhead
Shot scaling:    execution/readout visibility
Width scaling:   qubit-count, compilation, routing, measurement effects
Depth scaling:   scheduled-duration sensitivity
Full matrix:     confirm interactions once relevant axes are known
```

Run one probe locally or inside a Slurm job:

```bash
python -m timing_benchmark.run_experiment --config configs/probes/shot_scaling_fake.yaml
```

On QMIO:

```bash
sbatch jobs/submit_latency_probe.sh configs/probes/shot_scaling_qmio.yaml
```

Analyze one probe:

```bash
python -m timing_benchmark.analysis.fit_probe \
  --db output/db/timing_results.sqlite \
  --experiment-name shot_scaling_qmio

python -m timing_benchmark.analysis.plot_probe \
  --db output/db/timing_results.sqlite \
  --experiment-name shot_scaling_qmio
```

The older full-matrix analysis still works:

```bash
python -m timing_benchmark.analysis.fit_models --db output/db/timing_results.sqlite --backend qmio
python -m timing_benchmark.analysis.plot_overheads --db output/db/timing_results.sqlite --backend qmio
```
