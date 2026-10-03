"""sensor.py — a small virtual environmental sensor used in Parts 4 and 6.

    python sensor.py          stop it with Ctrl+C

The measurement generation is already implemented. In Part 6 you will only add the two MQTT
operations that implement the online/offline status.
"""
import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))

NAME = "student"
TOPIC = f"lab/sensors/{NAME}/env"
STATUS = f"lab/sensors/{NAME}/status"
PERIOD_S = 5
KEEPALIVE_S = 60                                # later set to 15 s


def reading():
    """Generate one plausible environmental measurement."""
    return {
        "temperature_c": round(random.uniform(20.0, 23.0), 2),
        "humidity_pct": round(random.uniform(40.0, 55.0), 1),
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sensor-{NAME}")

# PART 6 TODO: register the last will — 'offline' on STATUS, retained.
# It must be configured before connect().

c.connect(HOST, PORT, keepalive=KEEPALIVE_S)
c.loop_start()

# PART 6 TODO: publish 'online' on STATUS, retained.

while True:
    payload = json.dumps(reading())
    c.publish(TOPIC, payload)
    print("published", payload)
    time.sleep(PERIOD_S)
