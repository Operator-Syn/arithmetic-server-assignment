#!/usr/bin/env python3
"""Basic command smoke test client."""

from __future__ import annotations

import argparse
import socket


COMMANDS = [
    "ADD 1 2",
    "SUB 3 4",
    "MUL 5 6",
    "DIV 40 3",
    "DIV 12 0",
    "RND 100",
    "HIST",
    "HELP ADD",
    "STATS",
    "QUIT",
]


def read_response(sock: socket.socket) -> str:
    sock.settimeout(0.1)
    chunks = bytearray()
    try:
        while True:
            data = sock.recv(4096)
            if data == b"":
                break
            chunks.extend(data)
    except TimeoutError:
        pass
    finally:
        sock.settimeout(None)
    return chunks.decode("utf-8", errors="replace").rstrip("\r\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with socket.create_connection((args.host, args.port)) as sock:
        print(read_response(sock))
        for command in COMMANDS:
            print(f"> {command}")
            sock.sendall((command + "\n").encode("utf-8"))
            print(read_response(sock))


if __name__ == "__main__":
    main()
