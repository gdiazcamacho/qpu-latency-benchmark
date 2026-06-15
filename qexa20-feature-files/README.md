# QPU Latency Benchmark

A benchmarking framework for characterizing latency, overheads, and execution scaling in quantum computing platforms.

The project provides a collection of controlled latency probes that isolate different contributors to quantum job execution time, including batching overheads, compilation costs, queueing delays, readout costs, and quantum execution time.

The framework is designed to work both with:

* instrumented platforms that expose detailed timing information (e.g. QExa20 via MQSS), and
* black-box platforms that only expose aggregate walltimes (e.g. QMIO).

By running systematic latency probes and fitting timing models to the collected measurements, hidden backend behavior can be inferred and compared across quantum computing infrastructures.

## Objectives

The framework aims to answer questions such as:

* How much latency is fixed per submitted job?
* What is the cost of adding more circuits to a batch?
* How does execution time scale with shots?
* How does latency scale with circuit width?
* How does latency scale with circuit depth?
* Which fraction of total latency corresponds to actual quantum execution?

## Latency Probe Suite

The benchmark currently provides four targeted probes.

### Batch Scaling Probe

Measures latency as a function of the number of circuits submitted in a single job.

Primary metric:

* Per-circuit overhead

### Shot Scaling Probe

Measures latency as a function of the number of shots.

Primary metric:

* Visibility of execution and readout costs

### Width Scaling Probe

Measures latency as a function of the number of qubits.

Primary metric:

* Compilation, routing, and measurement scaling

### Depth Scaling Probe

Measures latency as a function of circuit depth.

Primary metric:

* Sensitivity to scheduled circuit duration

### Full Timing Matrix

Performs a combined sweep over multiple parameters to study interactions once relevant scaling dimensions have been identified.

## Architecture

```text
latency_benchmark/
├── backends/
├── core/
├── experiments/
├── analysis/
└── configs/
```

The architecture separates:

* Circuit generation
* Backend execution
* Data collection
* Timing analysis

allowing new backends and new latency probes to be added independently.

## Data Collection

Results are stored in SQLite databases.

Each execution records:

* Backend
* Experiment configuration
* Circuit characteristics
* Timing measurements
* Success and error information

Platforms that expose detailed timing events may additionally record:

* Compilation time
* Queueing time
* Execution time
* Post-processing time

## Quick Start

Run a probe:

```bash
python -m latency_benchmark.run_experiment \
    --config configs/probes/shot_scaling_fake.yaml
```

Submit a QMIO probe:

```bash
sbatch jobs/submit_latency_probe.sh \
    configs/probes/shot_scaling_qmio.yaml
```

Analyze results:

```bash
python -m latency_benchmark.analysis.fit_probe \
    --db output/db/timing_results.sqlite \
    --experiment-name shot_scaling_qmio
```

Generate plots:

```bash
python -m latency_benchmark.analysis.plot_probe \
    --db output/db/timing_results.sqlite \
    --experiment-name shot_scaling_qmio
```

## Future Directions

* QExa20 timeline decomposition
* Cross-platform latency comparison
* Pulse-duration-aware models
* MQSS integration
* Automated benchmark reporting
* Additional backend adapters
