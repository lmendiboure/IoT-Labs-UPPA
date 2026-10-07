#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
TOPIC = "quality/autoclave/AC-1/cure-records"

p = argparse.ArgumentParser(description="Lab 2 MQTT publisher: build and publish one synthetic AC-1 cure-completion record.")
p.add_argument("record_id", help="stable application record identifier, e.g. CR-101")
p.add_argument("--qos", type=int, choices=(0, 1, 2), default=0)
p.add_argument("--batch")
a = p.parse_args()

payload = {
    "record_id": a.record_id,
    "batch": a.batch or f"BATCH-{a.record_id.split('-')[-1]}",
    "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "recipe": "CFRP-180C",
    "max_air_c": 180.4,
    "min_pressure_bar": 6.96,
    "result": "PASS",
}

connected = False

def on_connect(client, userdata, flags, reason_code, properties=None):
    global connected
    connected = reason_code == 0

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cure-source", protocol=mqtt.MQTTv311)
c.on_connect = on_connect
c.connect(HOST, PORT, keepalive=30)
c.loop_start()
for _ in range(100):
    if connected:
        break
    time.sleep(0.03)
if not connected:
    raise SystemExit("could not connect to the MQTT broker")
wire = json.dumps(payload, separators=(",", ":"))
print(f"publishing {a.record_id} qos={a.qos}")
info = c.publish(TOPIC, wire, qos=a.qos)
info.wait_for_publish(timeout=10)
if not info.is_published():
    raise SystemExit("publish did not complete")
print(f"publish complete: mid={info.mid}")
c.disconnect()
c.loop_stop()
