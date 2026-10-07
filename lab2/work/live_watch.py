#!/usr/bin/env python3
"""Persistent MQTT subscriber for the AC-1 live state used in Q15."""
import argparse
import json
import os
import sys
import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
TOPIC = "lab2/autoclave/AC-1/live"

p = argparse.ArgumentParser(description="Lab 2 MQTT subscriber for the changing AC-1 live-state stream.")
p.add_argument("--client-id", default="live-history")
p.add_argument("--persistent", action="store_true")
a = p.parse_args()


def present(flags):
    if isinstance(flags, dict):
        return bool(flags.get("session present") or flags.get("session_present"))
    return bool(getattr(flags, "session_present", False))


def on_connect(c, userdata, flags, reason_code, properties=None):
    resumed = a.persistent and present(flags)
    print(f"connected session_present={present(flags)}")
    if not resumed:
        c.subscribe(TOPIC, qos=1)
        print("SUBSCRIBE sent")
    else:
        print("stored subscription resumed")


def on_message(c, userdata, msg):
    doc = json.loads(msg.payload.decode())
    print(f"MQTT seq={doc['seq']} observed_at={doc['observed_at']} qos={msg.qos} dup={bool(msg.dup)}")

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=a.client_id,
                clean_session=not a.persistent, protocol=mqtt.MQTTv311)
c.on_connect = on_connect
c.on_message = on_message
c.connect(HOST, PORT, keepalive=30)
try:
    c.loop_forever(retry_first_connection=True)
except KeyboardInterrupt:
    try:
        c.disconnect()
    except Exception:
        pass
