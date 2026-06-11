#!/usr/bin/env python3
"""Generate dedicated recv() logs for robustness and protocol test clients.

Run from the project root:

    python3 run_robustness_logs.py --port 14344

This starts a fresh arithmetic_server.py process for each scenario, runs the
matching client, then stops the server. It creates separate server recv() logs
and client-output logs under logs/:

    logs/smoke_recv.log
    logs/smoke_client_output.log
    logs/smoke_server_output.log

    logs/malformed_recv.log
    logs/malformed_client_output.log
    logs/malformed_server_output.log

    logs/partial_recv.log
    logs/partial_client_output.log
    logs/partial_server_output.log

    logs/oversized_recv.log
    logs/oversized_client_output.log
    logs/oversized_server_output.log

It also writes:

    logs/robustness_summary.md

Use --only to run just one scenario.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 14344
LOG_DIR = Path("logs")


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    client_file: str
    extra_args: tuple[str, ...] = ()
    timeout: float = 30.0


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_line(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(text + "\n")


def remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def find_project_file(filename: str) -> Path:
    """Find a client file whether it is in root, test/, or tests/."""
    candidates = [
        Path(filename),
        Path("test") / filename,
        Path("tests") / filename,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"could not find {filename}; searched: {searched}")


def wait_for_server(host: str, port: int, server: subprocess.Popen, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    last_error: BaseException | None = None

    while time.time() < deadline:
        if server.poll() is not None:
            output = ""
            if server.stdout is not None:
                output = server.stdout.read()
            raise RuntimeError(f"server exited before accepting connections:\n{output}")

        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.1)

    raise RuntimeError(f"server did not accept connections within {timeout:.1f}s: {last_error}")


def start_server(host: str, port: int, recv_log_path: Path) -> subprocess.Popen:
    recv_log_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "arithmetic_server.py",
        "--host",
        host,
        "--port",
        str(port),
        "--recv-log",
        str(recv_log_path),
    ]

    print("$ " + " ".join(command))

    server = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    wait_for_server(host, port, server)
    return server


def stop_server(server: subprocess.Popen) -> str:
    if server.poll() is None:
        server.terminate()

    try:
        output, _ = server.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        server.kill()
        output, _ = server.communicate()

    return output or ""


def run_client(command: list[str], timeout: float) -> tuple[int, str]:
    print("$ " + " ".join(command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )

    print(result.stdout, end="")
    return result.returncode, result.stdout


def build_scenarios(partial_delay: float, oversized_bytes: int) -> dict[str, Scenario]:
    return {
        "smoke": Scenario(
            name="smoke",
            description="Basic command coverage: arithmetic, RND, HIST, HELP, MOD, and QUIT.",
            client_file="smoke_client.py",
            timeout=30.0,
        ),
        "malformed": Scenario(
            name="malformed",
            description="Malformed input: blank line, wrong argument counts, non-numeric args, unknown command, bad HELP, bad RND.",
            client_file="malformed_client.py",
            timeout=30.0,
        ),
        "partial": Scenario(
            name="partial",
            description="Partial command: sends 'ADD 1', waits, then sends ' 2\\n'.",
            client_file="partial_client.py",
            extra_args=("--delay", str(partial_delay)),
            timeout=max(30.0, partial_delay + 10.0),
        ),
        "oversized": Scenario(
            name="oversized",
            description="Oversized command: sends many bytes before newline, then checks resynchronization.",
            client_file="oversized_client.py",
            extra_args=("--bytes", str(oversized_bytes)),
            timeout=30.0,
        ),
    }


def run_scenario(
    scenario: Scenario,
    host: str,
    port: int,
    log_dir: Path,
    append: bool,
    summary_path: Path,
) -> None:
    recv_log_path = log_dir / f"{scenario.name}_recv.log"
    client_output_path = log_dir / f"{scenario.name}_client_output.log"
    server_output_path = log_dir / f"{scenario.name}_server_output.log"

    if not append:
        remove_if_exists(recv_log_path)
        remove_if_exists(client_output_path)
        remove_if_exists(server_output_path)

    client_path = find_project_file(scenario.client_file)
    server = start_server(host, port, recv_log_path)

    client_command = [
        sys.executable,
        str(client_path),
        "--host",
        host,
        "--port",
        str(port),
        *scenario.extra_args,
    ]

    client_return_code = 1
    client_output = ""

    try:
        client_return_code, client_output = run_client(client_command, scenario.timeout)
    finally:
        server_output = stop_server(server)

    write_text(client_output_path, client_output)
    write_text(server_output_path, server_output)

    if client_return_code != 0:
        raise RuntimeError(
            f"{scenario.name} client failed with exit code {client_return_code}; "
            f"see {client_output_path}"
        )

    append_line(summary_path, f"## {scenario.name}")
    append_line(summary_path, "")
    append_line(summary_path, scenario.description)
    append_line(summary_path, "")
    append_line(summary_path, f"Command: `{' '.join(client_command)}`")
    append_line(summary_path, f"recv log: `{recv_log_path}`")
    append_line(summary_path, f"client output: `{client_output_path}`")
    append_line(summary_path, f"server output: `{server_output_path}`")
    append_line(summary_path, "")

    print(f"Saved recv log to {recv_log_path}")
    print(f"Saved client output to {client_output_path}")
    print(f"Saved server output to {server_output_path}")


def run_all(
    selected: str,
    host: str,
    port: int,
    log_dir: Path,
    partial_delay: float,
    oversized_bytes: int,
    append: bool,
) -> None:
    scenarios = build_scenarios(partial_delay, oversized_bytes)
    scenario_order = ["smoke", "malformed", "partial", "oversized"]

    if selected != "all":
        scenario_order = [selected]

    log_dir.mkdir(parents=True, exist_ok=True)
    summary_path = log_dir / "robustness_summary.md"

    if not append:
        write_text(
            summary_path,
            "# Robustness Test Logs\n\n"
            f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n"
            f"Host: `{host}`\n\n"
            f"Port: `{port}`\n\n",
        )
    else:
        append_line(summary_path)
        append_line(summary_path, "---")
        append_line(summary_path)
        append_line(summary_path, f"Generated: {datetime.now().isoformat(timespec='seconds')}")
        append_line(summary_path)

    for scenario_name in scenario_order:
        scenario = scenarios[scenario_name]
        print(f"\n=== {scenario.name} ===")
        run_scenario(scenario, host, port, log_dir, append, summary_path)

    print("")
    print(f"Saved robustness summary to {summary_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--log-dir", type=Path, default=LOG_DIR)
    parser.add_argument(
        "--only",
        choices=("smoke", "malformed", "partial", "oversized", "all"),
        default="all",
        help="which robustness scenario to run",
    )
    parser.add_argument(
        "--partial-delay",
        type=float,
        default=10.0,
        help="delay used by partial_client.py between the two command fragments",
    )
    parser.add_argument(
        "--oversized-bytes",
        type=int,
        default=10000,
        help="number of bytes sent by oversized_client.py before newline",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="append to the summary instead of replacing previous outputs",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        run_all(
            selected=args.only,
            host=args.host,
            port=args.port,
            log_dir=args.log_dir,
            partial_delay=args.partial_delay,
            oversized_bytes=args.oversized_bytes,
            append=args.append,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
