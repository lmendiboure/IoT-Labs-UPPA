"""sensor.py — a small virtual environmental sensor used in Parts 4 and 6.

    python sensor.py          stop it with Ctrl+C

Everything marked TODO is yours to write. The rest works as it is.
"""
import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))

NAME = "alice"                                  # TODO: your name, in lower case
TOPIC = f"lab/sensors/{NAME}/env"
STATUS = f"lab/sensors/{NAME}/status"
PERIOD_S = 5                                    # seconds between two messages (2 to 10)
KEEPALIVE_S = 60                                # later set to 15 s


def reading():
    """One measurement, as the dictionary the sensor will publish."""
    # TODO: return a dictionary with
    #   temperature_c  a number, around 20-23 °C (random.uniform is fine: the sensor is not real)
    #   humidity_pct   a number, around 40-55 %
    #   measured_at    the time of the measurement, ISO 8601, in UTC
    return {}


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sensor-{NAME}")

# PART 6 TODO: register the last will — 'offline' on STATUS, retained.
#   It travels in the CONNECT packet: where must this line be, then?

c.connect(HOST, PORT, keepalive=KEEPALIVE_S)
c.loop_start()                                  # the network runs in a background thread

# PART 6 TODO: publish 'online' on STATUS, retained.

while True:
    payload = json.dumps(reading())
    c.publish(TOPIC, payload)
    print("published", payload)
    time.sleep(PERIOD_S)
