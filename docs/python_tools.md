# Python Tools

This repo includes small Python helpers for running benchmarks, compressing raw
samples, and analyzing results in a notebook.

## Setup (uv)
```
uv venv
uv pip install -r reqs.txt
```
`uv venv` creates `.venv` in the repo root; `uv run` will use it automatically.

## Run a benchmark and capture results
```
python3 scripts/run_bench.py --lab os --case noop --tag quiet
```

Outputs are stored under:
```
results/<lab>/<case>/<timestamp>_<tag>/
  raw.csv
  raw.llr.xz
  meta.json
  stdout.txt
  summary.csv
```

The top-level index is appended at:
```
results/index.csv
```

## Raw sample compression
`raw.llr.xz` is a compact binary format (LLR1) compressed with LZMA. It stores:
- case name, tags, args
- iters, warmup, pin_cpu
- unit (ns/us/ms/s)
- delta-encoded integer samples

Unit selection defaults to `--raw-unit auto`, based on the smallest sample:
- `>= 100_000 ns` -> `us`
- `>= 100_000_000 ns` -> `ms`
- `>= 100_000_000_000 ns` -> `s`

To preserve exact nanosecond values, force `--raw-unit ns`.
To keep only the compressed file, pass `--raw-drop-csv`.

## Notebook analysis
Start the notebook server with uv (no manual activation required):
```
uv run -- jupyter lab notebooks/analysis.ipynb
```

If you already activated the venv, you can run:
```
jupyter lab notebooks/analysis.ipynb
```

The notebook reads `results/index.csv` and uses `scripts/results_lib.py` for
loading raw samples.

## Notebook runner (ipywidgets)
If you want to launch benchmarks from inside the notebook, use ipywidgets and
the helper in `scripts/notebook_runner.py`.

The notebook includes a simple runner UI with filterable checkboxes, select-all
controls, and a "Run selected" button that executes cases sequentially.
An update mode control lets you append new rows (default), skip summary/index
updates, or replace matching rows in `results/index.csv`.
See `notebooks/analysis.ipynb` for the actual widget cell.

## Tests
Run Python tests with uv:
```
uv venv
uv pip install -r reqs.txt
uv run -m pytest tests/python
```

If you already activated the venv, you can also run:
```
python3 -m pytest tests/python
```
