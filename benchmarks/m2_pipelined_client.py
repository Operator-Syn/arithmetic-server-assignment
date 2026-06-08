#!/usr/bin/env python3
"""M2: pipelined throughput benchmark client.

This client sends all ADD 1 2 commands first, then reads all responses.

Run the server first:

    python3 arithmetic_server.py --port 14344 --recv-log logs/l2_pipelined_recv.log

Then run this client from the project root:

    python3 -m benchmarks.m2_pipelined_client --port 14344 --runs 3

Or run it through the main benchmark file:

    python3 bench_client.py m2 --port 14344 --runs 3

To save the output for the report:

    python3 bench_client.py m2 --port 14344 --runs 3 | tee -a report/measurements.md
"""

from __future__ import annotations

import argparse
import sys
import time

from benchmarks.common import (
    COMMAND,
    DEFAULT_COUNT,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    close_session,
    connect,
    read_expected_add_response,
)


def run_once(host: str, port: int, count: int, timeout: float) -> tuple[float, float]:
    payload = COMMAND * count
    sock, reader = connect(host, port, timeout)

    with sock:
        start = time.perf_counter()

        # Send every command first, without waiting for each response.
        sock.sendall(payload)

        # After sending all commands, read the same number of responses.
        for _ in range(count):
            read_expected_add_response(reader)

        elapsed_seconds = time.perf_counter() - start
        close_session(sock, reader)

    operations_per_second = count / elapsed_seconds

    return elapsed_seconds, operations_per_second


def run(host: str, port: int, count: int, runs: int, timeout: float) -> None:
    print(f"mode=pipelined count={count} runs={runs}")

    for run_number in range(1, runs + 1):
        elapsed_seconds, operations_per_second = run_once(
            host,
            port,
            count,
            timeout,
        )

        print(
            f"run={run_number} "
            f"elapsed_seconds={elapsed_seconds:.6f} "
            f"operations_per_second={operations_per_second:.2f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        run(args.host, args.port, args.count, args.runs, args.timeout)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()