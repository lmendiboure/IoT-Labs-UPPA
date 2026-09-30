"""The Adour building: a handful of devices that publish, each in its vendor's way.

  thermaline-gw   Thermaline gateway: one topic per room and per quantity, plain values
  KL-7F3A         Klimo sensor, JSON in °F, timestamps in ms; drops off now and then
  KL-1EEC         Klimo sensor, same, stable
  chirpstack-ns   LoRaWAN network server: one event per water meter uplink
  door-ctrl       entrance door contact, retained, QoS 1
  bms             building management system: the building's configuration, retained

Every device connects through the relay, so the viewer sees all of them.
"""
import base64
import json
import os
import random
import socket
import struct
import threading
import time
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
SPEED = float(os.getenv("BUILDING_SPEED", "1"))      # tests only: > 1 makes everything faster
rng = random.Random(2026)


def pause(s):
    time.sleep(s / SPEED)


def iso(t=None):
    return datetime.fromtimestamp(t or time.time(), timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def client(client_id, keepalive=60, will=None):
    """A connected client that keeps trying until the relay answers."""
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if will:
        c.will_set(*will)
    c.reconnect_delay_set(1, 10)
    while True:
        try:
            c.connect(HOST, PORT, keepalive=keepalive)
            break
        except OSError:
            time.sleep(2)
    c.loop_start()
    return c


def forever(fn):
    def run():
        while True:
            try:
                fn()
            except Exception as e:                    # a device must never take the building down
                print(f"{fn.__name__}: {e!r}, restarting", flush=True)
                time.sleep(3)
    threading.Thread(target=run, name=fn.__name__, daemon=True).start()


# ---------------------------------------------------------------- Thermaline
ROOMS = {"A101": 21.0, "A102": 20.2, "A201": 22.1}


def thermaline():
    c = client("thermaline-gw")
    state = {r: {"t": t, "rh": 45.0, "co2": 520.0} for r, t in ROOMS.items()}
    while True:
        for room, s in state.items():
            s["t"] += rng.uniform(-0.15, 0.15)
            s["rh"] = min(70, max(30, s["rh"] + rng.uniform(-0.8, 0.8)))
            s["co2"] = min(1600, max(420, s["co2"] + rng.uniform(-40, 45)))
            c.publish(f"thermaline/{room}/temperature", f"{s['t']:.1f}")
            c.publish(f"thermaline/{room}/humidity", f"{s['rh']:.0f}")
            c.publish(f"thermaline/{room}/co2", f"{s['co2']:.0f}")
            pause(10 / len(state))


# ---------------------------------------------------------------- Klimo
def klimo(sensor_id, flaky):
    status = f"klimo/{sensor_id}/status"
    temp_f = rng.uniform(68, 73)
    while True:
        c = client(sensor_id, keepalive=30, will=(status, "offline", 1, True))
        c.publish(status, "online", qos=1, retain=True)
        up_until = time.time() + (240 if flaky else 10 ** 9) / SPEED
        while time.time() < up_until:
            temp_f += rng.uniform(-0.3, 0.3)
            reading = {"sensorId": sensor_id, "temp": round(temp_f, 1), "rh": rng.randint(40, 50),
                       "co2": rng.randint(450, 900), "ts": int(time.time() * 1000)}
            c.publish(f"klimo/{sensor_id}/data", json.dumps(reading))
            pause(15)
        # the battery connector is loose: the sensor vanishes without a word
        c.loop_stop()
        sock = c.socket()
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        pause(45)


def klimo_7f3a():
    klimo("KL-7F3A", flaky=True)


def klimo_1eec():
    klimo("KL-1EEC", flaky=False)


# ---------------------------------------------------------------- LoRaWAN network server
METERS = {"70b3d57ed0012a4f": ("meter-017", 184_220), "70b3d57ed00f1c4c": ("meter-001", 96_310)}
GATEWAYS = ["b827ebfffe6c3a11", "b827ebfffe6c3a22"]


def frame(index_l, temp_c, battery_pct, period_min):
    return struct.pack(">BIhBH", 1 << 4, index_l, int(round(temp_c * 100)), battery_pct, period_min)


def chirpstack():
    c = client("chirpstack-ns")
    index = {eui: v[1] for eui, v in METERS.items()}
    fcnt = {eui: rng.randint(100, 900) for eui in METERS}
    while True:
        for eui, (name, _) in METERS.items():
            index[eui] += rng.randint(2, 40)
            fcnt[eui] += 1
            heard = rng.sample(GATEWAYS, rng.choice([1, 2]))
            event = {
                "deduplicationId": str(uuid.UUID(int=rng.getrandbits(128))),
                "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "deviceInfo": {"tenantId": "52f14cd4-c6f1-4fbd-8f87-4025e1d49242", "tenantName": "UPPA",
                               "applicationId": "d6c9e2c1-8f5e-4b53-9a1e-2f4f7c1a9b3d",
                               "applicationName": "adour-meters", "deviceProfileName": "Aquanet LW-10",
                               "deviceName": name, "devEui": eui},
                "devAddr": "00" + eui[-6:], "adr": True, "dr": 5, "fCnt": fcnt[eui], "fPort": 2,
                "confirmed": False,
                "data": base64.b64encode(frame(index[eui], rng.uniform(12, 16), rng.randint(60, 95), 60)).decode(),
                "rxInfo": [{"gatewayId": g, "uplinkId": rng.randint(1, 60000), "rssi": rng.randint(-118, -90),
                            "snr": round(rng.uniform(-8, 9), 1), "channel": rng.randint(0, 7),
                            "location": {}, "context": "AAAAAA==", "crcStatus": "CRC_OK"} for g in heard],
                "txInfo": {"frequency": rng.choice([868100000, 868300000, 868500000]),
                           "modulation": {"lora": {"bandwidth": 125000, "spreadingFactor": 7,
                                                   "codeRate": "CR_4_5"}}},
            }
            c.publish(f"application/adour-meters/device/{eui}/event/up", json.dumps(event))
            pause(30)


# ---------------------------------------------------------------- door
def door():
    c = client("door-ctrl")
    state = "closed"
    while True:
        state = "open" if state == "closed" else "closed"
        c.publish("/adour/a/door3", state, qos=1, retain=True)
        pause(rng.uniform(20, 60))


# ---------------------------------------------------------------- building management system
def bms():
    config = {"site": "Adour", "building": "A", "floors": 3, "timezone": "Europe/Paris",
              "contact": "facilities@example.org", "updated": None}
    while True:
        c = client("bms")
        config["updated"] = iso()
        c.publish("adour/building-a/config", json.dumps(config), qos=1, retain=True).wait_for_publish(10)
        c.disconnect()                                 # a polite client says goodbye
        c.loop_stop()
        pause(600)


if __name__ == "__main__":
    print(f"building: publishing through {HOST}:{PORT}", flush=True)
    for fn in (thermaline, klimo_7f3a, klimo_1eec, chirpstack, door, bms):
        forever(fn)
    while True:
        time.sleep(3600)
