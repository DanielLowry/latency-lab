from __future__ import annotations

from pathlib import Path

import raw_format as rf
from results_lib import filter_runs, load_samples, parse_tags


def test_parse_tags() -> None:
    assert parse_tags('["quiet","warm"]') == ["quiet", "warm"]
    assert parse_tags("") == []
    assert parse_tags("noise") == ["noise"]


def test_filter_runs_list() -> None:
    rows = [
        {"case": "noop", "tags": '["quiet"]', "pin_cpu": "2"},
        {"case": "fork_wait", "tags": '["noise"]', "pin_cpu": "-1"},
    ]
    filtered = filter_runs(rows, case="noop")
    assert len(filtered) == 1
    assert filtered[0]["case"] == "noop"
    filtered = filter_runs(rows, tag="noise")
    assert len(filtered) == 1
    assert filtered[0]["case"] == "fork_wait"


def test_load_samples_prefers_llr(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    samples = [1000, 2000, 3000]
    header = rf.RawHeader(
        case_name="noop",
        tags=[],
        args=[],
        iters=len(samples),
        warmup=0,
        pin_cpu=-1,
        unit="ns",
        sample_count=0,
    )
    rf.encode_samples_to_llr(samples, run_dir / "raw.llr.xz", header, unit="ns")
    loaded = load_samples(run_dir, unit="ns")
    assert loaded == samples

