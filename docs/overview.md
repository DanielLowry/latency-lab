# Phase 1 Overview

## Context and background

Phase 1 shifts from reading (OSTEP 1-5) into doing: build a reusable microbenchmark harness and use it to measure OS primitives like `fork()` and `exec()` with full distributions (p50/p95/p99/p999) plus reproducible run metadata.

The shift from "algorithm benchmarking" to "latency engineering" is:

- measure distributions, not just averages
- ensure reproducibility by controlling and recording environment
- keep the harness extensible so future labs are "add a new case", not "rewrite tooling"

These docs propose a pragmatic architecture and a phased implementation plan.

See `docs/architecture.md` for the system design and `docs/backlog.md` for the execution tracker.

---

## Vision

- Build a stable "Latency Lab" harness that makes tail-latency measurements routine.
- Keep results file-based for easy comparison over time.
- Preserve a clear path to expand into later phases (perf tooling, concurrency, networking).

---

## Scope boundaries (Phase 1)

- Build the microbenchmark harness and run controls.
- Measure tiny OS operations and capture tail latency (p99+).
- Produce consistent outputs: `raw.csv`, `meta.json`, `stdout.txt`.
- Support controlled toggles (pinning, noise vs quiet, warmup vs measurement).
- Start with the single-binary registry approach; keep a migration path to other layouts.

---

## Non-goals (Phase 1)

- Cycle-accurate timing (`rdtsc/rdtscp`, fences, TSC calibration).
- Full statistical inference or hypothesis testing framework.
- Database-backed storage and query UI.
- Plugin ABI/versioning complexity.

---

## User journeys

- As a lab author, I add a new case by creating a new `.cpp` file that registers itself; no harness edits.
- As a runner, I execute a case with CLI flags and receive `raw.csv`, `meta.json`, and a readable summary.
- As an analyst, I compare runs using the results folder layout to understand p50/p95/p99/p999 shifts.
