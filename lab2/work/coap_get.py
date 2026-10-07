#!/usr/bin/env python3
"""Small CoAP GET client for the Lab 2 experiments."""
from __future__ import annotations

import argparse
import json
import random
import socket
import sys
import time

# /lab is on PYTHONPATH in the image; tools/coap_common.py is copied there.
sys.path.insert(0, "/lab")
from coap_common import decode_message, describe, encode_get, new_mid, new_token

p = argparse.ArgumentParser(description="Send one CoAP GET and show the message-level exchange.")
p.add_argument("uri", nargs="?", default="coap://ac1-edge/state")
p.add_argument("--type", choices=("con", "non"), default="con")
p.add_argument("--timeout", type=float, default=1.0)
p.add_argument("--max-attempts", type=int, default=4)
a = p.parse_args()

if not a.uri.startswith("coap://"):
    raise SystemExit("URI must start with coap://")
rest = a.uri[len("coap://"):]
hostport, _, path = rest.partition("/")
if ":" in hostport:
    host, port_s = hostport.rsplit(":", 1)
    port = int(port_s)
else:
    host, port = hostport, 5683
path = "/" + path

mid = new_mid()
token = new_token()
confirmable = a.type == "con"
wire = encode_get(path, confirmable=confirmable, mid=mid, token=token)
request = decode_message(wire)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(a.timeout)
peer = (socket.gethostbyname(host), port)
attempts = a.max_attempts if confirmable else 1

for attempt in range(1, attempts + 1):
    timeout = a.timeout * (2 ** (attempt - 1)) if confirmable else a.timeout
    sock.settimeout(timeout)
    print(f"SEND attempt={attempt} bytes={len(wire)}: {describe(request)}")
    sock.sendto(wire, peer)
    try:
        data, _ = sock.recvfrom(4096)
    except socket.timeout:
        print(f"TIMEOUT after {timeout:.1f}s")
        if attempt < attempts:
            continue
        raise SystemExit(2)
    msg = decode_message(data)
    print(f"RECV bytes={len(data)}: {describe(msg)}")
    if msg["token"] != token:
        print("ignoring response with a different token")
        continue
    if msg["payload"]:
        try:
            doc = json.loads(msg["payload"].decode())
            print("PAYLOAD:", json.dumps(doc, indent=2))
        except Exception:
            print("PAYLOAD:", msg["payload"].decode(errors="replace"))
    break
