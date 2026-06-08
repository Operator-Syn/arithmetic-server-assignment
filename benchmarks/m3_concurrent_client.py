#!/usr/bin/env python3
"""M3: concurrent-client benchmark.

Each client thread opens its own TCP connection and runs the sequential
ADD 1 2 benchmark.

Run the server first:

    python3 arithmetic_server.py --port 14344 --recv-log logs/recv.log

Then run this client from the project root:

    python3 -m benchmarks.m3_concurrent_client --port 14344 --clients 5 --runs 1
    python3 -m benchmarks.m3_concurrent_client --port 14344 --clients 10 --runs 1
    python3 -m benchmarks.m3_concurrent_client --port 14344 --clients 20 --runs 1

Or run it through the main benchmark file:

    python3 bench_client.py m3 --port 14344 --clients 5 --runs 1
    python3 bench_client.py m3 --port 14344 --clients 10 --runs 1
    python3 bench_client.py m3 --port 14344 --clients 20 --runs 1

To save the output for the report:

    python3 bench_client.py m3 --port 14344 --clients 5 --runs 1 | tee -a report/measurements.md
    python3 bench_client.py m3 --port 14344 --clients 10 --runs 1 | tee -a report/measurements.md
    python3 bench_client.py m3 --port 14344 --clients 20 --runs 1 | tee -a report/measurements.md
"""

from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time

from benchmarks.common import (
    DEFAULT_COUNT,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
)
from benchmarks.m1_rtt_client import run_once as run_sequential_once


def run(
    host: str,
    port: int,
    count: int,
    clients: int,
    runs: int,
    timeout: float,
) -> None:
    print(f"mode=concurrent clients={clients} count_per_client={count} runs={runs}")

    for run_number in range(1, runs + 1):
        start_event = threading.Event()
        results: list[list[float] | None] = [None] * clients
        errors: list[BaseException] = []
        error_lock = threading.Lock()

        def worker(index: int) -> None:
            try:
                start_event.wait()
                results[index] = run_sequential_once(host, port, count, timeout)
            except BaseException as exc:
                with error_lock:
                    errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(index,))
            for index in range(clients)
        ]

        for thread in threads:
            thread.start()

        start = time.perf_counter()
        start_event.set()

        for thread in threads:
            thread.join()

        elapsed_seconds = time.perf_counter() - start

        if errors:
            raise RuntimeError(f"{len(errors)} client thread(s) failed: {errors[0]!r}")

        all_rtts = [
            rtt
            for client_result in results
            if client_result is not None
            for rtt in client_result
        ]

        total_operations = clients * count

        print(
            f"run={run_number} "
            f"total_operations={total_operations} "
            f"elapsed_seconds={elapsed_seconds:.6f} "
            f"mean_rtt_ms={statistics.mean(all_rtts):.3f} "
            f"median_rtt_ms={statistics.median(all_rtts):.3f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--clients", type=int, default=5)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        run(
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