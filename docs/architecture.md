# Phase 1 Architecture

## System design

### Option A (start here): single binary + case registry
- One executable (e.g., `bench`) contains the harness (timing loop, warmup, quantiles, CSV), a registry of benchmark cases, and the CLI.
- Each case lives in its own `.cpp` file and registers itself; adding a case does not require editing the harness.

Why this is the best Phase 1 starting point:
- Minimal complexity.
- Clean separation between the measurement engine and what is being measured.
- Fast iteration during Phase 1.

### Option B (future): one binary per benchmark
- Each lab/case is its own executable (e.g., `bench_fork`, `bench_mmap`) linking a shared harness library.
- Useful when cases need special build flags or runtime environments, or when isolation is important.

Tradeoffs:
- More build artifacts.
- Slightly more repo clutter, but strong isolation per executable.

### Option C (future): plugin/shared-library cases
- A stable harness executable loads `.so` modules at runtime and discovers cases via exported symbols.
- Useful when you want to add cases without rebuilding the harness, at the cost of ABI discipline.

Tradeoffs:
- Added complexity (ABI, packaging, discovery).
- Not a performance win by itself; it is a workflow/productization choice.

**Recommendation:** start with Option A, but keep the case API C-like (POD structs + function pointers) so migration to B or C is mechanical. This keeps overhead tiny and predictable.

---

## Key invariants

- The timed region is only `run_once()` for a case; setup/teardown is excluded.
- Store samples in nanoseconds (`uint64_t`).
- Use a monotonic clock (`clock_gettime(CLOCK_MONOTONIC_RAW, ...)` on Linux; fallback to `std::chrono` if needed).
- Produce consistent outputs every run: `raw.csv`, `meta.json`, and a stdout summary with `min,p50,p95,p99,p999,max,mean,iters`.
- The stdout summary includes mean and iteration count for quick sanity checks.
- The harness is extensible without edits to core code: adding a case is a new file with a registration macro.
- Avoid per-iteration overhead in the hot path; keep the case interface lightweight and avoid `std::function`.

---

## Data model

- `raw.csv`: per-iteration samples, minimum schema `iter,ns`.
- `meta.json`: run metadata, including:
  - CPU model and core count
  - kernel version
  - command line used
  - compiler version and build flags
  - pinning status and CPU index (if used)
  - tags (e.g., `quiet`, `noise`, `warm`, `cold`)
- `stdout.txt`: human-readable summary with quantiles (one per line).

Note: keep `meta.json` minimal but consistent; add keys later as needed.

Recommended results layout:

```
results/
  <lab>/
    <case>/
      <timestamp>_<tag>/
        meta.json
        stdout.txt
        raw.csv
```
This is intentionally file-based (not database-backed). A database can be layered later by crawling `meta.json` files.

---

## APIs

### Case interface
- `struct Case { const char* name; void(*setup)(Ctx*); void(*run_once)(Ctx*); void(*teardown)(Ctx*); };`
- `register_case(const Case&)` and `cases()` enumeration.
- Registration macro for static initialization in each case file.

### CLI
Minimum flags:
- `--case <name>`
- `--iters N`
- `--warmup N`
- `--out <dir>`
- `--pin <cpu>` (optional)
- `--noise off|free|same|other` (optional)
- `--tag <string>` (free-form labels like `quiet`, `noise`, `warm`)

Pinning uses `sched_setaffinity` behind `--pin`.

Optional helper:
- A tiny runner script that creates the output directory and captures stdout/stderr into `stdout.txt`.

---

## Performance constraints

- Capture full distributions (p50/p95/p99/p999), not just averages.
- Warmup iterations are required to stabilize caches and branch predictors.
- Phase 1 quantiles can sort a vector of samples; avoid heavier stats libraries.
- The timed loop should avoid dynamic allocation and complex dispatch.

---

## Migration triggers (A to B or C)

Consider migrating to Option B if:
- specific benchmarks need isolation or special build flags
- you want "one binary per lab" packaging
- you care about address-space contents for a particular experiment

Consider migrating to Option C if:
- you want a stable harness tool and modular bench packs
- you are ready to manage ABI discipline and versioning
- you want to add cases without rebuilding the harness

Until those triggers appear, Option A is the simplest and best fit.
