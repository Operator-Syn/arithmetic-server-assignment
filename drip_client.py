#!/usr/bin/env python3
"""Send one command to the arithmetic server one byte at a time."""

from __future__ import annotations

import argparse
import socket
import time


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
    parser.add_argument("--command", default="ADD 1 2")
    parser.add_argument("--delay", type=float, default=0.3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    command = args.command
    if not command.endswith("\n"):
        command += "\n"

    with socket.create_connection((args.host, args.port)) as sock:
        print(read_line(sock))
        for byte in command.encode("utf-8"):
            sock.sendall(bytes([byte]))
            time.sleep(args.delay)
        print(read_line(sock))
        sock.sendall(b"QUIT\n")
        print(read_line(sock))


if __name__ == "__main__":
    main()
