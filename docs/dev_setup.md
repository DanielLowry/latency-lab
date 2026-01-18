# Development Setup

## Requirements
- CMake 3.28 or newer
- A C++ compiler (g++ or clang++)
- Ninja (recommended)

On Ubuntu/Debian:
```
sudo apt update
sudo apt install ninja-build build-essential cmake
```

## Build (recommended)
This repo uses out-of-source builds.
```
cmake --preset ninja
cmake --build --preset ninja
```

## Build (no Ninja)
```
cmake -S . -B build -G "Unix Makefiles"
cmake --build build
```

## Run
```
./build/bench
```

Optional arguments:
```
./build/bench [out.csv] [iters] [warmup]
```

List registered cases:
```
./build/bench --list
```

Run a specific case:
```
./build/bench --case noop [out.csv] [iters] [warmup]
```

Named options (preferred for clarity):
```
./build/bench --out results --iters 10000 --warmup 1000 --case noop
./build/bench --pin 2 --tag quiet --tag warm
```
`--out` writes `raw.csv`, `meta.json`, and `stdout.txt` into the given directory.

## Runner script (optional)
Use the helper script to create the results layout and capture stdout/stderr.
```
python3 scripts/run_bench.py --lab os --case noop --iters 10000 --warmup 1000 --tag quiet
```
This creates:
```
results/<lab>/<case>/<timestamp>_<tag>/
  raw.csv
  meta.json
  stdout.txt
```

## Verify pinning from the shell
You can inspect the process affinity from the outside using the PID.
```
./build/bench --pin 2 --case noop --iters 10000000 --warmup 0 --out /tmp/bench &
pid=$!
grep Cpus_allowed_list /proc/$pid/status
wait $pid
```

If `taskset` is available, this is also convenient:
```
taskset -pc $pid
```

Defaults:
- out.csv: `raw.csv`
- iters: `10000`
- warmup: `1000`

## Clean
```
cmake --build build --target clean
```

## Tests
```
ctest --test-dir build --output-on-failure
```

## Python tools
See `docs/python_tools.md` for installing the Python environment, running the
bench runner script, and using the analysis notebook.
