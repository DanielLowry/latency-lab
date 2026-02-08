# Development Setup

This guide covers the C++ toolchain, build commands, and day-to-day run/test
workflow for the benchmark harness.

## Platform and build model

- Linux is currently required for the full bench target (`fork_exec_wait` is
  Linux-only).
- Builds must be out-of-source (`cmake -S . -B <build-dir>`). In-source builds
  are blocked by the top-level `CMakeLists.txt`.

## Required dependencies

- CMake 3.28+
- A C++23 compiler (`g++` or `clang++`)
- Ninja (recommended generator)
- GDB (optional, for debugging in terminal/VS Code)

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install build-essential cmake ninja-build gdb
```

## Configure and build

The repo ships CMake presets for both release and debug builds.

### Release preset

```bash
cmake --preset ninja
cmake --build --preset ninja
```

Artifacts are written to `build/` (including `build/bench`).

### Debug preset

```bash
cmake --preset ninja-debug
cmake --build --preset ninja-debug
```

Artifacts are written to `build-debug/` (including `build-debug/bench`).

### Without presets (manual equivalent)

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build

cmake -S . -B build-debug -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug
```

## Running the benchmark

List available cases:

```bash
./build/bench --list
```

Quick run:

```bash
./build/bench --case noop --iters 10000 --warmup 1000
```

Run with output directory:

```bash
./build/bench --case noop --iters 10000 --warmup 1000 --out results/manual
```

`--out` writes `raw.csv`, `meta.json`, and `stdout.txt` in that directory.

Defaults:

- output path: `raw.csv`
- iters: `10000`
- warmup: `1000`

## Tests

Run tests for release build:

```bash
ctest --test-dir build --output-on-failure
```

Run tests for debug build:

```bash
ctest --test-dir build-debug --output-on-failure
```

## Debugging notes

- Build with `ninja-debug` before stepping through C++ source.
- If using VS Code and `cppdbg`, set `program` to the debug binary:
  `${workspaceFolder}/build-debug/bench`.

## Runner script (optional)

Use the helper script to create the results layout and capture stdout/stderr:

```bash
python3 scripts/run_bench.py --lab os --case noop --iters 10000 --warmup 1000 --tag quiet
```

Output layout:

```text
results/<lab>/<case>/<timestamp>_<tag>/
  raw.csv
  meta.json
  stdout.txt
```

## Verify CPU pinning

From another shell:

```bash
./build/bench --pin 2 --case noop --iters 10000000 --warmup 0 --out /tmp/bench &
pid=$!
grep Cpus_allowed_list /proc/$pid/status
wait $pid
```

If `taskset` is installed:

```bash
taskset -pc "$pid"
```

## Clean build outputs

```bash
cmake --build --preset ninja --target clean
cmake --build --preset ninja-debug --target clean
```

## Python tooling

For the notebook environment and analysis helpers, see `docs/python_tools.md`.
