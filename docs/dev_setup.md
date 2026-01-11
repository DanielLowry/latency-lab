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
./build/bench_noop
```

Optional arguments:
```
./build/bench_noop [out.csv] [iters] [warmup]
```

Defaults:
- out.csv: `raw.csv`
- iters: `10000`
- warmup: `1000`

## Clean
```
cmake --build build --target clean
```
