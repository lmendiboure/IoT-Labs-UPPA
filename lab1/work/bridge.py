"""bridge.py — republishes two of the plant's devices in your plant namespace.

    python bridge.py          stop it with Ctrl+C

It subscribes to the vendors' topics, normalizes each message, and publishes it on the device's topic
from your tree.json. Everything marked TODO is yours to write.
"""
import json
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from decode import decode           # your freezer payload decoder

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
TREE = json.load(open(os.path.join(os.getenv("WORK", "/work"), "tree.json")))

NAME = "alice"                      # TODO: your name
PSI_TO_BAR = 0.0689476

# Which ChirpStack device is which probe of the inventory? The event names each probe in words.
PROBES = {
    # TODO: "<deviceName of the probe near the door>": "FRZ1-T1",
    #       "<deviceName of the probe at the back>": "FRZ1-T2",
}


def compressor(d):
    """compressors/CMP1, already parsed from JSON -> the clean message of CMP-1."""
    # TODO: pressure_bar (from pressure_psi, at least two decimals) and measured_at
    #       (ISO 8601 with its time zone, from the device's own 'timestamp': seconds since 1970).
    #       Add any field you find useful.
    return {}


def probe(event):
    """A ChirpStack uplink event, already parsed from JSON -> the clean message of the probe."""
    # TODO: temperature_c from the 6-byte application payload in event["data"] (use decode()),
    #       measured_at: the probe has no clock — the best time is the network server's reception
    #       time, event["time"]. Add any field you find useful (fCnt, battery...).
    return {}


def on_connect(client, userdata, flags, reason_code, properties):
    # Subscribing here, not after connect(): a reconnection then subscribes again.
    # TODO: subscribe to the compressor's topic and to every ChirpStack uplink of the cold chain
    #       (one filter with a wildcard).
    pass


def on_message(client, userdata, msg):
    d = json.loads(msg.payload)
    if msg.topic == "compressors/CMP1":
        device, clean = "CMP-1", compressor(d)
    else:
        device, clean = PROBES.get(d["deviceInfo"]["deviceName"]), probe(d)
    if device is None:
        print("unknown device, ignored:", msg.topic)
        return
    client.publish(TREE[device], json.dumps(clean), qos=1)
    print(device, "->", TREE[device], clean)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"bridge-{NAME}")
c.on_connect = on_connect
c.on_message = on_message
c.connect(HOST, PORT, keepalive=30)
c.loop_forever()
