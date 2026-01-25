#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class RunResult:
    run_dir: Path
    returncode: int
    command: list[str]
    stdout_path: Path
    meta_path: Path
    raw_csv_path: Path
    summary_path: Path

    def read_stdout(self) -> str:
        try:
            return self.stdout_path.read_text()
        except FileNotFoundError:
            return ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_run_dir(output: str) -> Path:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("run_bench did not report a run directory")
    return Path(lines[-1])


def _resolve_from_root(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (_repo_root() / path).resolve()


def list_cases(bench_path: str | Path = "build/bench") -> list[str]:
    bench_path = _resolve_from_root(Path(bench_path))
    result = subprocess.run(
        [str(bench_path), "--list"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"bench --list failed: {message}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def run_case(
    *,
    bench_path: str | Path = "build/bench",
    lab: str,
    case: str,
    results_dir: str | Path = "results",
    iters: int = 10000,
    warmup: int = 1000,
    pin_cpu: int | None = None,
    tags: Iterable[str] | None = None,
    update_mode: str = "append",
    extra_args: Iterable[str] | None = None,
) -> RunResult:
    bench_path = _resolve_from_root(Path(bench_path))
    results_dir = _resolve_from_root(Path(results_dir))
    script_path = _repo_root() / "scripts" / "run_bench.py"

    cmd = [
        sys.executable,
        str(script_path),
        "--bench",
        str(bench_path),
        "--lab",
        lab,
        "--case",
        case,
        "--results",
        str(results_dir),
        "--iters",
        str(iters),
        "--warmup",
        str(warmup),
        "--update-mode",
        update_mode,
    ]
    if pin_cpu is not None:
        cmd += ["--pin", str(pin_cpu)]
    if tags:
        for tag in tags:
            cmd += ["--tag", tag]
    if extra_args:
        cmd += ["--", *extra_args]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(_repo_root()),
    )
    run_dir = _parse_run_dir(result.stdout)
    if result.returncode != 0:
        message = result.stderr.strip() or "bench run failed"
        raise RuntimeError(f"{message} (run_dir={run_dir})")

    return RunResult(
        run_dir=run_dir,
        returncode=result.returncode,
        command=cmd,
        stdout_path=run_dir / "stdout.txt",
        meta_path=run_dir / "meta.json",
        raw_csv_path=run_dir / "raw.csv",
        summary_path=run_dir / "summary.csv",
    )
