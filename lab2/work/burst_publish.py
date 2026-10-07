#!/usr/bin/env python3
"""Publish a numbered burst on one MQTT connection for queue-limit experiments."""
import argparse
import json
import os
import time

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))

p = argparse.ArgumentParser()
p.add_argument("count", type=int, nargs="?", default=1100)
p.add_argument("--topic", default="lab2/queue-test")
p.add_argument("--prefix", default="QUEUE")
p.add_argument("--qos", type=int, choices=(0, 1, 2), default=1)
a = p.parse_args()

connected = False

def on_connect(c, userdata, flags, reason_code, properties=None):
    global connected
    connected = reason_code == 0

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="burst-source", protocol=mqtt.MQTTv311)
c.on_connect = on_connect
c.connect(HOST, PORT, keepalive=30)
c.loop_start()
for _ in range(100):
    if connected:
        break
    time.sleep(0.03)
if not connected:
    raise SystemExit("could not connect to MQTT broker")

infos = []
for i in range(1, a.count + 1):
    payload = json.dumps({"record_id": f"{a.prefix}-{i:04d}", "seq": i}, separators=(",", ":"))
    infos.append(c.publish(a.topic, payload, qos=a.qos))
for info in infos:
    info.wait_for_publish(timeout=30)
print(f"published={a.count} topic={a.topic} qos={a.qos}")
c.disconnect()
c.loop_stop()
