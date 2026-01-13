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
`--out` writes `raw.csv` into the given directory.

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
