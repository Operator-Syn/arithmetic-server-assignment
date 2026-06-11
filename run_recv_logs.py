#!/usr/bin/env python3
"""Generate L1, L2, and L3 recv() logs.

Run from the project root:

    python3 run_recv_logs.py --port 14344

This creates:

    logs/l1_telnet_recv.log
    logs/l2_pipelined_recv.log
    logs/l3_drip_recv.log

The script starts the server separately for each scenario, runs the client,
then stops the server.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 14344
LOG_DIR = Path("logs")


def start_server(host: str, port: int, log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if log_path.exists():
        log_path.unlink()

    command = [
        sys.executable,
        "arithmetic_server.py",
        "--host",
        host,
        "--port",
        str(port),
        "--recv-log",
        str(log_path),
    ]

    print("$ " + " ".join(command))

    server = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Give the server time to bind before starting the client.
    time.sleep(1.0)

    if server.poll() is not None:
        output = server.stdout.read() if server.stdout is not None else ""
        raise RuntimeError(f"server failed to start:\n{output}")

    return server


def stop_server(server: subprocess.Popen) -> None:
    server.terminate()

    try:
        server.wait(timeout=3)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()


def run_client(
    command: list[str],
    input_text: Optional[str] = None,
    allowed_return_codes: tuple[int, ...] = (0,),
) -> None:
    print("$ " + " ".join(command))

    result = subprocess.run(
        command,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )

    print(result.stdout, end="")

    if result.returncode not in allowed_return_codes:
        raise RuntimeError(f"client command failed with exit code {result.returncode}")


def run_l1_telnet(host: str, port: int) -> None:
    if shutil.which("telnet") is None:
        raise RuntimeError("telnet is not installed or not in PATH")

    log_path = LOG_DIR / "l1_telnet_recv.log"
    server = start_server(host, port, log_path)

    try:
        run_client(
            ["telnet", host, str(port)],
            input_text="ADD 1 2\r\nQUIT\r\n",
            allowed_return_codes=(0, 1),
        )
    finally:
        stop_server(server)

    print(f"Saved L1 telnet recv log to {log_path}")


def run_l2_pipelined(host: str, port: int) -> None:
    log_path = LOG_DIR / "l2_pipelined_recv.log"
    server = start_server(host, port, log_path)

    try:
        run_client(
            [
                sys.executable,
                "bench_client.py",
                "m2",
                "--host",
                host,
                "--port",
                str(port),
                "--runs",
                "1",
            ]
        )
    finally:
        stop_server(server)

    print(f"Saved L2 pipelined recv log to {log_path}")


def run_l3_drip(host: str, port: int) -> None:
    log_path = LOG_DIR / "l3_drip_recv.log"
    server = start_server(host, port, log_path)

    try:
        run_client(
            [
                sys.executable,
                "drip_client.py",
                "--host",
                host,
                "--port",
                str(port),
                "--delay",
                "0.3",
            ]
        )
    finally:
        stop_server(server)

    print(f"Saved L3 drip recv log to {log_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--only",
        choices=("l1", "l2", "l3", "all"),
        default="all",
        help="which recv log scenario to run",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        if args.only in ("l1", "all"):
            run_l1_telnet(args.host, args.port)

        if args.only in ("l2", "all"):
            run_l2_pipelined(args.host, args.port)

        if args.only in ("l3", "all"):
            run_l3_drip(args.host, args.port)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
