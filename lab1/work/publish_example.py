"""The smallest MQTT publisher: connect, publish one message, leave politely.

    python publish_example.py

Exercise 4 starts from sensor.py, which works the same way.
"""
import os

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")          # always the relay, never the broker directly
PORT = int(os.getenv("MQTT_PORT", "1884"))

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="example-1")
c.connect(HOST, PORT, keepalive=60)
c.loop_start()                                  # the network runs in a background thread
info = c.publish("lab/example", "hello from the workstation", qos=1)
info.wait_for_publish()                         # wait for the broker's PUBACK
print("published, message id", info.mid)
c.disconnect()                                  # a polite goodbye: a DISCONNECT packet
c.loop_stop()
