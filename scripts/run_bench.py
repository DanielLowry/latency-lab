#!/usr/bin/env python3

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


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
        "bench_args",
        nargs=argparse.REMAINDER,
        help="Additional args passed to bench (prefix with --).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bench_path = Path(args.bench)
    if not bench_path.exists():
        print(f"bench not found: {bench_path}", file=sys.stderr)
        return 1

    run_dir = pick_run_dir(Path(args.results), args.lab, args.case, args.tag)
    run_dir.mkdir(parents=True, exist_ok=False)

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

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    stdout_path = run_dir / "stdout.txt"
    stdout_path.write_text(result.stdout or "")

    print(run_dir)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
