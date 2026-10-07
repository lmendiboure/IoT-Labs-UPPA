"""The Adour Composites plant, Tarnos: the devices of the site, simulated.

Everything follows the plant's real rhythm, in local time (Europe/Paris):
two shifts on weekdays, 06:00-22:00; nights and weekends are quiet, but
not silent. The numbers are linked the way they are in a real plant: the
autoclave's cure cycle drives the curing sub-meter, which shows on the main
meter; every time someone opens the freezer, its probes warm up; the
compressor keeps running at night, because the air network leaks.

  hygrolab-gw     cleanroom sensors CR-01..03: one topic per quantity, bare values
  autoclave-ac1   autoclave controller: one JSON document every 5 s, cure cycles
  cnc1-adapter    CNC router adapter: state, spindle load, part counter; crashes now and then
  cmp1            screw compressor controller (a US unit: pressure in psi)
  modbus2mqtt     a Modbus-to-MQTT gateway reading two energy meters: raw registers
  chirpstack      LoRaWAN network server: the two freezer probes, 6-byte application payloads
  coldstore-ctrl  freezer door contact
  weather-roof    weather station on the roof
  mes             manufacturing execution system: site configuration, current orders

The models are functions of time, seeded: two VMs show the same plant at
the same moment. Read it if you like - but the data are the subject.
"""
import base64
import json
import math
import os
import random
import socket
import struct
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
SEED = 2026

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Paris")
except Exception:                                   # no time zone database: summer time
    TZ = timezone(timedelta(hours=2))


# ================================================================ time and noise
def local(t):
    return datetime.fromtimestamp(t, TZ)


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def minutes_of_day(t):
    d = local(t)
    return d.hour * 60 + d.minute + d.second / 60


def on_shift(t):
    d = local(t)
    return d.weekday() < 5 and 6 <= d.hour < 22


def day_start(t):
    d = local(t)
    return datetime(d.year, d.month, d.day, tzinfo=TZ).timestamp()


def wiggle(t, key, amp, period):
    """Smooth, deterministic noise: three sines with seeded phases."""
    r = random.Random(f"{SEED}-{key}")
    total = 0.0
    for k, f in enumerate((1.0, 2.7, 7.3)):
        total += math.sin(2 * math.pi * t / (period / f) + r.uniform(0, 2 * math.pi)) / (k + 1.5)
    return amp * total / 1.4


def jitter(key, t, amp):
    return random.Random(f"{SEED}-{key}-{int(t)}").uniform(-amp, amp)


def occupancy(t):
    """0 at night, 1 in the middle of a shift, soft edges."""
    m = minutes_of_day(t)
    if local(t).weekday() >= 5:
        return 0.0
    return max(0.0, min(1.0, (m - 350) / 20, (1330 - m) / 20))


# ================================================================ weather
def outdoor(t):
    doy = local(t).timetuple().tm_yday
    h = minutes_of_day(t) / 60
    mean = 14.5 + 6.0 * math.sin(2 * math.pi * (doy - 110) / 365)
    temp = mean + 4.0 * math.sin(2 * math.pi * (h - 9) / 24) + wiggle(t, "out-t", 1.2, 7200)
    rh = max(35, min(98, 78 - 2.6 * (temp - mean) + wiggle(t, "out-rh", 5, 5400)))
    wind = max(0.0, 3.5 + wiggle(t, "wind", 2.5, 1800) + jitter("gust", t // 10, 0.8))
    return temp, rh, wind


# ================================================================ cleanroom (layup room, ISO 8)
CLEANROOM = {"CR-01": 0.0, "CR-02": 0.25, "CR-03": -0.15}


def cleanroom(sensor, t):
    out_t, out_rh, _ = outdoor(t)
    occ = occupancy(t)
    temp = (20.0 + CLEANROOM[sensor] + 0.45 * occ + 0.05 * (out_t - 14)
            + wiggle(t, f"cr-t-{sensor}", 0.18, 2400))
    rh = 44 + 0.08 * (out_rh - 70) + 2.5 * occ + wiggle(t, f"cr-rh-{sensor}", 1.6, 3000)
    return temp, rh


# ================================================================ freezer (prepreg cold store, -18 °C)
def door_openings(t):
    """The freezer's door openings around time t: (start, duration in s)."""
    out = []
    for day_offset in (-1, 0):
        d0 = day_start(t) + day_offset * 86400
        d = local(d0 + 3600)
        if d.weekday() >= 5:
            continue
        r = random.Random(f"{SEED}-door-{d:%Y%m%d}")
        m = 6 * 60 + r.uniform(10, 40)
        while m < 21.5 * 60:
            out.append((d0 + m * 60, r.uniform(40, 170)))
            m += r.uniform(35, 95)
        if d.weekday() == 2:                          # every Wednesday: the door is left ajar
            out.append((d0 + (15 * 60 + 10) * 60, 11 * 60))
    return out


def freezer(probe, t):
    phase = (t % 1440) / 1440                         # the freezer's own cooling cycle, 24 min
    saw = 1 - 2 * phase / 0.6 if phase < 0.6 else -1 + 2 * (phase - 0.6) / 0.4
    temp = -18.0 + 1.4 * saw + wiggle(t, f"frz-{probe}", 0.15, 900)
    rate, tau = (0.9, 360) if probe == "T1" else (0.4, 540)       # T1 near the door, T2 at the back
    for start, dur in door_openings(t):
        if start <= t:
            open_for = min(t - start, dur)
            rise = rate * open_for / 60
            after = t - start - dur
            temp += rise if after <= 0 else rise * math.exp(-after / tau)
    return temp


def door_open(t):
    return any(start <= t < start + dur for start, dur in door_openings(t))


# ================================================================ autoclave AC-1
PHASES = [("LOADING", 20), ("LEAK_TEST", 10), ("HEATING", 78), ("DWELL", 120), ("COOLING", 40), ("UNLOADING", 15)]
CYCLE_MIN = sum(m for _, m in PHASES)
STARTS = [6 * 60 + 10, 10 * 60 + 55, 15 * 60 + 40]
PARTS = ["BRK-2231 bracket", "FRG-0417 fairing", "PNL-1180 access panel", "RIB-0902 rib", "CLP-3310 clip"]


def autoclave_cycle(t):
    """(start of the current or last cycle, index of the day) or None."""
    best = None
    for day_offset in (-1, 0):
        d0 = day_start(t) + day_offset * 86400
        if local(d0 + 3600).weekday() >= 5:
            continue
        for i, m in enumerate(STARTS):
            s = d0 + m * 60
            if s <= t:
                best = (s, i)
    return best


def autoclave(t):
    """Everything the controller knows at time t."""
    cyc = autoclave_cycle(t)
    ambient = 24.0 + wiggle(t, "ac-amb", 0.8, 3600)
    if cyc is None or t - cyc[0] >= CYCLE_MIN * 60 + 4 * 3600:
        return {"state": "IDLE", "air": ambient, "tc": [ambient] * 4, "pressure": 0.0, "vacuum": 0.0,
                "kw": 1.2 + jitter("ac-kw", t, 0.1), "batch": None, "recipe": None, "cycle": None}
    start, index = cyc
    elapsed = (t - start) / 60

    def air_at(minute):
        m = minute
        for name, dur in PHASES:
            if m < dur:
                break
            m -= dur
        else:
            return "IDLE", ambient + (42.0 - ambient) * math.exp(-m / 30), m
        if name in ("LOADING", "LEAK_TEST"):
            warm = 15.0 * math.exp(-minute / 12) if index > 0 else 0.0   # still warm from the last cycle
            return name, ambient + warm, m
        if name == "HEATING":
            return name, ambient + (180 - ambient) * m / dur, m
        if name == "DWELL":
            return name, 180.0 + wiggle(start + minute * 60, "ac-dwell", 0.6, 900), m
        if name == "COOLING":
            return name, 180.0 - 3.0 * m, m
        return name, 60 - 1.2 * m, m                      # UNLOADING

    state, air, in_phase = air_at(elapsed)
    if elapsed >= CYCLE_MIN:
        state = "IDLE"
    # part thermocouples lag behind the air: first-order lag, integrated from the cycle start
    taus = [8, 11, 14, 19]
    tcs = [ambient] * 4
    step = 0.25
    m = 0.0
    while m < min(elapsed, CYCLE_MIN + 240):
        _, a, _ = air_at(m)
        tcs = [x + (a - x) * step / tau for x, tau in zip(tcs, taus)]
        m += step
    heat_start = 30
    if state in ("HEATING", "DWELL"):
        pressure = min(7.0, 7.0 * (elapsed - heat_start) / 12) if state == "HEATING" else 7.0
    elif state == "COOLING":
        pressure = 7.0 if air > 80 else max(0.0, 7.0 * (1 - (80 - air) / 15))
    else:
        pressure = 0.0
    pressure = max(0.0, pressure + (wiggle(t, "ac-p", 0.03, 300) if pressure > 0 else 0))
    vacuum = -920 + wiggle(t, "ac-vac", 6, 600) if state in ("LEAK_TEST", "HEATING", "DWELL", "COOLING") else 0.0
    kw = {"LOADING": 1.5, "LEAK_TEST": 4.2, "HEATING": 118, "DWELL": 38, "COOLING": 9, "UNLOADING": 2,
          "IDLE": 1.2}[state]
    if state in ("HEATING", "DWELL"):
        kw += wiggle(t, "ac-kw-h", 5 if state == "DWELL" else 3, 240)
    d = local(start)
    batch = f"B{d:%y}{d.timetuple().tm_yday:03d}-{index + 1}"
    return {"state": state, "air": air, "tc": tcs, "pressure": pressure, "vacuum": vacuum,
            "kw": kw, "batch": batch, "recipe": "EP180-2H", "cycle": start,
            "part": PARTS[(d.timetuple().tm_yday * 3 + index) % len(PARTS)]}


# ================================================================ CNC router
def cnc_schedule(t):
    """The router's day: a list of (start, end, state), seeded by the date."""
    d0 = day_start(t)
    d = local(d0 + 3600)
    if d.weekday() >= 5:
        return [(d0, d0 + 86400, "OFF")]
    r = random.Random(f"{SEED}-cnc-{d:%Y%m%d}")
    out = [(d0, d0 + 6 * 3600 + 5 * 60, "OFF")]
    now = out[-1][1]
    end = d0 + 21 * 3600 + 50 * 60
    breaks = [(d0 + 9.5 * 3600, 15), (d0 + 12 * 3600, 30), (d0 + 14 * 3600, 15), (d0 + 18 * 3600, 20)]
    jobs = 0

    def add(state, minutes):
        nonlocal now
        out.append((now, now + minutes * 60, state))
        now += minutes * 60

    add("SETUP", r.uniform(12, 20))
    while now < end:
        for b, dur in breaks:
            if b <= now < b + 1800:
                add("IDLE", dur)
                breaks.remove((b, dur))
                break
        add("RUNNING", r.uniform(14, 42))
        jobs += 1
        if r.random() < 0.08:
            add("ALARM", r.uniform(3, 14))
        add("IDLE", r.uniform(1.5, 8))
        if jobs % 4 == 0:
            add("SETUP", r.uniform(10, 25))
    out.append((now, d0 + 86400, "OFF"))
    return out


def cnc(t):
    sched = cnc_schedule(t)
    parts = sum(1 for s, e, st in sched if st == "RUNNING" and e <= t)
    for s, e, st in sched:
        if s <= t < e:
            load = 0.0
            if st == "RUNNING":
                load = 55 + wiggle(t, "cnc-load", 18, 120) + jitter("cnc-j", t // 5, 6)
            kw = {"RUNNING": 4 + 0.16 * load, "IDLE": 2.4, "SETUP": 1.8, "ALARM": 1.2, "OFF": 0.1}[st]
            return {"state": st, "since": s, "load": max(0.0, load), "kw": kw, "parts": parts}
    return {"state": "OFF", "since": t, "load": 0.0, "kw": 0.1, "parts": parts}


# ================================================================ compressor (stateful)
class Compressor:
    """A 37 kW screw compressor with load/unload control, 6.5-7.5 bar."""

    def __init__(self):
        self.p, self.state, self.unloaded_since, self.hours = 7.0, "UNLOADED", time.time(), 18432.0
        self.lock = threading.Lock()

    def demand(self, t):
        leak = 0.9                                              # m³/min, day and night
        use = 0.0
        if cnc(t)["state"] == "RUNNING":
            use += 1.3
        use += 1.1 * occupancy(t) * (0.6 + 0.4 * math.sin(t / 97) ** 2)
        return leak + use + wiggle(t, "air", 0.15, 600)

    def step(self, t, dt):
        with self.lock:
            q_in = 5.8 if self.state == "LOADED" else 0.0
            self.p += (q_in - self.demand(t)) * 0.35 * dt / 60
            if self.state != "LOADED" and self.p < 6.5:
                self.state = "LOADED"
            elif self.state == "LOADED" and self.p >= 7.5:
                self.state, self.unloaded_since = "UNLOADED", t
            elif self.state == "UNLOADED" and t - self.unloaded_since > 600:
                self.state = "STOPPED"
            if self.state != "STOPPED":
                self.hours += dt / 3600

    def kw(self):
        return {"LOADED": 41.5, "UNLOADED": 13.2, "STOPPED": 0.0}[self.state]


compressor = Compressor()


# ================================================================ energy meters (stateful indexes)
class Meters:
    def __init__(self):
        t = time.time()
        self.index = {"main": 1_284_571.0 + (t - 1_790_000_000) / 3600 * 64,
                      "ac1": 212_904.0 + (t - 1_790_000_000) / 3600 * 21}
        self.last = t

    def power(self, t):
        out_t, _, _ = outdoor(t)
        occ = occupancy(t)
        freezer_kw = 3.8 if (t % 1440) / 1440 < 0.6 else 0.3
        hvac = 9 + 0.55 * abs(out_t - 18)
        base = 6.5 + 8 * occ + 6 * occ                      # IT and security; offices; lighting
        ac = autoclave(t)["kw"]
        main = base + hvac + freezer_kw + ac + cnc(t)["kw"] + compressor.kw() + jitter("em", t, 0.4)
        return main, ac + jitter("em-ac", t, 0.15)

    def step(self, t):
        main, ac = self.power(t)
        dt = t - self.last
        self.last = t
        self.index["main"] += main * dt / 3600
        self.index["ac1"] += ac * dt / 3600
        return main, ac


meters = Meters()


# ================================================================ MQTT plumbing
def client(client_id, keepalive=60, will=None, on_connect=None):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if will:
        c.will_set(*will)
    if on_connect:
        c.on_connect = on_connect
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
            except Exception as e:                         # one device must never take the plant down
                print(f"{fn.__name__}: {e!r}, restarting", flush=True)
                time.sleep(3)
    threading.Thread(target=run, name=fn.__name__, daemon=True).start()


def every(period, offset=0.0):
    """Sleep until the next multiple of `period` (+ offset): devices keep their rhythm."""
    now = time.time()
    time.sleep(period - ((now - offset) % period))
    return time.time()


# ================================================================ devices
def hygrolab():
    c = client("hygrolab-gw")
    while True:
        t = every(10)
        for sensor in CLEANROOM:
            temp, rh = cleanroom(sensor, t)
            c.publish(f"hygrolab/{sensor}/temperature", f"{temp:.2f}")
            c.publish(f"hygrolab/{sensor}/humidity", f"{rh:.1f}")


def autoclave_ac1():
    c = client("autoclave-ac1")
    while True:
        t = every(5, 1)
        a = autoclave(t)
        doc = {"Timestamp": iso(t), "State": a["state"], "Recipe": a["recipe"], "Batch": a["batch"],
               "AirTemp": round(a["air"], 1), "PartTC": [round(x, 1) for x in a["tc"]],
               "Pressure": round(a["pressure"], 2), "Vacuum": round(a["vacuum"]), "Units": "C/bar/mbar"}
        c.publish("Autoclave1/Data", json.dumps(doc))


def cnc1_adapter():
    avail = "cnc/router1/availability"
    while True:
        c = client("cnc1-adapter", keepalive=30, will=(avail, "UNAVAILABLE", 1, True))
        c.publish(avail, "AVAILABLE", qos=1, retain=True)
        last_state, last_parts = None, None
        crash_at = time.time() + random.uniform(300, 480)     # the adapter's PC is not the most stable
        while time.time() < crash_at:
            t = every(5, 2)
            s = cnc(t)
            if s["state"] != last_state:
                c.publish("cnc/router1/state", s["state"], qos=1, retain=True)
                last_state = s["state"]
            if s["parts"] != last_parts:
                c.publish("cnc/router1/part_count", str(s["parts"]), qos=1, retain=True)
                last_parts = s["parts"]
            c.publish("cnc/router1/spindle_load", f"{s['load']:.0f}")
        c.loop_stop()
        sock = c.socket()
        if sock is not None:                                  # gone without a word
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        time.sleep(40)


def cmp1():
    c = client("cmp1")
    last = time.time()
    n = 0
    while True:
        time.sleep(1)
        t = time.time()
        compressor.step(t, t - last)
        last = t
        n += 1
        if n % 10 == 0:
            doc = {"unit": "CMP-1", "state": compressor.state,
                   "pressure_psi": round(compressor.p * 14.5038 + jitter("psi", t, 0.3), 1),
                   "motor_hours": round(compressor.hours, 1), "timestamp": int(t)}
            c.publish("compressors/CMP1", json.dumps(doc))


def modbus2mqtt():
    c = client("modbus2mqtt")
    while True:
        t = every(10, 3)
        main, ac = meters.step(t)
        c.publish("modbus2mqtt/meter_main/reg/3059", f"{main:.2f}")
        c.publish("modbus2mqtt/meter_main/reg/2699", f"{meters.index['main']:.1f}")
        c.publish("modbus2mqtt/meter_ac1/reg/3059", f"{ac:.2f}")
        c.publish("modbus2mqtt/meter_ac1/reg/2699", f"{meters.index['ac1']:.1f}")


PROBES = {"T1": ("70b3d57ed0058a21", "frz1-probe-door"), "T2": ("70b3d57ed0058a37", "frz1-probe-back")}
GATEWAYS = ["7276ff002e0a1b01", "7276ff002e0a1b02"]


def frame(temp_c, rh, battery, status=0):
    return struct.pack(">BhBBB", 0x11, int(round(temp_c * 100)), int(rh), battery, status)


def chirpstack():
    c = client("chirpstack")
    fcnt = {p: random.Random(f"{SEED}-fcnt-{p}").randint(2000, 9000) + int(time.time() // 60) % 10000
            for p in PROBES}
    r = random.Random()
    attempts = {p: 0 for p in PROBES}
    while True:
        for probe, (eui, name) in PROBES.items():
            t = every(60, 7 if probe == "T1" else 37)
            attempts[probe] += 1
            fcnt[probe] += 1
            # Teaching fault: deliberately suppress every fourth uplink so an fCnt gap is
            # observable during the session. The 25% rate is intentionally unrealistic.
            if attempts[probe] % 4 == 0:
                continue
            heard = r.sample(GATEWAYS, r.choice([1, 1, 2]))
            batt = 87 if probe == "T1" else 64
            event = {
                "deduplicationId": str(uuid.uuid4()),
                "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "deviceInfo": {"tenantId": "0e2cb8d4-51f2-4b8e-9a4c-3c1f0a7d2e91", "tenantName": "Adour Composites",
                               "applicationId": "6f1b9c2e-7a44-4d0b-8e3f-5b2a9d1c4e77",
                               "applicationName": "adour-coldchain", "deviceProfileName": "Cold-chain probe v2",
                               "deviceName": name, "devEui": eui, "tags": {"area": "coldstore"}},
                "devAddr": "260b" + eui[-4:], "adr": True, "dr": 5, "fCnt": fcnt[probe], "fPort": 2,
                "confirmed": False,
                "data": base64.b64encode(frame(freezer(probe, t), 28 + r.randint(0, 6), batt)).decode(),
                "rxInfo": [{"gatewayId": g, "uplinkId": r.randint(1, 65000), "rssi": r.randint(-112, -86),
                            "snr": round(r.uniform(-6, 9), 1), "channel": r.randint(0, 7),
                            "location": {}, "context": "AAAAAA==", "crcStatus": "CRC_OK"} for g in heard],
                "txInfo": {"frequency": r.choice([868100000, 868300000, 868500000]),
                           "modulation": {"lora": {"bandwidth": 125000, "spreadingFactor": 7,
                                                   "codeRate": "CR_4_5"}}},
            }
            c.publish(f"application/adour-coldchain/device/{eui}/event/up", json.dumps(event))


def coldstore_ctrl():
    c = client("coldstore-ctrl")
    last = None
    while True:
        t = every(2)
        state = "open" if door_open(t) else "closed"
        if state != last:
            c.publish("/adour/coldstore/freezer1/door", state, qos=1, retain=True)
            last = state


def weather_roof():
    c = client("weather-roof")
    while True:
        t = every(60, 11)
        temp, rh, wind = outdoor(t)
        c.publish("weather/roof", json.dumps({"temp_c": round(temp, 1), "rh": round(rh), "wind_ms": round(wind, 1),
                                               "ts": int(t)}))


def mes():
    config = {"company": "Adour Composites", "site": "Tarnos", "timezone": "Europe/Paris",
              "shifts": [{"name": "morning", "from": "06:00", "to": "14:00"},
                         {"name": "afternoon", "from": "14:00", "to": "22:00"}],
              "areas": ["coldstore", "cleanroom", "curing", "machining", "utilities"]}
    while True:
        t = time.time()
        c = client("mes")
        config["updated"] = iso(t)
        c.publish("mes/site/config", json.dumps(config), qos=1, retain=True).wait_for_publish(10)
        a = autoclave(t)
        order = ({"workcenter": "AC-1", "order": f"OF-{a['batch']}", "part": a["part"],
                  "recipe": a["recipe"], "quantity": 12, "status": "IN_PROGRESS"}
                 if a["state"] != "IDLE" else {"workcenter": "AC-1", "status": "NO_ORDER"})
        c.publish("mes/orders/AC-1", json.dumps(order), qos=1, retain=True).wait_for_publish(10)
        c.disconnect()                                     # a polite client says goodbye
        c.loop_stop()
        time.sleep(600)


if __name__ == "__main__":
    print(f"plant: Adour Composites, Tarnos, publishing through {HOST}:{PORT}", flush=True)
    for fn in (hygrolab, autoclave_ac1, cnc1_adapter, cmp1, modbus2mqtt, chirpstack, coldstore_ctrl,
               weather_roof, mes):
        forever(fn)
    while True:
        time.sleep(3600)
