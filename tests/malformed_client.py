#!/usr/bin/env python3
"""Exercise malformed input cases."""

from __future__ import annotations

import argparse
import socket


COMMANDS = [
    "",
    "MUL 3",
    "ADD one 2",
    "XYZ 2 1",
    "HELP ADD SUB",
    "RND 0",
    "QUIT",
]


def read_line(sock: socket.socket) -> str:
    chunks = bytearray()
    while True:
        data = sock.recv(1)
        if data == b"":
            raise ConnectionError("server closed connection")
        chunks.extend(data)
        if data == b"\n":
            return chunks.decode("utf-8", errors="replace").rstrip("\r\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with socket.create_connection((args.host, args.port)) as sock:
        print(read_line(sock))
        for command in COMMANDS:
            print(f"> {command}")
            sock.sendall((command + "\n").encode("utf-8"))
            if command:
                print(read_line(sock))


if __name__ == "__main__":
    main()
