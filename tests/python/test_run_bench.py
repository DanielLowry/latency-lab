from __future__ import annotations

import csv
from pathlib import Path

from run_bench import append_index_csv, compute_quantiles, write_summary_csv


def test_compute_quantiles_basic() -> None:
    samples = [5, 1, 4, 2, 3]
    stats = compute_quantiles(samples)
    assert stats["min"] == 1
    assert stats["p50"] == 3
    assert stats["p95"] == 4
    assert stats["p99"] == 4
    assert stats["p999"] == 4
    assert stats["max"] == 5
    assert stats["mean"] == 3.0


def test_write_summary_csv(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.csv"
    row = {
        "case": "noop",
        "tags": "[]",
        "iters": 10,
        "warmup": 0,
        "pin_cpu": -1,
        "unit": "ns",
        "min": 1,
        "p50": 2,
        "p95": 3,
        "p99": 4,
        "p999": 5,
        "max": 6,
        "mean": "3.50",
    }
    write_summary_csv(summary_path, row)
    with summary_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["case"] == "noop"
    assert rows[0]["unit"] == "ns"


def test_append_index_csv(tmp_path: Path) -> None:
    index_path = tmp_path / "index.csv"
    row = {
        "lab": "os",
        "case": "noop",
        "tags": "[]",
        "iters": 1,
        "warmup": 0,
        "pin_cpu": -1,
        "unit": "ns",
        "min": 1,
        "p50": 1,
        "p95": 1,
        "p99": 1,
        "p999": 1,
        "max": 1,
        "mean": "1.0",
        "run_dir": "/tmp/run",
        "summary_path": "/tmp/summary.csv",
        "meta_path": "/tmp/meta.json",
        "stdout_path": "/tmp/stdout.txt",
        "raw_csv_path": "/tmp/raw.csv",
        "raw_llr_path": "/tmp/raw.llr.xz",
        "raw_unit": "ns",
        "bench_path": "/tmp/bench",
        "bench_args": "[]",
        "started_at": "2024-01-01T00:00:00",
    }
    append_index_csv(index_path, row)
    append_index_csv(index_path, row)
    with index_path.open(newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    assert len(rows) == 3
