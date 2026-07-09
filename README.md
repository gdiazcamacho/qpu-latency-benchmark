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

## Installation

**Local development / `fake` backend only** (no real hardware access needed):

```bash
git clone <this-repo>
cd qpu-latency-benchmark
pip install -e .
cp .env.example .env   # not needed for fake, but harmless to have
python -m latency_benchmark.run_experiment --backend fake --family qft --axis width
```

`pip install -e .` covers everything needed for `--backend fake`: qiskit,
qiskit-aer, pyyaml, numpy, pandas, matplotlib. If this is your first time
in the repo, start here -- it requires no credentials, no cluster access,
and exercises the full pipeline (config building, circuit families,
orchestration, SQLite output, analysis) end to end.

**QMIO (CESGA)**: not pip-installable -- `qmio-tools` and a matching Qiskit
version come from CESGA's environment modules, loaded via
`module load qmio/hpc qmio-tools/... qiskit/...` (see `jobs/run_slurm.sh`,
which has the exact module versions currently in use -- these are
CESGA-specific and may need updating as the module stack evolves). You'll
also need calibration file read access at
`configs/backends/qmio.yaml`'s `calibration_dir` -- ask your CESGA contact
if `find_latest_calibration_file()` (in `backends/qmio.py`) can't find
anything there.

**QExa20 (LRZ via MQSS)**: needs the `mqss.qiskit_adapter` package (not on
public PyPI -- ask your LRZ/MQSS contact for access) and an API token. Copy
`.env.example` to `.env` and fill in `MQSS_TOKEN` (and `MQSS_URL`/
`MQSS_PORT` if different from the defaults). `.env` is gitignored --
never commit it. `jobs/run_direct.sh` sources `.env` automatically; if
running commands manually (e.g. `check_routing.py`), source it yourself
first: `set -a; source .env; set +a`.



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

## Deeper overhead-decomposition analysis

`fit_probe.py` (documented above) fits the simple registry model
(linear or quadratic) for a single probe. Three additional tools implement
the project's original `T = T0 + alpha*N (+ beta*depth)` overhead model,
with automatic term selection, across any probe already in the database:

```bash
# Fit T0 (fixed overhead) + alpha (per-circuit cost), auto-adding a
# depth term only if it meaningfully improves R²
python -m latency_benchmark.analysis.fit_models \
    --db output/db/timing_results_<date>.sqlite \
    --experiment-name single_qubit_batch_qmio

# Same model, fit and compared across every backend present in the DB,
# plus a summary figure
python -m latency_benchmark.analysis.compare_backends \
    --db output/db/timing_results_<date>.sqlite

# 4-panel diagnostic figure: walltime vs N, per-circuit overhead vs N,
# backend_run/result_wait breakdown, residuals
python -m latency_benchmark.analysis.plot_overheads \
    --db output/db/timing_results_<date>.sqlite --backend qmio \
    --outdir output/figures
```

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

## Common issues

- **`MQSS_TOKEN is not set. Aborting.`** -- `.env` is missing or wasn't
  sourced. `jobs/run_direct.sh` sources it automatically; if you're
  running a script directly (e.g. `check_routing.py`, or any manual
  `python` invocation), source it yourself first:
  `set -a; source .env; set +a`.

- **A SLURM sweep is missing some points, with no error rows in the DB**
  -- almost always the job hit `run_slurm.sh`'s `-t` time limit and was
  killed mid-sweep. SLURM gives no chance to log a failure for points that
  never got to run. Increase the time limit for large sweeps, e.g.
  `sbatch --time=02:00:00 jobs/run_slurm.sh ...` (overrides the script's
  `#SBATCH -t` directive, no file edit needed). Check
  `output/raw/<jobname>_<jobid>.out` for a truncated point count as
  confirmation.

- **`Repo: /var/spool/slurmd` in a job's `.out` log, followed by an
  import error** -- SLURM copies submitted scripts to a spool directory
  before executing them, so `${BASH_SOURCE[0]}` no longer points at the
  real repo. `jobs/run_slurm.sh` already handles this via
  `SLURM_SUBMIT_DIR`; if you've written a new job script from scratch
  instead of copying `run_slurm.sh`, make sure it does the same.

- **QExa20 prints `Warning: Instruction 'if_else' not found in the
  instruction_map` / similar** -- benign, comes from MQSS's instruction-set
  metadata not covering every Qiskit control-flow instruction. Doesn't
  affect circuits that don't use those instructions (none of the current
  circuit families do).

- **Comparing `transpiled_depth_mean` across two runs and getting
  different numbers for the identical circuit/backend** -- check
  `backend_options.seed_transpiler` is set (both `configs/backends/*.yaml`
  default to `42`). Without a fixed seed, Qiskit's routing pass is
  stochastic and can produce meaningfully different depths for the same
  input across separate process launches -- this was a real, confusing
  bug hunted down during this project's development; see
  `scripts/check_routing.py` for the verification tool that catches it.

- **Comparing depth/connectivity across backends and the result looks
  backwards** -- confirm `optimization_level` matches in both
  `configs/backends/*.yaml`. A mismatched optimization level changes
  transpiled depth independently of any real hardware difference, and can
  produce a comparison that's precisely inverted from the truth (this
  happened during development: QMIO appeared to have *better*
  connectivity than QExa20 until this was fixed, when it turned out to
  have worse connectivity, as expected from the two backends' real
  coupling maps).

- **`<date>` in a command from this README or from your own notes** -- that's
  a placeholder, not literal syntax; bash will try to interpret it as a
  redirection and fail. Substitute the real date from the `Output DB: ...`
  line printed at the start of every run, or `ls output/db/`.

## Future directions

* Changepoint detection for the single-qubit width/depth "jump" hypothesis
* Confirming whether QExa20/QMIO client libraries support caller-chosen IR
  formats at submission time (vs. local-only serialization timing)
* Cross-platform latency comparison reporting
* Additional backend adapters
