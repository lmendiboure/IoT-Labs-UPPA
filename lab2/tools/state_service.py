#!/usr/bin/env python3
"""AC-1 teaching endpoint: one live state exposed by MQTT and by CoAP."""
from __future__ import annotations

import json
import math
import os
import socket
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from coap_common import decode_message, describe, encode_message, new_mid

MQTT_HOST = os.getenv("MQTT_HOST", "relay")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1884"))
MQTT_TOPIC = "lab2/autoclave/AC-1/live"
COAP_PORT = 5683


def state(now: float | None = None) -> dict:
    now = time.time() if now is None else now
    seq = int(now // 2)
    return {
        "seq": seq,
        "observed_at": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "state": "DWELL",
        "air_c": round(180.0 + 0.55 * math.sin(seq / 7.0), 1),
        "pressure_bar": round(7.0 + 0.04 * math.sin(seq / 11.0), 2),
    }


def mqtt_loop():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ac1-live", protocol=mqtt.MQTTv311)
    c.reconnect_delay_set(1, 10)
    while True:
        try:
            c.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            break
        except OSError:
            time.sleep(1)
    c.loop_start()
    last = None
    while True:
        current = state()
        if current["seq"] != last:
            wire = json.dumps(current, separators=(",", ":"))
            c.publish(MQTT_TOPIC, wire, qos=1)
            print(f"MQTT published seq={current['seq']}", flush=True)
            last = current["seq"]
        time.sleep(0.15)


def coap_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", COAP_PORT))
    dropped_tokens: set[bytes] = set()
    print(f"CoAP listening on udp/{COAP_PORT}: /state and /state/drop-once", flush=True)
    while True:
        data, peer = sock.recvfrom(4096)
        try:
            req = decode_message(data)
        except Exception as exc:
            print(f"CoAP malformed from {peer}: {exc}", flush=True)
            continue
        print(f"CoAP <- {peer[0]}:{peer[1]} {describe(req)}", flush=True)
        if req["code"] != 1 or req["path"] not in ("/state", "/state/drop-once"):
            continue
        if req["path"] == "/state/drop-once" and req["token"] not in dropped_tokens:
            dropped_tokens.add(req["token"])
            print(f"CoAP !! deliberately ignored first request token={req['token'].hex()}", flush=True)
            continue
        payload = json.dumps(state(), separators=(",", ":")).encode()
        if req["type"] == 0:  # piggyback response in ACK
            response = encode_message(2, 69, req["mid"], req["token"], [], payload)
        elif req["type"] == 1:
            response = encode_message(1, 69, new_mid(), req["token"], [], payload)
        else:
            continue
        sock.sendto(response, peer)
        print(f"CoAP -> {peer[0]}:{peer[1]} {describe(decode_message(response))}", flush=True)


if __name__ == "__main__":
    threading.Thread(target=mqtt_loop, daemon=True, name="mqtt-live").start()
    coap_loop()
