#!/usr/bin/env python3
"""Shared helpers for arithmetic server benchmark clients."""

from __future__ import annotations

import socket


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 14344
DEFAULT_COUNT = 1000
DEFAULT_TIMEOUT = 10.0

RECV_SIZE = 4096

COMMAND = b"ADD 1 2\n"
EXPECTED_RESPONSE = "OK 3"
QUIT = b"QUIT\n"


class LineReader:
    """Read newline-terminated responses from the arithmetic server."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = bytearray()

    def read_line(self) -> str:
        while True:
            try:
                newline_index = self.buffer.index(0x0A)
            except ValueError:
                data = self.sock.recv(RECV_SIZE)

                if data == b"":
                    raise ConnectionError("server closed connection")

                self.buffer.extend(data)
                continue

            raw_line = bytes(self.buffer[:newline_index])
            del self.buffer[: newline_index + 1]

            return raw_line.decode("utf-8", errors="replace").rstrip("\r")


def connect(host: str, port: int, timeout: float) -> tuple[socket.socket, LineReader]:
    sock = socket.create_connection((host, port), timeout=timeout)
    reader = LineReader(sock)

    welcome = reader.read_line()

    if not welcome.startswith("OK Welcome"):
        sock.close()
        raise RuntimeError(f"unexpected welcome line: {welcome!r}")

    return sock, reader


def read_expected_add_response(reader: LineReader) -> None:
    response = reader.read_line()

    if response != EXPECTED_RESPONSE:
        raise RuntimeError(f"unexpected response: {response!r}")


def close_session(sock: socket.socket, reader: LineReader) -> None:
    try:
        sock.sendall(QUIT)
        reader.read_line()
    except OSError:
        pass
    except ConnectionError:
        pass