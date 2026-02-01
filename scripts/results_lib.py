#!/usr/bin/env python3

from __future__ import annotations

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, List

from raw_format import read_llr, read_raw_csv_list


def _load_csv_rows(path: Path) -> List[dict]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_index(path: str | Path = "results/index.csv") -> Any:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"index not found: {path}")
    try:
        import pandas as pd  # type: ignore

        return pd.read_csv(path)
    except Exception:
        return _load_csv_rows(path)


def load_summary(path: str | Path) -> Any:
    path = Path(path)
    try:
        import pandas as pd  # type: ignore

        return pd.read_csv(path)
    except Exception:
        rows = _load_csv_rows(path)
        return rows[0] if rows else {}


def parse_tags(value: str) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return [value]


def filter_runs(
    df,
    case: str | None = None,
    tag: str | None = None,
    pin_cpu: int | None = None,
    noise_mode: str | None = None,
    noise_cpu: int | None = None,
):
    try:
        import pandas as pd  # type: ignore

        if isinstance(df, pd.DataFrame):
            out = df
            if case is not None:
                out = out[out["case"] == case]
            if tag is not None:
                out = out[out["tags"].str.contains(tag)]
            if pin_cpu is not None:
                out = out[out["pin_cpu"] == pin_cpu]
            if noise_mode is not None and "noise_mode" in out.columns:
                out = out[out["noise_mode"] == noise_mode]
            if noise_cpu is not None and "noise_cpu" in out.columns:
                out = out[out["noise_cpu"] == noise_cpu]
            return out
    except Exception:
        pass

    rows = df if isinstance(df, list) else []
    filtered = []
    for row in rows:
        if case is not None and row.get("case") != case:
            continue
        if tag is not None and tag not in parse_tags(row.get("tags", "")):
            continue
        if pin_cpu is not None and str(pin_cpu) != str(row.get("pin_cpu", "")):
            continue
        if noise_mode is not None and str(noise_mode) != str(row.get("noise_mode", "")):
            continue
        if noise_cpu is not None and str(noise_cpu) != str(row.get("noise_cpu", "")):
            continue
        filtered.append(row)
    return filtered


def load_samples(run_dir: str | Path, unit: str = "ns") -> List[int]:
    run_dir = Path(run_dir)
    raw_llr = run_dir / "raw.llr.xz"
    if raw_llr.exists():
        _header, samples = read_llr(raw_llr, unit=unit)
        return samples
    raw_csv = run_dir / "raw.csv"
    if raw_csv.exists():
        return read_raw_csv_list(raw_csv)
    raise FileNotFoundError(f"no raw data in {run_dir}")


def iter_run_dirs(index_rows: Iterable[dict]) -> Iterable[Path]:
    for row in index_rows:
        run_dir = row.get("run_dir")
        if run_dir:
            yield Path(run_dir)
