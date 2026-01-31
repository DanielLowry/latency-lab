# Phase 1 Backlog

This is the execution tracker for Phase 1. It keeps the full phased breakdown of Option A and tracks concrete deliverables.

---

# Fully phased implementation plan for Option A

## Phase A0 — Define the contract
**Deliverable**
- [x] `bench/README.md` that specifies:
  - definition of the timed region (only `run_once()` is timed)
  - output schema:
    - `raw.csv`: `iter,ns` (minimum)
    - printed summary: `min,p50,p95,p99,p999,max` (optional mean)
  - required run metadata keys for `meta.json`

**Key decisions**
- [x] Store samples in nanoseconds (`uint64_t`).
- [x] Use a monotonic clock source (`clock_gettime(CLOCK_MONOTONIC_RAW, ...)` on Linux; optional chrono fallback).

---

## Phase A1 — Core harness library (timing + stats + CSV)
**Build**
- [x] `bench/core/timer.h`
  - `now_ns()` implementation
- [x] `bench/core/stats.h`
  - quantiles: min/p50/p95/p99/p999/max
  - Phase 1 approach: collect samples in a vector + sort
- [x] `bench/core/csv.h`
  - write `raw.csv` safely

**Add immediately**
- [x] Warmup iterations.
- [x] A `noop` case (empty measurement) to estimate timer/loop overhead.

**Acceptance criteria**
- [x] You can run a dummy case and produce:
  - printed summary
  - `raw.csv`

---

## Phase A2 — Case interface + registry
**Build**
- [x] `bench/core/case.h`
  - `struct Case { const char* name; void(*setup)(Ctx*); void(*run_once)(Ctx*); void(*teardown)(Ctx*); };`
- [x] `bench/core/registry.h/.cpp`
  - `register_case(const Case&)`
  - `cases()` returns list for enumeration

**Pattern**
- [x] Each benchmark lives in its own `.cpp` file and calls a registration macro at static init time.

**Acceptance criteria**
- [x] Add a new benchmark by adding a `.cpp` file — no harness edits required.
- [x] CLI can list cases and run one by name.

---

## Phase A3 — CLI and run controls
**CLI flags (minimum)**
- [x] `--case <name>`
- [x] `--iters N`
- [x] `--warmup N`
- [x] `--out <dir>`
- [x] `--pin <cpu>` (optional)
- [x] `--tag <string>` (free-form label: `quiet`, `noise`, `warm`, etc.)

**Pinning**
- [x] Implement CPU affinity (`sched_setaffinity`) behind `--pin`.

**Acceptance criteria**
- [x] You can run the same case pinned vs unpinned with identical output schema.

---

## Phase A4 — Metadata capture
**Deliverable**
- [x] `meta.json` written to the output directory containing at least:
  - CPU model + core count
  - kernel version
  - command line used
  - compiler version + build flags
  - pinning status + pinned CPU index (if used)
  - tag(s): `quiet/noise`, `warm/cold`, etc.

**Note**
- [x] Keep this minimal but consistent. You can always add keys later.

**Acceptance criteria**
- [x] Every run folder contains `meta.json`, `stdout.txt`, and `raw.csv`.

---

## Phase A5 — Results folder convention + optional runner script
**Folder convention**
- [x] Use the recommended layout:

```
results/
  <lab>/
    <case>/
      <timestamp>_<tag>/
        meta.json
        stdout.txt
        raw.csv
```

**Optional: tiny Python runner**
- [x] A small script can:
  - create the run directory
  - execute the binary with chosen args
  - capture stdout/stderr into `stdout.txt`

**Note**
- [x] This is intentionally file-based (not database-backed). A DB can be layered on later by crawling `meta.json` files if needed.

---

## Phase A6 — Implement Lab A (first real consumer)
Implement these cases first:

1. [x] `fork_wait`
   - parent forks, child `_exit(0)`, parent `waitpid()`
2. [x] `fork_exec_wait`
   - child `execv("./child_exec")` where `child_exec` does almost nothing

**Outputs**
- [ ] `raw.csv` per case
- [ ] summary printed to stdout
- [ ] a short `results.md` that records p50/p95/p99/p999 under:
  - pinned vs unpinned
  - quiet vs noise (optional)

---

## Phase A7 — Ongoing incremental extensions (don’t rewrite)
As you progress through later Phase 1 labs, extend the harness in small steps:

- [ ] parameter sweeps (e.g., sizes/strides)
- [ ] optional counters (page faults, perf stat outputs) saved into run folder
- [ ] compare script (diff quantiles + key metadata between two runs)
