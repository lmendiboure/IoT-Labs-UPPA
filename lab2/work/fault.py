#!/usr/bin/env python3
"""Arm or inspect a one-shot packet drop in the Lab 2 MQTT relay."""
import argparse
import json
import os
import urllib.parse
import urllib.request

VIEWER = os.getenv("VIEWER", "http://relay:8080")
p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="command", required=True)
d = sub.add_parser("drop-next")
d.add_argument("--client", required=True)
d.add_argument("--direction", choices=("up", "down"), required=True)
d.add_argument("--type", required=True, dest="packet_type")
sub.add_parser("show")
sub.add_parser("clear")
a = p.parse_args()
if a.command == "drop-next":
    q = urllib.parse.urlencode({"client": a.client, "dir": a.direction, "type": a.packet_type.upper()})
    url = f"{VIEWER}/api/drop-next?{q}"
elif a.command == "show":
    url = f"{VIEWER}/api/drop-rules"
else:
    url = f"{VIEWER}/api/drop-clear"
req = urllib.request.Request(url, method="POST")
with urllib.request.urlopen(req, timeout=5) as r:
    print(json.dumps(json.load(r), indent=2))
