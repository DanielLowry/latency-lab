#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from raw_format import RawHeader, encode_samples_to_llr, read_raw_csv_list


def sanitize_tag(tag: str) -> str:
    if not tag:
        return "tag"
    clean = []
    for ch in tag.strip():
        if ch.isalnum() or ch in ("-", "_"):
            clean.append(ch)
        else:
            clean.append("-")
    out = "".join(clean).strip("-")
    return out or "tag"


def pick_run_dir(base: Path, lab: str, case: str, tags) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    if tags:
        tag_part = "_".join(sanitize_tag(tag) for tag in tags)
    else:
        tag_part = "run"
    stem = f"{timestamp}_{tag_part}"
    run_dir = base / lab / case / stem
    counter = 1
    while run_dir.exists():
        run_dir = base / lab / case / f"{stem}_{counter}"
        counter += 1
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bench with a timestamped results layout."
    )
    parser.add_argument("--bench", default="./build/bench", help="Path to bench")
    parser.add_argument("--lab", required=True, help="Lab name for results layout")
    parser.add_argument("--case", required=True, help="Case name to run")
    parser.add_argument("--results", default="results", help="Base results directory")
    parser.add_argument("--iters", type=int, default=10000, help="Iterations")
    parser.add_argument("--warmup", type=int, default=1000, help="Warmup iterations")
    parser.add_argument("--pin", type=int, help="CPU index to pin")
    parser.add_argument("--tag", action="append", default=[], help="Tag label")
    parser.add_argument(
        "--raw-format",
        choices=["llr-xz", "none"],
        default="llr-xz",
        help="Store compressed raw samples (default: llr-xz).",
    )
    parser.add_argument(
        "--raw-unit",
        choices=["auto", "ns", "us", "ms", "s"],
        default="auto",
        help="Unit for compressed raw samples (default: auto).",
    )
    parser.add_argument(
        "--raw-drop-csv",
        action="store_true",
        help="Delete raw.csv after compression.",
    )
    parser.add_argument(
        "bench_args",
        nargs=argparse.REMAINDER,
        help="Additional args passed to bench (prefix with --).",
    )
    return parser.parse_args()


def compute_quantiles(samples: list[int]) -> dict:
    if not samples:
        return {
            "min": 0,
            "p50": 0,
            "p95": 0,
            "p99": 0,
            "p999": 0,
            "max": 0,
            "mean": 0.0,
        }
    total = sum(samples)
    mean = total / len(samples)
    samples.sort()
    last = len(samples) - 1

    def pick(p: float) -> int:
        return samples[int(p * last)]

    return {
        "min": samples[0],
        "p50": pick(0.50),
        "p95": pick(0.95),
        "p99": pick(0.99),
        "p999": pick(0.999),
        "max": samples[-1],
        "mean": mean,
    }


def write_summary_csv(path: Path, row: dict) -> None:
    fields = [
        "case",
        "tags",
        "iters",
        "warmup",
        "pin_cpu",
        "unit",
        "min",
        "p50",
        "p95",
        "p99",
        "p999",
        "max",
        "mean",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)


def append_index_csv(path: Path, row: dict) -> None:
    default_fields = [
        "lab",
        "case",
        "tags",
        "iters",
        "warmup",
        "pin_cpu",
        "unit",
        "min",
        "p50",
        "p95",
        "p99",
        "p999",
        "max",
        "mean",
        "run_dir",
        "summary_path",
        "meta_path",
        "stdout_path",
        "raw_csv_path",
        "raw_llr_path",
        "raw_unit",
        "bench_path",
        "bench_args",
        "started_at",
    ]
    file_exists = path.exists()
    fields = default_fields
    needs_header = not file_exists
    if file_exists:
        with path.open(newline="") as handle:
            reader = csv.reader(handle)
            existing = next(reader, None)
            if existing:
                fields = existing
            else:
                needs_header = True
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def main() -> int:
    args = parse_args()
    bench_path = Path(args.bench)
    if not bench_path.exists():
        print(f"bench not found: {bench_path}", file=sys.stderr)
        return 1

    start_time = dt.datetime.now().isoformat(timespec="seconds")
    results_base = Path(args.results)
    run_dir = pick_run_dir(results_base, args.lab, args.case, args.tag)
    run_dir.mkdir(parents=True, exist_ok=False)

    extra_args: list[str] = []
    cmd = [
        str(bench_path),
        "--case",
        args.case,
        "--iters",
        str(args.iters),
        "--warmup",
        str(args.warmup),
        "--out",
        str(run_dir),
    ]
    if args.pin is not None:
        cmd += ["--pin", str(args.pin)]
    for tag in args.tag:
        cmd += ["--tag", tag]
    if args.bench_args:
        extra = args.bench_args
        if extra and extra[0] == "--":
            extra = extra[1:]
        cmd += extra
        extra_args = extra

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    stdout_path = run_dir / "stdout.txt"
    stdout_path.write_text(result.stdout or "")

    if result.returncode == 0:
        raw_csv_path = run_dir / "raw.csv"
        if not raw_csv_path.exists():
            print(f"raw.csv not found: {raw_csv_path}", file=sys.stderr)
            return 1
        raw_unit = ""
        samples = read_raw_csv_list(raw_csv_path)
        if args.raw_format != "none":
            raw_out_path = run_dir / "raw.llr.xz"
            header = RawHeader(
                case_name=args.case,
                tags=args.tag,
                args=extra_args,
                iters=args.iters,
                warmup=args.warmup,
                pin_cpu=args.pin if args.pin is not None else -1,
                unit="ns",
                sample_count=0,
            )
            try:
                encoded_header = encode_samples_to_llr(
                    samples,
                    raw_out_path,
                    header,
                    unit=args.raw_unit,
                )
                raw_unit = encoded_header.unit
            except Exception as exc:
                print(f"failed to encode raw data: {exc}", file=sys.stderr)
                return 1

        stats = compute_quantiles(samples)

        summary_path = run_dir / "summary.csv"
        tags_json = json.dumps(args.tag, separators=(",", ":"))
        summary_row = {
            "case": args.case,
            "tags": tags_json,
            "iters": args.iters,
            "warmup": args.warmup,
            "pin_cpu": args.pin if args.pin is not None else -1,
            "unit": "ns",
            "min": stats["min"],
            "p50": stats["p50"],
            "p95": stats["p95"],
            "p99": stats["p99"],
            "p999": stats["p999"],
            "max": stats["max"],
            "mean": f"{stats['mean']:.6f}",
        }
        write_summary_csv(summary_path, summary_row)

        index_path = results_base / "index.csv"
        index_row = {
            "lab": args.lab,
            "case": args.case,
            "tags": tags_json,
            "iters": args.iters,
            "warmup": args.warmup,
            "pin_cpu": args.pin if args.pin is not None else -1,
            "unit": "ns",
            "min": stats["min"],
            "p50": stats["p50"],
            "p95": stats["p95"],
            "p99": stats["p99"],
            "p999": stats["p999"],
            "max": stats["max"],
            "mean": f"{stats['mean']:.6f}",
            "run_dir": str(run_dir),
            "summary_path": str(summary_path),
            "meta_path": str(run_dir / "meta.json"),
            "stdout_path": str(stdout_path),
            "raw_csv_path": str(raw_csv_path),
            "raw_llr_path": str(run_dir / "raw.llr.xz")
            if args.raw_format != "none"
            else "",
            "raw_unit": raw_unit,
            "bench_path": str(bench_path),
            "bench_args": json.dumps(extra_args, separators=(",", ":")),
            "started_at": start_time,
        }
        append_index_csv(index_path, index_row)

        if args.raw_drop_csv and args.raw_format != "none":
            raw_csv_path.unlink()

    print(run_dir)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
