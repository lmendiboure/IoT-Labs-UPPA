"""bridge.py — republish two plant sources in a common topic hierarchy.

    python bridge.py          stop it with Ctrl+C

The MQTT callback plumbing and timestamp conversion are already implemented. The remaining edits are
limited to the design choices made in the lab: output topics, one MQTT filter, and one unit conversion.
"""
import json
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from decode import decode

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))

# Copy the exact normalized topics designed in Q11.
# FRZ1-T2 should follow the same pattern as FRZ1-T1.
OUTPUT_TOPICS = {
    "CMP-1": "",       # TODO: Q11 topic for compressor pressure
    "FRZ1-T1": "",     # TODO: Q11 topic for freezer temperature
    "FRZ1-T2": "",     # TODO: same pattern for the second probe
}

COMPRESSOR_INPUT = "compressors/CMP1"
FREEZER_INPUT = ""      # TODO in step 2: one wildcard filter for all cold-chain uplinks

PSI_TO_BAR = 0.0689476

# Plant identifier <-> ChirpStack deviceName mapping.
PROBES = {
    "frz1-probe-door": "FRZ1-T1",
    "frz1-probe-back": "FRZ1-T2",
}


def unix_to_iso(seconds):
    """Convert Unix seconds to an ISO 8601 UTC timestamp."""
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def compressor(d):
    """Normalize one compressor message."""
    # TODO: replace None with the pressure converted from psi to bar, rounded to 2 decimals.
    pressure_bar = None
    return {
        "pressure_bar": pressure_bar,
        "measured_at": unix_to_iso(d["timestamp"]),
    }


def probe(event):
    """Normalize one ChirpStack freezer uplink."""
    values = decode(event["data"])
    return {
        "temperature_c": values["temperature_c"],
        "measured_at": event["time"],
    }


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe(COMPRESSOR_INPUT)
    if FREEZER_INPUT:
        client.subscribe(FREEZER_INPUT)


def on_message(client, userdata, msg):
    d = json.loads(msg.payload)
    if msg.topic == COMPRESSOR_INPUT:
        device, clean = "CMP-1", compressor(d)
    else:
        device = PROBES.get(d["deviceInfo"]["deviceName"])
        if device is None:
            print("unknown device, ignored:", msg.topic)
            return
        clean = probe(d)

    output = OUTPUT_TOPICS[device]
    if not output:
        print("no output topic configured for", device)
        return

    client.publish(output, json.dumps(clean))
    print(device, "->", output, clean)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bridge-student")
c.on_connect = on_connect
c.on_message = on_message
c.connect(HOST, PORT, keepalive=30)
c.loop_forever()
