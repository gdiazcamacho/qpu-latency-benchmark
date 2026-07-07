# QPU Latency Benchmark

A benchmarking framework for characterizing latency, overheads, and execution
scaling on quantum computing platforms (currently: QMIO at CESGA, QExa20 at
LRZ via MQSS, and a local AerSimulator "fake" backend for development).

The core model: total job walltime decomposes into orchestration overhead
versus actual quantum execution time. Systematic probes vary one structural
parameter at a time (batch size, shots, qubit count, circuit depth) and fit
a timing model to the result, so hidden backend behavior (queueing,
compilation cost, execution scaling) can be inferred and compared across
platforms.

## Three orthogonal axes, not a file per combination

Every probe is defined by three independent choices:

- **backend**: `qmio`, `qexa20`, or `fake` -- connection/credentials/
  calibration, a property of the hardware (`configs/backends/*.yaml`)
- **family**: `single_qubit` or `qft` (also `qft_no_swap`, `measure_only`)
  -- which circuit gets built (`latency_benchmark/experiments/families/`)
- **axis**: `batch`, `shot`, `width`, or `depth` -- which parameter is swept
  (`latency_benchmark/experiments/axis_defaults.py`)

Default sweep ranges live in one small, reviewable table
(`axis_defaults.py`) rather than being duplicated across dozens of
near-identical YAML files. Not every (family, axis) combination is valid --
`depth` is rejected for the `qft` family, since QFT circuit depth is
structurally derived from qubit count (O(n^2) controlled-phase gates), not
an independently settable parameter. This is enforced automatically: a
mismatched combination raises a clear error instead of silently producing
a meaningless run.

## Quick start

```bash
# Run a probe -- backend, family, and axis are the only required choices
python -m latency_benchmark.run_experiment --backend fake --family qft --axis width

# Override the default sweep values / repetitions for a one-off run
python -m latency_benchmark.run_experiment \
    --backend qmio --family single_qubit --axis batch \
    --values 1,2,4,8,16 --repetitions 5

# Submit to SLURM (qmio, fake -- backends needing a QPU-attached compute node)
sbatch -J qft_width_qmio jobs/run_slurm.sh --backend qmio --family qft --axis width

# Run directly (qexa20 -- REST API via MQSS, no SLURM allocation needed)
bash jobs/run_direct.sh --backend qexa20 --family qft --axis width

# Analyze -- model (linear vs quadratic) is selected automatically from the
# (circuit_family, sweep_axis) registry in analysis/models.py
python -m latency_benchmark.analysis.fit_probe \
    --db output/db/timing_results_<date>.sqlite \
    --experiment-name qft_width_qmio

python -m latency_benchmark.analysis.plot_probe \
    --db output/db/timing_results_<date>.sqlite \
    --experiment-name qft_width_qmio
```

A "queue-noise" probe is not a separate category -- it's the same
mechanism with the sweep pinned to one value and repetitions cranked up:

```bash
bash jobs/run_direct.sh --backend qexa20 --family measure_only --axis batch \
    --values 1 --repetitions 20
```

## Circuit families

- **`single_qubit`**: independent single-qubit gates (RX/RY), no
  entanglement. Depth is an independent, freely-settable parameter --
  expect roughly linear scaling in every axis. Watch for an unexpected
  jump at large width/depth (possible memory pressure or a relaxation-time
  boundary); not automatically detected yet, inspect visually.
- **`qft`** / **`qft_no_swap`**: Fourier-state preparation (fixed,
  non-dyadic phase, hardcoded in `families/entangling.py` -- deliberately
  not config-driven, since it affects rotation angles but not gate count)
  followed by an inverse QFT, with or without the final SWAP network.
  Depth grows as O(n^2) with qubit count; expect quadratic latency scaling
  in the `width` axis specifically, linear in `batch`/`shot` at fixed
  width. Algorithmic correctness (not latency) is checked once via
  `scripts/check_qft_correctness.py` -- run manually after editing the
  circuit, not part of the regular pipeline.
- **`measure_only`**: minimal circuit, just measurement. Cheapest possible
  probe; useful for isolating orchestration/queue overhead from any gate
  cost (see the queue-noise example above).

## IR-format serialization timing (opt-in, off by default)

`--ir-formats qasm2,qasm3` measures local circuit-serialization cost per
format as a diagnostic side-measurement, stored in the `timing_events`
table -- it never affects `walltime_total` or what's actually submitted to
the backend. Whether choosing a wire format could change *real* submitted
execution time depends on whether the underlying client library
(`mqss.qiskit_adapter`, `qmio-tools`) actually accepts a caller-chosen
format at submission time, or always reconverts internally regardless of
input -- that's unconfirmed and worth checking directly against those
libraries before treating IR format as a variable that affects real
walltime rather than just local compile cost. `backends/base.py` has a
`supports_ir_formats()` stub (defaults `False` everywhere) as the seam for
wiring that in once confirmed.

## Data collection

Results go to a date-stamped SQLite DB (`output/db/timing_results_<date>.sqlite`)
with two tables:

- `timing_jobs`: one row per probe point (backend, family, swept
  parameter, transpiled depth, walltime breakdown into
  `walltime_backend_run` + `walltime_result_wait`, success/error)
- `timing_events`: optional finer-grained events (QExa20 per-circuit
  timing if the adapter supports it; IR-format serialization timing if
  requested)

Each run also dumps its fully-resolved config to
`output/raw/resolved_config_<timestamp>.yaml` for reproducibility, since
the actual sweep values now come from a merge of the backend file + axis
defaults + any CLI overrides rather than a single hand-authored file.

## Architecture

```text
configs/
    backends/          # qmio.yaml, qexa20.yaml, fake.yaml -- connection only
    legacy/             # old-style full-matrix configs, still runnable via --config

jobs/
    run_slurm.sh         # generic SLURM wrapper (qmio, fake)
    run_direct.sh        # generic direct wrapper (qexa20, no SLURM needed)

latency_benchmark/
    run_experiment.py    # CLI: --backend --family --axis [--values ...]
    core/
        orchestrator.py    # runs points, times them, saves to SQLite
        database.py         # SQLite schema + save helpers
        models.py            # TimingJobRecord
    backends/
        base.py, fake.py, qmio.py, qexa20.py, factory.py
    experiments/
        families/            # circuit builders + FAMILY_REGISTRY (valid axes per family)
        axis_defaults.py       # default sweep values per (family, axis)
        config_builder.py       # backend file + axis default + CLI overrides -> config
        strategies/matrix.py     # sweep/controls -> point list, validates axis against family
        ir_formats.py             # opt-in local serialization timing
    analysis/
        models.py             # MODEL_REGISTRY: (family, axis) -> linear/quadratic fit
        fit_probe.py            # fits the registered model automatically
        plot_probe.py, compare_backends.py, load_results.py

scripts/
    check_qft_correctness.py  # one-time algorithmic sanity check, not part of the pipeline

output/
    db/       # SQLite results
    raw/      # SLURM .out/.err logs + resolved_config_<timestamp>.yaml per run
    figures/  # generated plots
```

## Adding a new backend

1. Add `latency_benchmark/backends/<name>.py`, subclassing `BackendAdapter`.
2. Register it in `backends/factory.py`.
3. Add `configs/backends/<name>.yaml` with connection details.
4. Add `<name>` to the `--backend` choices in `run_experiment.py`.

No changes needed to families, axes, or analysis -- those are backend-independent.

## Adding a new circuit family

1. Add a builder function to `experiments/families/` (new or existing module).
2. Register it in `experiments/families/__init__.py`'s `FAMILY_REGISTRY`,
   declaring `valid_axes` and whether `depth_is_independent`.
3. Add default sweep values per valid axis to `experiments/axis_defaults.py`.
4. Add `(family, axis)` entries to `analysis/models.py`'s `MODEL_REGISTRY`
   once you know which fit model is appropriate -- don't guess; derive it
   from the circuit's expected gate/depth scaling first.
5. If it's an entangling/structured circuit, consider a one-time
   correctness check under `scripts/`, following
   `check_qft_correctness.py` as a template.

## Future directions

* Changepoint detection for the single-qubit width/depth "jump" hypothesis
* Confirming whether QExa20/QMIO client libraries support caller-chosen IR
  formats at submission time (vs. local-only serialization timing)
* Cross-platform latency comparison reporting
* Additional backend adapters
