from __future__ import annotations

from pathlib import Path

import raw_format as rf


def test_choose_unit_from_min_thresholds() -> None:
    assert rf.choose_unit_from_min(0) == "ns"
    assert rf.choose_unit_from_min(99_999) == "ns"
    assert rf.choose_unit_from_min(100_000) == "us"
    assert rf.choose_unit_from_min(100_000_000) == "ms"
    assert rf.choose_unit_from_min(100_000_000_000) == "s"


def test_llr_roundtrip_ns_exact(tmp_path: Path) -> None:
    samples = [1, 2, 3, 1000, 1001]
    header = rf.RawHeader(
        case_name="noop",
        tags=["quiet"],
        args=["--flag", "value"],
        iters=len(samples),
        warmup=0,
        pin_cpu=-1,
        unit="ns",
        sample_count=0,
    )
    out_path = tmp_path / "raw.llr.xz"
    rf.encode_samples_to_llr(samples, out_path, header, unit="ns")
    read_header, decoded = rf.read_llr(out_path, unit="ns")
    assert decoded == samples
    assert read_header.case_name == "noop"
    assert read_header.tags == ["quiet"]
    assert read_header.args == ["--flag", "value"]
    assert read_header.iters == len(samples)
    assert read_header.warmup == 0
    assert read_header.pin_cpu == -1
    assert read_header.unit == "ns"


def test_llr_roundtrip_auto_with_rounding(tmp_path: Path) -> None:
    samples = [100_000, 150_000, 250_000, 249_999]
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
    out_path = tmp_path / "raw.llr.xz"
    rf.encode_samples_to_llr(samples, out_path, header, unit="auto")
    read_header, decoded = rf.read_llr(out_path, unit="ns")
    assert read_header.unit == "us"
    assert decoded == [100_000, 150_000, 250_000, 250_000]


def test_read_raw_csv_list(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    raw_path.write_text("iter,ns\n0,10\n1,20\n2,30\n")
    assert rf.read_raw_csv_list(raw_path) == [10, 20, 30]
