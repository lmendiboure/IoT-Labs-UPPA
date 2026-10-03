"""watch_uplinks.py — one line per uplink of the freezer probes, as the network server publishes them.

    python watch_uplinks.py          leave it running in a spare terminal; Ctrl+C to stop

Ready to use: nothing to write here. It prints the fields used in the freezer trace questions.
"""
import json
import os

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("application/adour-coldchain/device/+/event/up")
    print(f"{'received at (time)':<26} {'probe':<17} {'fCnt':>6}  gateways")


def on_message(client, userdata, msg):
    e = json.loads(msg.payload)
    print(f"{e['time']:<26} {e['deviceInfo']['deviceName']:<17} {e['fCnt']:>6}  {len(e['rxInfo'])}", flush=True)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="uplink-monitor")
c.on_connect = on_connect
c.on_message = on_message
c.connect(HOST, PORT, keepalive=60)
c.loop_forever()
