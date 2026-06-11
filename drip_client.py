#!/usr/bin/env python3
import argparse, socket, time
def read_line(sock):
    data=b""
    while not data.endswith(b"\n"):
        chunk=sock.recv(1)
        if chunk==b"": raise ConnectionError("server closed connection")
        data+=chunk
    return data.decode(errors="replace").rstrip("\r\n")
parser=argparse.ArgumentParser()
parser.add_argument("--host",default="127.0.0.1")
parser.add_argument("--port",type=int,default=14344)
parser.add_argument("--delay",type=float,default=0.3)
args=parser.parse_args()
with socket.create_connection((args.host,args.port)) as sock:
    print(read_line(sock))
    for byte in b"ADD 1 2\n":
        sock.sendall(bytes([byte])); time.sleep(args.delay)
    print(read_line(sock))
    sock.sendall(b"QUIT\n"); print(read_line(sock))