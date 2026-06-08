#!/usr/bin/env python3
"""Send an oversized line with no newline to test resynchronization."""

from __future__ import annotations

import argparse
import socket


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
    parser.add_argument("--bytes", type=int, default=10000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with socket.create_connection((args.host, args.port)) as sock:
        print(read_line(sock))
        sock.sendall(b"X" * args.bytes)
        print(read_line(sock))
        sock.sendall(b"\nADD 1 2\n")
        print(read_line(sock))


if __name__ == "__main__":
    main()
