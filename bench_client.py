#!/usr/bin/env python3
"""Benchmark dispatcher for arithmetic_server.py.

Examples:

    python3 bench_client.py m1 --runs 3
    python3 bench_client.py m2 --runs 3
    python3 bench_client.py m3 --clients 5
    python3 bench_client.py m3 --clients 10
    python3 bench_client.py m3 --clients 20
"""

from __future__ import annotations

import argparse
import sys

from benchmarks.common import (
    DEFAULT_COUNT,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
)
from benchmarks.m1_rtt_client import run as run_m1
from benchmarks.m2_pipelined_client import run as run_m2
from benchmarks.m3_concurrent_client import run as run_m3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "benchmark",
        choices=("m1", "m2", "m3"),
        help="benchmark to run",
    )

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--clients", type=int, default=5)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        match args.benchmark:
            case "m1":
                run_m1(args.host, args.port, args.count, args.runs, args.timeout)

            case "m2":
                run_m2(args.host, args.port, args.count, args.runs, args.timeout)

            case "m3":
                run_m3(
                    args.host,
                    args.port,
                    args.count,
                    args.clients,
                    args.runs,
                    args.timeout,
                )

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()