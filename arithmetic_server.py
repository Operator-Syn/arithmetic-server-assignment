#!/usr/bin/env python3
"""Concurrent TCP arithmetic server.

Run:

    python3 arithmetic_server.py

or:

    python3 arithmetic_server.py --host 127.0.0.1 --port 14344
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import selectors
import socket
import threading
from collections import deque
from pathlib import Path
from typing import Deque, Optional


WELCOME = "OK Welcome to the CSc 113 Arithmetic Server!"
BYE = "OK Bye."

MAX_LINE_BYTES = 256
RECV_SIZE = 4096

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 14344

HELP_TEXT = (
    "OK The following commands are available:\n"
    "ADD <N1> <N2> - to add N1 and N2\n"
    "SUB <N1> <N2> - to subtract N2 from N1\n"
    "MUL <N1> <N2> - to multiply N1 by N2\n"
    "DIV <N1> <N2> - to divide N1 by N2\n"
    "RND <N> - to generate a random number between 1 and N, inclusive\n"
    "HIST - to show the last 5 valid operations in the session\n"
    "HELP [command] - to display the syntax and semantics of a specific command. "
    "If no command is specified, it will display all the available commands and their meanings\n"
    "QUIT - to end the current session of the arithmetic server"
)

COMMAND_HELP = {
    "ADD": "OK ADD <N1> <N2> - to add N1 and N2",
    "SUB": "OK SUB <N1> <N2> - to subtract N2 from N1",
    "MUL": "OK MUL <N1> <N2> - to multiply N1 by N2",
    "DIV": "OK DIV <N1> <N2> - to divide N1 by N2",
    "RND": "OK RND <N> - to generate a random number between 1 and N, inclusive",
    "HIST": "OK HIST - to show the last 5 valid operations in the session",
    "HELP": (
        "OK HELP [command] - to display the syntax and semantics of a specific command. "
        "If no command is specified, it will display all the available commands and their meanings"
    ),
    "QUIT": "OK QUIT - to end the current session of the arithmetic server",
    "MOD": "OK MOD <N1> <N2> - to return the remainder after dividing N1 by N2",
}


class RecvLogger:
    def __init__(self, path: Optional[Path]) -> None:
        self.path = path
        self._lock = threading.Lock()

        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, address: tuple[str, int], data: bytes) -> None:
        if self.path is None:
            return

        timestamp = dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = (
            f"[{timestamp}] {address[0]}:{address[1]} recv() -> "
            f"{len(data)} bytes {data!r}\n"
        )

        # Different client threads can write logs at the same time.
        with self._lock:
            with self.path.open("a", encoding="utf-8") as log_file:
                log_file.write(line)


class ServerState:
    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        self._client_sockets: set[socket.socket] = set()
        self._threads: list[threading.Thread] = []

    def register_client(self, conn: socket.socket) -> None:
        with self._lock:
            self._client_sockets.add(conn)

    def unregister_client(self, conn: socket.socket) -> None:
        with self._lock:
            self._client_sockets.discard(conn)

    def register_thread(self, thread: threading.Thread) -> None:
        with self._lock:
            self._threads.append(thread)

    def close_clients(self) -> None:
        with self._lock:
            sockets = list(self._client_sockets)

        for conn in sockets:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                conn.close()
            except OSError:
                pass

    def join_threads(self, timeout: float = 0.2) -> None:
        with self._lock:
            threads = list(self._threads)

        for thread in threads:
            thread.join(timeout=timeout)


class Session:
    def __init__(self) -> None:
        # Belongs to one client only, not the whole server.
        self.history: Deque[str] = deque(maxlen=5)

    def add_history(self, command: str, result: int) -> None:
        self.history.append(f"{command} -> {result}")


def send_line(conn: socket.socket, text: str) -> None:
    conn.sendall((text + "\n").encode("utf-8"))


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError("Arguments must be integers.") from exc


def require_arg_count(command: str, args: list[str], expected: int) -> None:
    if len(args) != expected:
        raise ValueError(f"Invalid number of arguments to {command}.")


def handle_binary_operation(
    operation: str,
    args: list[str],
    session: Session,
) -> tuple[str, bool]:
    require_arg_count(operation, args, 2)

    n1 = parse_int(args[0])
    n2 = parse_int(args[1])

    if operation == "ADD":
        result = n1 + n2

    elif operation == "SUB":
        result = n1 - n2

    elif operation == "MUL":
        result = n1 * n2

    elif operation == "DIV":
        if n2 == 0:
            return "ERR Division by 0.", False
        result = n1 // n2

    elif operation == "MOD":
        if n2 == 0:
            return "ERR Modulo by 0.", False
        result = n1 % n2

    else:
        return f"ERR Unknown operation {operation}.", False

    canonical = f"{operation} {n1} {n2}"
    session.add_history(canonical, result)

    return f"OK {result}", False


def handle_rnd(args: list[str], session: Session) -> tuple[str, bool]:
    require_arg_count("RND", args, 1)

    upper_bound = parse_int(args[0])

    if upper_bound < 1:
        return "ERR RND requires N >= 1.", False

    result = random.randint(1, upper_bound)
    canonical = f"RND {upper_bound}"
    session.add_history(canonical, result)

    return f"OK {result}", False


def handle_hist(args: list[str], session: Session) -> tuple[str, bool]:
    require_arg_count("HIST", args, 0)

    lines = ["OK — The last five (5) valid operations from this session are:"]
    lines.extend(session.history)

    return "\n".join(lines), False


def handle_help(args: list[str]) -> tuple[str, bool]:
    if len(args) == 0:
        return HELP_TEXT, False

    if len(args) == 1:
        topic = args[0].upper()

        if topic not in COMMAND_HELP:
            return f"ERR Unknown operation {topic}.", False

        return COMMAND_HELP[topic], False

    return "ERR Invalid number of arguments to HELP.", False


def handle_quit(args: list[str]) -> tuple[str, bool]:
    require_arg_count("QUIT", args, 0)
    return BYE, True


def handle_command(line: str, session: Session) -> tuple[str, bool]:
    parts = line.split()

    # Blank lines will be ignored.
    if not parts:
        return "", False

    operation = parts[0].upper()
    args = parts[1:]

    try:
        if operation in {"ADD", "SUB", "MUL", "DIV", "MOD"}:
            return handle_binary_operation(operation, args, session)

        if operation == "RND":
            return handle_rnd(args, session)

        if operation == "HIST":
            return handle_hist(args, session)

        if operation == "HELP":
            return handle_help(args)

        if operation == "QUIT":
            return handle_quit(args)

        return f"ERR Unknown operation {operation}.", False

    except ValueError as exc:
        return f"ERR {exc}", False


def extract_raw_lines(buffer: bytearray) -> list[bytes]:
    # TCP is a byte stream, so a command may arrive partially or together
    # with other commands. Only complete newline-terminated lines are returned.
    lines: list[bytes] = []

    while True:
        try:
            newline_index = buffer.index(0x0A)  # newline: "\n"
        except ValueError:
            # No full command yet. Leave the partial data in the buffer.
            return lines

        # Copy one complete line without the newline character.
        raw_line = bytes(buffer[:newline_index])

        # Remove the processed line from the buffer.
        del buffer[: newline_index + 1]

        lines.append(raw_line)

def decode_command_line(raw_line: bytes) -> str:
    # Accept telnet-style CRLF input.
    if raw_line.endswith(b"\r"):
        raw_line = raw_line[:-1]

    return raw_line.decode("utf-8", errors="replace")


def handle_client(
    conn: socket.socket,
    address: tuple[str, int],
    recv_logger: RecvLogger,
    max_line_bytes: int,
    server_state: ServerState,
) -> None:
    session = Session()
    buffer = bytearray()
    discarding_oversized_line = False

    server_state.register_client(conn)

    try:
        with conn:
            try:
                send_line(conn, WELCOME)
            except OSError:
                return

            while not server_state.stop_event.is_set():
                try:
                    data = conn.recv(RECV_SIZE)
                except OSError:
                    return

                recv_logger.log(address, data)

                if data == b"":
                    return

                # Store received bytes because.
                buffer.extend(data)

                # If a command was too long, ignore the rest until a newline.
                if discarding_oversized_line:
                    try:
                        newline_index = buffer.index(0x0A)
                    except ValueError:
                        buffer.clear()
                        continue

                    del buffer[: newline_index + 1]
                    discarding_oversized_line = False

                for raw_line in extract_raw_lines(buffer):
                    if len(raw_line) + 1 > max_line_bytes:
                        try:
                            send_line(conn, "ERR Command too long.")
                        except OSError:
                            return
                        continue

                    line = decode_command_line(raw_line)
                    response, should_close = handle_command(line.strip(), session)

                    if response:
                        try:
                            send_line(conn, response)
                        except OSError:
                            return

                    if should_close:
                        return

                # A partial command without newline is already past the limit.
                if len(buffer) >= max_line_bytes:
                    try:
                        send_line(conn, "ERR Command too long.")
                    except OSError:
                        return

                    buffer.clear()
                    discarding_oversized_line = True

    finally:
        server_state.unregister_client(conn)


def serve(host: str, port: int, recv_log: Optional[Path], max_line_bytes: int) -> None:
    recv_logger = RecvLogger(recv_log)
    server_state = ServerState()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        server_address = (host, port)
        print("starting up on {} port {}".format(*server_address))

        sock.bind(server_address)
        sock.listen(64)
        sock.setblocking(False)

        selector = selectors.DefaultSelector()
        selector.register(sock, selectors.EVENT_READ, data=None)

        try:
            while not server_state.stop_event.is_set():
                events = selector.select(timeout=0.5)

                for key, _ in events:
                    if key.fileobj is not sock:
                        continue

                    try:
                        connection, client_address = sock.accept()
                    except BlockingIOError:
                        continue

                    print("connection from", client_address)

                    connection.setblocking(True)

                    thread = threading.Thread(
                        target=handle_client,
                        args=(
                            connection,
                            client_address,
                            recv_logger,
                            max_line_bytes,
                            server_state,
                        ),
                        daemon=True,
                    )

                    thread.start()
                    server_state.register_thread(thread)

        except KeyboardInterrupt:
            print("\nKeyboard interrupt received. Shutting down server...")

        finally:
            server_state.stop_event.set()

            try:
                selector.unregister(sock)
            except Exception:
                pass

            selector.close()
            server_state.close_clients()
            server_state.join_threads()
            print("Server stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--recv-log", type=Path, default=Path("logs/recv.log"))
    parser.add_argument("--max-line-bytes", type=int, default=MAX_LINE_BYTES)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    serve(args.host, args.port, args.recv_log, args.max_line_bytes)


if __name__ == "__main__":
    main()