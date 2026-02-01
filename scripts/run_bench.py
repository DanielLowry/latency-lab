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


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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
    parser.add_argument(
        "--noise",
        choices=["off", "free", "same", "other"],
        default="off",
        help="Run with background noise (default: off).",
    )
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
        "--update-mode",
        choices=["append", "skip", "replace"],
        default="append",
        help=(
            "How to update summary/index outputs: append (default), "
            "skip (no summary/index), or replace (drop older matching rows)."
        ),
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
        "noise_mode",
        "noise_cpu",
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


INDEX_FIELDS = [
    "lab",
    "case",
    "tags",
    "iters",
    "warmup",
    "pin_cpu",
    "noise_mode",
    "noise_cpu",
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

INDEX_KEY_FIELDS = [
    "lab",
    "case",
    "tags",
    "iters",
    "warmup",
    "pin_cpu",
    "noise_mode",
    "noise_cpu",
    "bench_args",
]


def _merge_index_fields(fields: list[str]) -> list[str]:
    merged = list(fields)
    for field in INDEX_FIELDS:
        if field not in merged:
            merged.append(field)
    return merged


def _ensure_index_fields(path: Path) -> list[str]:
    if not path.exists():
        return INDEX_FIELDS
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        existing = next(reader, None) or []
    if not existing:
        return INDEX_FIELDS
    missing = [field for field in INDEX_FIELDS if field not in existing]
    if not missing:
        return existing
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        existing = reader.fieldnames or []
    merged = _merge_index_fields(existing)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=merged, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return merged


def append_index_csv(path: Path, row: dict) -> None:
    fields = _ensure_index_fields(path)
    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def _read_index_rows(path: Path) -> tuple[list[str], list[dict]]:
    if not path.exists():
        return INDEX_FIELDS, []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or INDEX_FIELDS
    return fields, rows


def _index_key(row: dict) -> tuple[str, ...]:
    return tuple(str(row.get(field, "")) for field in INDEX_KEY_FIELDS)


def update_index_csv(path: Path, row: dict, mode: str) -> None:
    if mode == "skip":
        return
    if mode == "append":
        append_index_csv(path, row)
        return
    fields, rows = _read_index_rows(path)
    fields = _merge_index_fields(fields)
    target = _index_key(row)
    filtered = [existing for existing in rows if _index_key(existing) != target]
    filtered.append(row)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filtered)


def main() -> int:
    args = parse_args()
    root = repo_root()
    bench_path = resolve_path(Path(args.bench))
    if not bench_path.exists():
        print(f"bench not found: {bench_path}", file=sys.stderr)
        return 1

    start_time = dt.datetime.now().isoformat(timespec="seconds")
    results_base = resolve_path(Path(args.results))
    run_dir = pick_run_dir(results_base, args.lab, args.case, args.tag)
    run_dir.mkdir(parents=True, exist_ok=False)

    extra_args: list[str] = []
    bench_cmd = relative_to_root(bench_path, root)
    run_dir_cmd = relative_to_root(run_dir, root)
    cmd = [
        bench_cmd,
        "--case",
        args.case,
        "--iters",
        str(args.iters),
        "--warmup",
        str(args.warmup),
        "--out",
        run_dir_cmd,
    ]
    if args.pin is not None:
        cmd += ["--pin", str(args.pin)]
    if args.noise != "off":
        cmd += ["--noise", args.noise]
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
        cwd=str(root),
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

        meta_path = run_dir / "meta.json"
        noise_mode = args.noise
        noise_cpu = -1
        try:
            meta = json.loads(meta_path.read_text())
            noise_mode = str(meta.get("noise_mode", noise_mode))
            noise_cpu = int(meta.get("noise_cpu", noise_cpu))
        except Exception:
            pass

        tags_json = json.dumps(args.tag, separators=(",", ":"))
        if args.update_mode != "skip":
            summary_path = run_dir / "summary.csv"
            summary_row = {
                "case": args.case,
                "tags": tags_json,
                "iters": args.iters,
                "warmup": args.warmup,
                "pin_cpu": args.pin if args.pin is not None else -1,
                "noise_mode": noise_mode,
                "noise_cpu": noise_cpu,
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
            rel = lambda path: relative_to_root(path, root)
            index_row = {
                "lab": args.lab,
                "case": args.case,
                "tags": tags_json,
                "iters": args.iters,
                "warmup": args.warmup,
                "pin_cpu": args.pin if args.pin is not None else -1,
                "noise_mode": noise_mode,
                "noise_cpu": noise_cpu,
                "unit": "ns",
                "min": stats["min"],
                "p50": stats["p50"],
                "p95": stats["p95"],
                "p99": stats["p99"],
                "p999": stats["p999"],
                "max": stats["max"],
                "mean": f"{stats['mean']:.6f}",
                "run_dir": rel(run_dir),
                "summary_path": rel(summary_path),
                "meta_path": rel(run_dir / "meta.json"),
                "stdout_path": rel(stdout_path),
                "raw_csv_path": rel(raw_csv_path),
                "raw_llr_path": rel(run_dir / "raw.llr.xz")
                if args.raw_format != "none"
                else "",
                "raw_unit": raw_unit,
                "bench_path": rel(bench_path),
                "bench_args": json.dumps(extra_args, separators=(",", ":")),
                "started_at": start_time,
            }
            update_index_csv(index_path, index_row, args.update_mode)

        if args.raw_drop_csv and args.raw_format != "none":
            raw_csv_path.unlink()

    print(run_dir)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
