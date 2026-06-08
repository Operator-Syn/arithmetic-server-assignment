#!/usr/bin/env python3
"""M1: sequential benchmark client.

This client sends ADD 1 2 sequentially. It waits for each response before
sending the next command.
"""

from __future__ import annotations

import argparse
import statistics
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


def run_once(host: str, port: int, count: int, timeout: float) -> list[float]:
    rtts_ms: list[float] = []
    sock, reader = connect(host, port, timeout)

    with sock:
        for _ in range(count):
            start = time.perf_counter()

            sock.sendall(COMMAND)
            read_expected_add_response(reader)

            elapsed_ms = (time.perf_counter() - start) * 1000
            rtts_ms.append(elapsed_ms)

        close_session(sock, reader)

    return rtts_ms


def run(host: str, port: int, count: int, runs: int, timeout: float) -> None:
    print(f"mode=sequential count={count} runs={runs}")

    for run_number in range(1, runs + 1):
        rtts_ms = run_once(host, port, count, timeout)

        print(
            f"run={run_number} "
            f"mean_rtt_ms={statistics.mean(rtts_ms):.3f} "
            f"median_rtt_ms={statistics.median(rtts_ms):.3f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

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