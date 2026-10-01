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
        "The viewer gives sizes: in the Packets tab, 'payload B' and 'packet B' for each packet. The topic's "
        "length is just its number of characters. For the ChirpStack event, click its payload to see it whole: "
        "copy the value of 'data', and run python decode.py <that value> once decode.py is complete.",
        "Which event is FRZ1-T1? Compare deviceInfo.deviceName in the events with the note of FRZ1-T1 in "
        "inventory.json. In decode.py, the first TODO is one call: raw = base64.b64decode(data_b64). "
        "Then python decode.py --test tells you which values are right.",
        "The format follows the datasheet byte by byte: big-endian '>', then one unsigned byte (B), two bytes "
        "signed (h), and three unsigned bytes (B B B):\n"
        "    kind, centi, rh, battery, status = struct.unpack('>BhBBB', raw)\n"
        "With 'H' instead of 'h', a freezer at -18 °C reads +637 °C.",
    ],
    4: [
        "sensor.py already connects, loops and publishes: only NAME and reading() are yours. "
        "reading() returns a dictionary; the loop turns it into JSON with json.dumps().",
        "measured_at: datetime.now(timezone.utc).isoformat(timespec='seconds') — the imports are already there. "
        "Run python sensor.py and look at what it prints, then at the Packets tab.",
        "reading() can be:\n"
        "    return {'temperature_c': round(random.uniform(19, 23), 1),\n"
        "            'humidity_pct': random.randint(40, 55),\n"
        "            'measured_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}",
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
    7: [
        "Two separate things: a retained message on lab/sensors/<name>/status saying online, "
        "and a last will on the same topic saying offline, retained too.",
        "The last will is set BEFORE connect(): c.will_set(STATUS, 'offline', qos=1, retain=True). "
        "Right after connecting, publish 'online' with retain=True.",
        "To die abruptly, stop sensor.py with Ctrl+C: Python closes the socket without sending DISCONNECT. "
        "Then look at the Clients tab of the viewer, and at mosquitto_sub -t 'lab/sensors/+/status' -v.",
    ],
    8: [
        "Start your sensor with a short keepalive: KEEPALIVE_S = 15 in sensor.py. "
        "Then, in the viewer's Clients tab, press Freeze on its connection.",
        "Keep a subscriber on lab/sensors/+/status running and note the time: the broker waits a while "
        "before it declares the client gone and publishes the will. Compare that wait with the keepalive.",
        "The MQTT specification (3.1.1, section 3.1.2.10) says how long the broker waits: search for "
        "'one and a half times the Keep Alive'.",
    ],
    6: [
        "Start with PROBES and on_connect. The deviceName of each probe is in its events (viewer, click a payload); "
        "inventory.json says which FRZ1 is near the door. on_connect needs two client.subscribe(...): "
        "compressors/CMP1, and application/adour-coldchain/device/+/event/up.",
        "compressor(d): d['pressure_psi'] * PSI_TO_BAR, rounded to 3 decimals; d['timestamp'] is seconds since "
        "1970: datetime.fromtimestamp(d['timestamp'], timezone.utc).isoformat(). probe(event): "
        "decode(event['data'])['temperature_c'], and event['time'] is already ISO 8601 with its zone.",
        "The two conversions:\n"
        "    def compressor(d):\n"
        "        return {'pressure_bar': round(d['pressure_psi'] * PSI_TO_BAR, 3),\n"
        "                'measured_at': datetime.fromtimestamp(d['timestamp'], timezone.utc).isoformat()}\n"
        "    def probe(event):\n"
        "        frame = decode(event['data'])\n"
        "        return {'temperature_c': frame['temperature_c'], 'measured_at': event['time']}",
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
