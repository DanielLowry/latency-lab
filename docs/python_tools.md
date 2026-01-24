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

Example cell (from `notebooks/analysis.ipynb`):
```python
from pathlib import Path
import sys

import ipywidgets as widgets
from IPython.display import display, clear_output

repo_root = Path("..").resolve()
sys.path.append(str(repo_root / "scripts"))
import notebook_runner as nb

bench_path = repo_root / "build" / "bench"
results_dir = repo_root / "results"

case = widgets.Dropdown(options=nb.list_cases(bench_path), description="Case")
lab = widgets.Text(value="os", description="Lab")
iters = widgets.IntText(value=10000, description="Iters")
warmup = widgets.IntText(value=1000, description="Warmup")
pin_cpu = widgets.IntText(value=-1, description="Pin CPU")
tags = widgets.Text(value="quiet", description="Tags (csv)")
run_button = widgets.Button(description="Run")
output = widgets.Output()

def run_clicked(_):
    with output:
        clear_output()
        tag_list = [t.strip() for t in tags.value.split(",") if t.strip()]
        pin = None if pin_cpu.value < 0 else pin_cpu.value
        try:
            result = nb.run_case(
                bench_path=bench_path,
                lab=lab.value,
                case=case.value,
                results_dir=results_dir,
                iters=iters.value,
                warmup=warmup.value,
                pin_cpu=pin,
                tags=tag_list,
            )
        except Exception as exc:
            print(f"Run failed: {exc}")
            return
        print(f"Run dir: {result.run_dir}")
        print(result.read_stdout())

run_button.on_click(run_clicked)
display(widgets.VBox([case, lab, iters, warmup, pin_cpu, tags, run_button]), output)
```

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
