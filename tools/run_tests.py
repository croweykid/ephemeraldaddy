#!/usr/bin/env python3
"""Run the complete pytest suite and retain readable test reports."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIRECTORY = REPOSITORY_ROOT / "results" / "test-runs"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run every test with pytest, show output live, and save a detailed "
            "text log plus a JUnit XML report."
        )
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="check that every test can be discovered without running it",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIRECTORY,
        help=f"report directory (default: {DEFAULT_LOG_DIRECTORY})",
    )
    parser.add_argument(
        "--target",
        action="append",
        help="test file or directory to run (repeatable; default: tests)",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="extra pytest arguments after '--', such as: -- -k chart_uids -x",
    )
    return parser.parse_args()


def _write_line(log_file, message: str = "") -> None:
    print(message, flush=True)
    log_file.write(f"{message}\n")
    log_file.flush()


def main() -> int:
    args = _arguments()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_directory = args.log_dir.expanduser().resolve()
    log_directory.mkdir(parents=True, exist_ok=True)
    text_report = log_directory / f"pytest-{timestamp}.log"
    junit_report = log_directory / f"pytest-{timestamp}.xml"

    extra_args = list(args.pytest_args)
    if extra_args[:1] == ["--"]:
        extra_args.pop(0)

    targets = args.target or ["tests"]
    command = [
        sys.executable,
        "-m",
        "pytest",
        *targets,
        "-ra",
        f"--junitxml={junit_report}",
    ]
    if args.collect_only:
        command.append("--collect-only")
    command.extend(extra_args)

    with text_report.open("w", encoding="utf-8", errors="replace") as log_file:
        _write_line(log_file, "EphemeralDaddy test run")
        _write_line(log_file, f"Started (UTC): {timestamp}")
        _write_line(log_file, f"Repository: {REPOSITORY_ROOT}")
        _write_line(log_file, f"Python: {sys.version.replace(os.linesep, ' ')}")
        _write_line(log_file, f"Platform: {platform.platform()}")
        _write_line(log_file, f"Command: {subprocess.list2cmdline(command)}")
        _write_line(log_file, "-" * 72)

        try:
            process = subprocess.Popen(
                command,
                cwd=REPOSITORY_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as error:
            _write_line(log_file, f"Could not start pytest: {error}")
            return 2

        assert process.stdout is not None
        for line in process.stdout:
            _write_line(log_file, line.rstrip("\n"))
        return_code = process.wait()

        _write_line(log_file, "-" * 72)
        _write_line(log_file, f"Exit code: {return_code}")
        _write_line(log_file, f"Text report: {text_report}")
        _write_line(log_file, f"JUnit report: {junit_report}")

    print(f"\nSaved detailed log to: {text_report}")
    print(f"Saved JUnit report to: {junit_report}")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
