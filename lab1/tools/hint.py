#!/usr/bin/env python3
"""hint — help for one exercise, one step at a time.

    hint 4      the next hint for exercise 4 (run it again for the next one)
    hint 4 2    hint number 2 of exercise 4

The last hint of each exercise is close to the answer: try the others first.
The hints you open are listed in your report — that is fine, it is what they are for.
"""
import json
import os
import sys

WORK = os.getenv("WORK", "/work")
SEEN = os.path.join(WORK, ".hints.json")

HINTS = {
    1: [
        "On the VM, `docker compose ps` lists the four services: broker, relay, plant, workstation. "
        "All should be 'Up'. If one is not, `docker compose logs <service>` says why.",
        "The checker runs inside the workstation. Open it with `docker compose exec workstation bash`, "
        "then type `check 1`. From outside the workstation, `check` does not exist.",
        "Still red? Restart everything: `docker compose down` then `docker compose up -d`, wait 30 s, `check 1`.",
    ],
    2: [
        "mosquitto_pub needs a host (-h), a port (-p), a topic (-t) and a message (-m). "
        "The host is relay and the port 1884: everything goes through the relay, never to the broker directly.",
        "Publish: mosquitto_pub -h relay -p 1884 -t lab/hello -m 'hello'. "
        "Subscribe with a wildcard in a second terminal: mosquitto_sub -h relay -p 1884 -t 'hygrolab/#' -v",
        "Quote topics that contain # or +, otherwise your shell may interpret them. "
        "-v prints the topic in front of each message.",
    ],
    3: [
        "Everything you need is in the viewer. The Packets tab shows, for each packet, the payload size "
        "and the size of the whole packet. The Topics tab averages them over the last 5 minutes.",
        "The 'data' field of a ChirpStack event is base64. In Python: "
        "len(base64.b64decode('...')). Copy one from the viewer or from mosquitto_sub.",
        "plant_bytes_per_minute: in the Topics tab, for every topic published by the plant, "
        "messages x avg packet, summed, then divided by 5 (the tab covers 5 minutes). "
        "Leave out your own topics (lab/...).",
    ],
    4: [
        "Start from publish_example.py: copy it to sensor.py. Give your client an id starting with sensor-, "
        "for example sensor-alice, and publish on lab/sensors/alice/env.",
        "Build the payload with a dict and json.dumps(). measured_at: "
        "datetime.now(timezone.utc).isoformat(timespec='seconds'). Loop forever with time.sleep(5).",
        "Skeleton:\n"
        "    c.loop_start()\n"
        "    while True:\n"
        "        reading = {'temperature_c': round(random.uniform(19, 23), 1),\n"
        "                   'humidity_pct': random.randint(40, 55),\n"
        "                   'measured_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        "        c.publish(TOPIC, json.dumps(reading), qos=1)\n"
        "        time.sleep(5)",
    ],
    5: [
        "Follow the ISA-95 hierarchy, from the most general to the most specific: enterprise, site, area, "
        "cell (work unit), then the device. A subscription can then pick any level with + and cut the rest with #.",
        "Every need should take one filter. 'Everything in the curing area' is easy only if the area is at the same "
        "level in every topic. 'Every energy meter' is easy only if the class of device is a level of its own. "
        "The weather station belongs to the site, not to an area: give it values that no need will catch by mistake.",
        "One tree that works: <enterprise>/<site>/<area>/<cell>/<class>/<device>, in lower case, "
        "for example adour/tarnos/curing/autoclave-1/machine/AC-1. Then N1 is adour/tarnos/curing/#.",
    ],
    6: [
        "Two separate things: a retained message on lab/sensors/<name>/status saying online, "
        "and a last will on the same topic saying offline, retained too.",
        "The last will is set BEFORE connect(): c.will_set(STATUS, 'offline', qos=1, retain=True). "
        "Right after connecting, publish 'online' with retain=True.",
        "To die abruptly, stop sensor.py with Ctrl+C: Python closes the socket without sending DISCONNECT. "
        "Then look at the Clients tab of the viewer, and at mosquitto_sub -t 'lab/sensors/+/status' -v.",
    ],
    7: [
        "Start your sensor with a short keepalive: c.connect(HOST, PORT, keepalive=15). "
        "Then, in the viewer's Clients tab, press Freeze on its connection.",
        "Keep a subscriber on lab/sensors/+/status running and note the time: the broker waits a while "
        "before it declares the client gone and publishes the will. Compare that wait with the keepalive.",
        "The MQTT specification (3.1.1, section 3.1.2.10) says how long the broker waits: search for "
        "'one and a half times the Keep Alive'.",
    ],
    8: [
        "A bridge is a client that subscribes and publishes. Subscribe to the three sources "
        "(hygrolab/CR-01/temperature, compressors/CMP1, application/adour-coldchain/device/+/event/up); "
        "subscribe in on_connect, so that a reconnection subscribes again; in on_message, look at msg.topic to know which one arrived, "
        "compute the clean value, and publish it on that device's topic from your tree.json.",
        "The three conversions. Cleanroom: float(msg.payload), no timestamp in the message, so use the time "
        "you received it. Compressor: json.loads, pressure_psi * 0.0689476 gives bar, and 'timestamp' is "
        "seconds since 1970 (datetime.fromtimestamp(ts, timezone.utc)). Freezer: json.loads, "
        "base64.b64decode(event['data']) gives 6 bytes, and struct.unpack('>BhBBB', raw) gives "
        "(frame type, temperature in hundredths of a degree, humidity, battery, status); the time is in event['time'].",
        "Skeleton:\n"
        "    TREE = json.load(open('/work/tree.json'))\n"
        "    def on_connect(c, u, flags, rc, props):\n"
        "        for f in ('hygrolab/CR-01/temperature', 'compressors/CMP1',\n"
        "                  'application/adour-coldchain/device/+/event/up'):\n"
        "            c.subscribe(f)\n"
        "    def on_message(c, u, msg):\n"
        "        if msg.topic == 'compressors/CMP1':\n"
        "            d = json.loads(msg.payload)\n"
        "            out = {'pressure_bar': round(d['pressure_psi'] * 0.0689476, 3),\n"
        "                   'measured_at': datetime.fromtimestamp(d['timestamp'], timezone.utc).isoformat()}\n"
        "            c.publish(TREE['CMP-1'], json.dumps(out))\n"
        "        elif ...  # the cleanroom, then the freezer probes (map each probe's deviceName to FRZ1-T1 or FRZ1-T2)",
    ],
}


def main():
    args = [a for a in sys.argv[1:] if a.isdigit()]
    if not args or int(args[0]) not in HINTS:
        print(__doc__)
        return
    n = int(args[0])
    try:
        seen = json.load(open(SEEN))
    except (OSError, json.JSONDecodeError):
        seen = {}
    hints = HINTS[n]
    if len(args) > 1:
        level = max(1, min(int(args[1]), len(hints)))
    else:
        level = min(seen.get(str(n), 0) + 1, len(hints))
    seen[str(n)] = max(seen.get(str(n), 0), level)
    try:
        with open(SEEN, "w") as f:
            json.dump(seen, f)
    except OSError:
        pass
    print(f"Exercise {n}, hint {level} of {len(hints)}:\n")
    print(hints[level - 1])
    if level < len(hints):
        print(f"\n(still stuck later? `hint {n}` again)")


if __name__ == "__main__":
    main()
