# Microbench Harness Contract

This document defines the timed region, output schema, and required metadata for Phase 1.

## Timed region

- Only `run_once()` is timed.
- `setup()` and `teardown()` are explicitly excluded.
- Warmup iterations run before measurement and are not recorded.

## Output schema

### `raw.csv`
- Header: `iter,ns`
- `iter` is 0-based.
- `ns` is the elapsed time per iteration in nanoseconds (`uint64_t`).

### stdout summary
- Print quantiles: `min,p50,p95,p99,p999,max`.
- Optional: include `mean` if convenient.

### `meta.json`
Required keys:
- `cpu_model`
- `cpu_cores`
- `kernel_version`
- `command_line`
- `compiler_version`
- `build_flags`
- `pinning` (boolean)
- `pinned_cpu` (only when `pinning=true`)
- `tags` (array of strings, e.g., `quiet`, `noise`, `warm`, `cold`)

Note: keep this minimal but consistent; add keys later as needed.

## Timing source and units

- Store all samples as nanoseconds (`uint64_t`).
- Use a monotonic clock source:
  - Linux: `clock_gettime(CLOCK_MONOTONIC_RAW, ...)`
  - Fallback: `std::chrono::steady_clock` if needed
