#!/usr/bin/env python3
"""Starter for the idempotent quality-recorder extension."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
TOPIC = "quality/autoclave/AC-1/cure-records"

p = argparse.ArgumentParser(description="Lab 2 MQTT subscriber representing the quality application; display and optionally log delivered cure records.")
p.add_argument("--qos", type=int, choices=(0, 1, 2), default=0)
p.add_argument("--client-id", default="audit-recorder")
p.add_argument("--topic", default=TOPIC)
p.add_argument("--persistent", action="store_true")
p.add_argument("--log", help="append deliveries to this JSON-lines file")
a = p.parse_args()


def has_session(flags):
    if isinstance(flags, dict):
        return bool(flags.get("session present") or flags.get("session_present"))
    return bool(getattr(flags, "session_present", False))


def already_recorded(log_path, record_id):
    """Return True if record_id already appears in the JSONL audit log."""
    if not log_path or not os.path.exists(log_path):
        return False

    # TODO: read the existing JSONL records and return True when record_id
    # has already been stored. Ignore empty or malformed lines.
    return False


def on_connect(client, userdata, flags, reason_code, properties=None):
    present = has_session(flags)
    print(f"connected client_id={a.client_id} persistent={a.persistent} session_present={present}")
    if not a.persistent or not present:
        result, mid = client.subscribe(a.topic, qos=a.qos)
        if result != mqtt.MQTT_ERR_SUCCESS:
            print(f"subscribe failed: {result}", file=sys.stderr)
        else:
            print(f"SUBSCRIBE sent topic={a.topic} qos={a.qos} mid={mid}")
    else:
        print("stored subscription resumed: no SUBSCRIBE sent")


def on_message(client, userdata, msg):
    try:
        doc = json.loads(msg.payload.decode())
        rid = doc.get("record_id", "?")
    except Exception:
        doc = {"raw": msg.payload.decode(errors="replace")}
        rid = "?"
    print(f"RECEIVED record_id={rid} qos={msg.qos} dup={bool(msg.dup)} retain={bool(msg.retain)}")
    if a.log:
        if already_recorded(a.log, rid):
            print(f"SKIPPED record_id={rid}: already present in application log")
            return
        row = {
            "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "record_id": rid,
            "mqtt_qos": msg.qos,
            "mqtt_dup": bool(msg.dup),
            "payload": doc,
        }
        with open(a.log, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")


c = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=a.client_id,
    clean_session=not a.persistent,
    protocol=mqtt.MQTTv311,
)
c.on_connect = on_connect
c.on_message = on_message
c.connect(HOST, PORT, keepalive=30)
try:
    c.loop_forever(retry_first_connection=True)
except KeyboardInterrupt:
    print("\nclosing recorder")
    try:
        c.disconnect()
    except Exception:
        pass
