#!/usr/bin/env python3
"""Run all Part 3 measurement benchmarks.

Run the server first in another terminal:

    python3 arithmetic_server.py --port 14344 --recv-log logs/recv.log

Then run this script from the project root:

    python3 run_measurements.py --port 14344

By default, this replaces report/measurements.md so repeated test runs do not
mix old and new results. Use --append if old results should be kept.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 14344
DEFAULT_OUTPUT = Path("report/measurements.md")


def write_line(output_path: Path, text: str) -> None:
    with output_path.open("a", encoding="utf-8") as file:
        file.write(text + "\n")


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


def run_all_measurements(host: str, port: int, output_path: Path, append: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not append:
        output_path.write_text("", encoding="utf-8")

    write_line(output_path, "# Arithmetic Server Measurements")
    write_line(output_path, "")
    write_line(output_path, f"Date: {datetime.now().isoformat(timespec='seconds')}")
    write_line(output_path, f"Host: {host}")
    write_line(output_path, f"Port: {port}")

    python = sys.executable

    write_line(output_path, "")
    write_line(output_path, "## M1 Sequential RTT")
    run_command(
        output_path,
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

    write_line(output_path, "")
    write_line(output_path, "## M2 Pipelined Throughput")
    run_command(
        output_path,
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

    write_line(output_path, "")
    write_line(output_path, "## M3 Concurrent Clients")
    for clients in (5, 10, 20):
        run_command(
            output_path,
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

    print(f"\nSaved measurements to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--append", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        run_all_measurements(args.host, args.port, args.output, args.append)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()