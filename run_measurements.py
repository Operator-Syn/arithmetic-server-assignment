#!/usr/bin/env python3
"""Run all Part 3 measurement benchmarks into separate files.

Run the server first in another terminal:

    python3 arithmetic_server.py --port 14344 --recv-log logs/recv.log

Then run this script from the project root:

    python3 run_measurements.py --port 14344

This creates:

    report/m1_measurements.md
    report/m2_measurements.md
    report/m3_measurements.md

By default, old files are replaced. Use --append to keep old results.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 14344
DEFAULT_OUTPUT_DIR = Path("report")


def write_line(output_path: Path, text: str) -> None:
    with output_path.open("a", encoding="utf-8") as file:
        file.write(text + "\n")


def prepare_file(output_path: Path, title: str, host: str, port: int, append: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not append:
        output_path.write_text("", encoding="utf-8")

    write_line(output_path, f"# {title}")
    write_line(output_path, "")
    write_line(output_path, f"Date: {datetime.now().isoformat(timespec='seconds')}")
    write_line(output_path, f"Host: {host}")
    write_line(output_path, f"Port: {port}")


def run_command(output_path: Path, command: list[str]) -> None:
    command_text = " ".join(command)

    print(f"\n$ {command_text}")
    write_line(output_path, "")
    write_line(output_path, f"$ {command_text}")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if process.stdout is not None:
        for line in process.stdout:
            print(line, end="")
            with output_path.open("a", encoding="utf-8") as file:
                file.write(line)

    return_code = process.wait()

    if return_code != 0:
        raise RuntimeError(f"command failed with exit code {return_code}: {command_text}")


def run_all_measurements(
    host: str,
    port: int,
    output_dir: Path,
    append: bool,
) -> None:
    python = sys.executable

    m1_output = output_dir / "m1_measurements.md"
    m2_output = output_dir / "m2_measurements.md"
    m3_output = output_dir / "m3_measurements.md"

    prepare_file(m1_output, "M1 Sequential RTT Measurements", host, port, append)
    run_command(
        m1_output,
        [
            python,
            "bench_client.py",
            "m1",
            "--host",
            host,
            "--port",
            str(port),
            "--runs",
            "3",
        ],
    )

    prepare_file(m2_output, "M2 Pipelined Throughput Measurements", host, port, append)
    run_command(
        m2_output,
        [
            python,
            "bench_client.py",
            "m2",
            "--host",
            host,
            "--port",
            str(port),
            "--runs",
            "3",
        ],
    )

    prepare_file(m3_output, "M3 Concurrent Client Measurements", host, port, append)

    for clients in (5, 10, 20):
        run_command(
            m3_output,
            [
                python,
                "bench_client.py",
                "m3",
                "--host",
                host,
                "--port",
                str(port),
                "--clients",
                str(clients),
                "--runs",
                "1",
            ],
        )

    print("")
    print(f"Saved M1 results to {m1_output}")
    print(f"Saved M2 results to {m2_output}")
    print(f"Saved M3 results to {m3_output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--append", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        run_all_measurements(
            args.host,
            args.port,
            args.output_dir,
            args.append,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()