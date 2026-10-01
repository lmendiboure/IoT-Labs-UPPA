#!/usr/bin/env python3
"""check — tells you whether each exercise of Lab 1 is done.

    check            every exercise
    check 4          exercise 4 only
    check report     writes report-lab1.txt, the file you hand in

It reads what the relay saw (every MQTT packet of the lab goes through it)
and the files you write in /work. Nothing here changes your work.
"""
import base64
import json
import os
import statistics
import struct
import sys
import time
import urllib.request
from datetime import datetime

VIEWER = os.getenv("VIEWER", "http://relay:8080")
HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
WORK = os.getenv("WORK", "/work")
RECORD = os.getenv("RECORD", "/record")
LAB = os.path.dirname(os.path.realpath(__file__))
STATE = os.path.join(WORK, ".checks.json")
PLANT = {"hygrolab-gw", "autoclave-ac1", "cnc1-adapter", "cmp1", "modbus2mqtt", "chirpstack",
         "coldstore-ctrl", "weather-roof", "mes"}
OK, NO, INFO = "✔", "✘", "·"

TITLES = {
    1: "The lab is running",
    2: "A subscription and a message by hand",
    3: "Take a message apart",
    4: "Your virtual sensor",
    5: "A namespace for the plant",
    6: "Bridge two devices into your namespace",
    7: "A status and a last will",
    8: "A link that dies in silence",
}
CORE, DEEPER = [1, 2, 3, 4, 5, 6, 7, 8], []


# ---------------------------------------------------------------- helpers
def api(path):
    if path == "/api/packets":
        path += "?limit=1000000"                 # the whole history, not the viewer's last 1000
    with urllib.request.urlopen(VIEWER + path, timeout=10) as r:
        return json.loads(r.read())


def mine(client_id):
    """A client of yours: not the plant, not this checker."""
    return bool(client_id) and client_id not in PLANT and not client_id.startswith("checker-")


def load(name):
    path = os.path.join(WORK, name)
    if not os.path.exists(path):
        raise Check(f"{name} not found in /work")
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise Check(f"{name} is not valid JSON: {e.msg} at line {e.lineno}, column {e.colno}")


try:                                     # the plant's clock, whatever the container's
    from zoneinfo import ZoneInfo
    PLANT_TZ = ZoneInfo(os.getenv("PLANT_TZ", "Europe/Paris"))
except Exception:
    PLANT_TZ = None


def hhmm(t):
    return datetime.fromtimestamp(t, PLANT_TZ).strftime("%H:%M:%S")


def topic_matches(filt, topic):
    """MQTT topic filter matching, as a broker does it."""
    f, t = filt.split("/"), topic.split("/")
    for i, level in enumerate(f):
        if level == "#":
            return True
        if i >= len(t):
            return False
        if level != "+" and level != t[i]:
            return False
    return len(f) == len(t)


def valid_filter(filt):
    levels = filt.split("/")
    for i, level in enumerate(levels):
        if "#" in level and (level != "#" or i != len(levels) - 1):
            return "'#' must be a whole level, and the last one"
        if "+" in level and level != "+":
            return "'+' must be a whole level"
    return None


class Check(Exception):
    pass


# ---------------------------------------------------------------- exercises
def ex1(out):
    try:
        packets = api("/api/packets")
    except OSError as e:
        raise Check(f"the viewer does not answer at {VIEWER} ({e}). Is the relay running? "
                    "On the VM: docker compose ps")
    out.append((OK, f"the relay answers at {VIEWER}"))
    recent = {p["client"] for p in packets if p["t"] > time.time() - 90 and p["type"] == "PUBLISH"}
    seen = sorted(recent & PLANT)
    if len(seen) < 5:
        raise Check("the plant is silent (fewer than 5 of its devices published in the last 90 s). "
                    "On the VM: docker compose logs plant")
    out.append((OK, f"the plant is talking: {', '.join(seen)}"))
    import paho.mqtt.client as mqtt
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"checker-{os.getpid()}")
    try:
        c.connect(HOST, PORT, keepalive=10)
        c.disconnect()
    except OSError as e:
        raise Check(f"cannot connect to MQTT at {HOST}:{PORT} ({e})")
    out.append((OK, f"MQTT answers at {HOST}:{PORT}"))


def ex2(out):
    packets = api("/api/packets")
    pubs = [p for p in packets if p["type"] == "PUBLISH" and p["dir"] == "up" and mine(p["client"])
            and (p["topic"] or "").startswith("lab/")]
    if not pubs:
        raise Check("no message of yours on a topic starting with lab/ yet (mosquitto_pub, exercise 2)")
    p = pubs[-1]
    out.append((OK, f"you published on {p['topic']} (client {p['client']}, {hhmm(p['t'])})"))
    subs = [p for p in packets if p["type"] == "SUBSCRIBE" and mine(p["client"])
            and any(w in (p["topic"] or "") for w in "+#")]
    if not subs:
        raise Check("no subscription of yours with a wildcard (+ or #) yet (mosquitto_sub, exercise 2)")
    p = subs[-1]
    out.append((OK, f"you subscribed to {p['topic']} (client {p['client']})"))


def ex3(out):
    m = load("measurements.json")
    packets = api("/api/packets")
    pubs = [p for p in packets if p["type"] == "PUBLISH" and p["dir"] == "up"]
    cr = [p for p in pubs if p["topic"] == "hygrolab/CR-01/temperature"]
    cs = [p for p in pubs if (p["topic"] or "").startswith("application/adour-coldchain/")]
    if not cr or not cs:
        raise Check("the relay has not seen enough of the plant yet: wait a minute")
    wrong = []

    def number(key):
        v = m.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            wrong.append(f"{key}: missing or not a number")
            return None
        return v

    def expect(key, ok, hint):
        v = number(key)
        if v is None:
            return
        if ok(v):
            out.append((OK, f"{key} = {v}"))
        else:
            wrong.append(f"{key} = {v}: {hint}")

    expect("cleanroom_topic_bytes", lambda v: v == len("hygrolab/CR-01/temperature"),
           "count the characters of the topic itself")
    sizes = {p["size"] for p in cr}
    expect("cleanroom_packet_bytes", lambda v: v in sizes,
           "not the size of the whole PUBLISH packet for that topic (viewer, packet B)")
    lo, hi = min(p["payload_size"] for p in cs), max(p["payload_size"] for p in cs)
    expect("chirpstack_payload_bytes", lambda v: lo * 0.95 <= v <= hi * 1.05,
           "not the payload size of a ChirpStack event")
    expect("probe_payload_bytes", lambda v: v == 6,
           "decode the base64 'data' field and count the bytes")
    v = number("probe_temperature_c")
    if v is not None:
        orig = originals(packets)
        recent = {d: [o[1] for o in orig[d] if o[0] >= time.time() - 900] for d in ("FRZ1-T1", "FRZ1-T2")}
        if not recent["FRZ1-T1"]:
            wrong.append("probe_temperature_c: no uplink of FRZ1-T1 in the last 15 minutes yet: wait a minute")
        elif any(abs(v - x) < 0.006 for x in recent["FRZ1-T1"]):
            out.append((OK, f"probe_temperature_c = {v}: FRZ1-T1 did send that"))
        else:
            why = "not a temperature FRZ1-T1 sent in the last 15 minutes"
            if any(abs(v - x) < 0.006 for x in recent["FRZ1-T2"]):
                why = "that is FRZ1-T2, the probe at the back; FRZ1-T1 is near the door"
            elif any(abs(v - x * 100) < 1 for x in recent["FRZ1-T1"]):
                why = "right bytes, but the unit is hundredths of a degree"
            elif any(min(abs(v - (x * 100 + 65536)), abs(v - (x + 655.36))) < 0.1 for x in recent["FRZ1-T1"]):
                why = "the temperature is a signed number"
            wrong.append(f"probe_temperature_c = {v}: {why}")
    if wrong:
        raise Check("; ".join(wrong))


def ex4(out):
    conns = api("/api/connections")
    sensors = [c for c in conns if (c["client_id"] or "").startswith("sensor-")]
    if not sensors:
        raise Check("no client whose id starts with sensor- has connected yet")
    packets = api("/api/packets")
    since = time.time() - 900
    by_topic = {}
    for p in packets:
        if (p["type"] == "PUBLISH" and p["dir"] == "up" and p["t"] >= since
                and (p["client"] or "").startswith("sensor-")):
            by_topic.setdefault((p["client"], p["topic"]), []).append(p)
    good = {k: v for k, v in by_topic.items()
            if (k[1] or "").startswith("lab/sensors/") and k[1].endswith("/env") and k[1].count("/") == 3}
    if not good:
        topics = ", ".join(sorted({k[1] for k in by_topic})) or "none"
        raise Check(f"no message on lab/sensors/<name>/env in the last 15 minutes (your topics: {topics})")
    (client, topic), msgs = max(good.items(), key=lambda kv: len(kv[1]))
    out.append((OK, f"{client} publishes on {topic}"))
    if len(msgs) < 10:
        raise Check(f"{len(msgs)} messages in the last 15 minutes, 10 needed: let it run")
    problems = []
    for p in msgs[-10:]:
        try:
            d = json.loads(p["payload"])
        except (TypeError, json.JSONDecodeError):
            problems.append(f"not JSON: {p['payload'][:60]}")
            continue
        for key in ("temperature_c", "humidity_pct"):
            if not isinstance(d.get(key), (int, float)):
                problems.append(f"{key} missing or not a number")
        try:
            datetime.fromisoformat(str(d.get("measured_at")).replace("Z", "+00:00"))
        except ValueError:
            problems.append("measured_at missing or not an ISO 8601 date")
    if problems:
        raise Check("; ".join(sorted(set(problems))))
    out.append((OK, "payload: JSON with temperature_c, humidity_pct and measured_at"))
    gaps = [b["t"] - a["t"] for a, b in zip(msgs, msgs[1:])]
    period = statistics.median(gaps)
    if not 2 <= period <= 10:
        raise Check(f"one message every {period:.1f} s: choose a period between 2 and 10 s")
    out.append((OK, f"one message every {period:.1f} s"))


def ex5(out):
    inventory = json.load(open(os.path.join(LAB, "inventory.json")))
    devices = {d["id"]: d for d in inventory["devices"]}
    needs = inventory["needs"]
    tree = load("tree.json")
    subs = load("subscriptions.json")
    problems = []
    missing = sorted(set(devices) - set(tree))
    if missing:
        problems.append(f"no topic for {', '.join(missing)}")
    extra = sorted(set(tree) - set(devices))
    if extra:
        problems.append(f"unknown devices in tree.json: {', '.join(extra)}")
    seen = {}
    for dev, topic in tree.items():
        if not isinstance(topic, str) or not topic:
            problems.append(f"{dev}: the topic must be a non-empty string")
            continue
        why = None
        if any(ch in topic for ch in "+#"):
            why = "wildcards belong in subscriptions, not in topics"
        elif topic.startswith("/") or topic.endswith("/") or "//" in topic:
            why = "no leading or trailing '/', no empty level"
        elif topic.startswith("$"):
            why = "topics starting with $ are reserved for the broker"
        elif any(ch.isspace() for ch in topic):
            why = "no spaces"
        elif not topic.isascii():
            why = "stay with plain ASCII"
        elif topic.count("/") > 7:
            why = "more than 8 levels: keep it readable"
        if why:
            problems.append(f"{dev} -> {topic}: {why}")
        if topic in seen:
            problems.append(f"{dev} and {seen[topic]} share the topic {topic}")
        seen[topic] = dev
    if problems:
        raise Check("; ".join(problems))
    out.append((OK, f"{len(tree)} devices, one valid topic each"))
    for need in needs:
        filters = subs.get(need["id"])
        if not isinstance(filters, list) or not filters:
            problems.append(f"{need['id']}: no filter")
            continue
        if len(filters) > 2:
            problems.append(f"{need['id']}: {len(filters)} filters, 2 at most — your tree should make this easy")
            continue
        bad = [f"{f} ({valid_filter(f)})" for f in filters if valid_filter(f)]
        if bad:
            problems.append(f"{need['id']}: invalid filter {', '.join(bad)}")
            continue
        got = {dev for dev, topic in tree.items() if any(topic_matches(f, topic) for f in filters)}
        want = set(need["devices"])
        if got == want:
            out.append((OK, f"{need['id']} ({need['text']}): {', '.join(filters)}"))
        else:
            parts = []
            if want - got:
                parts.append(f"misses {', '.join(sorted(want - got))}")
            if got - want:
                parts.append(f"also catches {', '.join(sorted(got - want))}")
            problems.append(f"{need['id']} ({need['text']}): {' and '.join(parts)}")
    if problems:
        raise Check("; ".join(problems))


def ex_status(out):
    import paho.mqtt.client as mqtt
    retained = {}

    def on_message(c, u, msg):
        if msg.retain:
            retained[msg.topic] = msg.payload.decode("utf-8", "replace")

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"checker-{os.getpid()}")
    c.on_message = on_message
    c.connect(HOST, PORT, keepalive=10)
    c.subscribe("lab/sensors/+/status", qos=1)
    c.loop_start()
    time.sleep(2)
    c.disconnect()
    c.loop_stop()
    if not retained:
        raise Check("no retained message on lab/sensors/<name>/status")
    topic, value = sorted(retained.items())[0]
    if value not in ("online", "offline"):
        raise Check(f"{topic} holds '{value}': the status should be online or offline")
    out.append((OK, f"retained on {topic}: {value}"))
    conns = api("/api/connections")
    willing = [x for x in conns if (x["client_id"] or "").startswith("sensor-") and x["will"]
               and x["will"]["topic"].startswith("lab/sensors/") and x["will"]["topic"].endswith("/status")]
    if not willing:
        raise Check("none of your sensor- clients connected with a last will on lab/sensors/<name>/status")
    w = willing[-1]["will"]
    if w["payload"] != "offline" or not w["retain"]:
        raise Check(f"your last will publishes '{w['payload']}'{' retained' if w['retain'] else ' not retained'}: "
                    "it should publish offline, retained")
    out.append((OK, f"{willing[-1]['client_id']} has a last will: {w['topic']} <- offline, retained"))
    died = [x for x in willing if x["end"] and x["end"].startswith("abrupt")]
    if not died:
        raise Check("none of them has died abruptly yet: stop your sensor without disconnect() (Ctrl+C)")
    out.append((OK, f"{died[-1]['client_id']} died abruptly at {hhmm(died[-1]['closed'])}"))


def ex_freeze(out):
    conns = api("/api/connections")
    frozen = [x for x in conns if (x["client_id"] or "").startswith("sensor-") and x["end"]
              and x["end"].startswith("frozen")]
    if not frozen:
        pending = [x for x in conns if (x["client_id"] or "").startswith("sensor-") and x["frozen_at"]
                   and not x["closed"]]
        if pending:
            raise Check(f"{pending[-1]['client_id']} is frozen, the broker has not given up yet: wait")
        raise Check("no frozen connection of a sensor- client yet (viewer, Clients tab, Freeze)")
    x = frozen[-1]
    if (x["keepalive"] or 0) > 30:
        raise Check(f"{x['client_id']} had a keepalive of {x['keepalive']} s: use 30 s or less, "
                    "so that you do not wait too long")
    out.append((OK, f"{x['client_id']} (keepalive {x['keepalive']} s): {x['end']}"))


PSI_TO_BAR = 0.0689476
PROBES = {"70b3d57ed0058a21": "FRZ1-T1", "70b3d57ed0058a37": "FRZ1-T2"}
BRIDGED = [  # (devices, key the bridge must publish, tolerance, unit, where the plant publishes it)
    (["CMP-1"], "pressure_bar", 0.011, "bar", "compressors/CMP1"),
    (["FRZ1-T1", "FRZ1-T2"], "temperature_c", 0.051, "°C", "application/adour-coldchain/.../event/up"),
]


def originals(packets):
    """What the plant itself published, decoded: {device: [(relay time, value, device time), ...]}."""
    got = {"CR-01": [], "CMP-1": [], "FRZ1-T1": [], "FRZ1-T2": []}
    for p in packets:
        if p["type"] != "PUBLISH" or p["dir"] != "up" or p["client"] not in PLANT:
            continue
        topic, payload = p["topic"] or "", p["payload"] or ""
        try:
            if topic == "hygrolab/CR-01/temperature":
                got["CR-01"].append((p["t"], float(payload), p["t"]))
            elif topic == "compressors/CMP1":
                d = json.loads(payload)
                got["CMP-1"].append((p["t"], d["pressure_psi"] * PSI_TO_BAR, float(d["timestamp"])))
            elif topic.startswith("application/adour-coldchain/device/") and topic.split("/")[3] in PROBES:
                d = json.loads(payload)
                centi = struct.unpack(">BhBBB", base64.b64decode(d["data"]))[1]
                when = datetime.fromisoformat(d["time"].replace("Z", "+00:00")).timestamp()
                got[PROBES[topic.split("/")[3]]].append((p["t"], centi / 100, when))
        except (ValueError, KeyError, TypeError, IndexError, struct.error):
            pass
    return got


def ex_bridge(out):
    tree = load("tree.json")
    missing = [d for devs, *_ in BRIDGED for d in devs if not isinstance(tree.get(d), str)]
    if missing:
        raise Check(f"tree.json has no topic for {', '.join(missing)}: the bridge publishes on the "
                    "topics of your namespace (exercise 5)")
    packets = api("/api/packets")
    orig = originals(packets)
    since = time.time() - 900
    problems = []
    for devs, key, tol, unit, source in BRIDGED:
        msgs = []
        for p in packets:
            if (p["type"] == "PUBLISH" and p["dir"] == "up" and p["t"] >= since and mine(p["client"])
                    and p["topic"] in [tree[d] for d in devs]):
                try:
                    d = json.loads(p["payload"])
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(d, dict) and key in d:
                    msgs.append((p, d))
        if not msgs:
            where = " or ".join(tree[d] for d in devs)
            problems.append(f"{' / '.join(devs)}: no JSON message of yours with a {key} field on {where} "
                            "in the last 15 minutes")
            continue
        p, d = msgs[-1]
        dev = next(x for x in devs if tree[x] == p["topic"])
        v = d[key]
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            problems.append(f"{dev}: {key} = {v!r} is not a number")
            continue
        window = [o for o in orig[dev] if p["t"] - 90 <= o[0] <= p["t"] + 1]
        match = min(window, key=lambda o: abs(o[1] - v), default=None)
        if match is None:
            problems.append(f"{dev}: the relay saw nothing from the plant on {source} in the 90 s before "
                            "your message: is the plant running?")
            continue
        if abs(match[1] - v) > tol:
            def near(f, eps):
                return any(abs(v - f(o[1])) < eps for o in window)
            why = f"{dev}: {key} = {v}, but the plant said {window[-1][1]:.2f} {unit} just before"
            if key == "pressure_bar" and near(lambda x: x / PSI_TO_BAR, 0.2):
                why += " — that is still psi"
            elif dev.startswith("FRZ") and near(lambda x: x * 100, 1):
                why += " — divide the raw number by 100"
            elif dev.startswith("FRZ") and (near(lambda x: x * 100 + 65536, 1)
                                            or near(lambda x: x + 655.36, 0.02)):
                why += " — the temperature is a signed number"
            problems.append(why)
            continue
        try:
            when = datetime.fromisoformat(str(d.get("measured_at")).replace("Z", "+00:00"))
        except ValueError:
            problems.append(f"{dev}: measured_at missing or not an ISO 8601 date")
            continue
        if when.tzinfo is None:
            problems.append(f"{dev}: measured_at = {d['measured_at']} has no time zone: say it is UTC")
            continue
        gap = when.timestamp() - match[2]
        if abs(gap) > 60:
            problems.append(f"{dev}: measured_at is {gap:+.0f} s away from when the device measured: "
                            "check its time zone, or use the device's own time when it gives one")
            continue
        out.append((OK, f"{dev} -> {p['topic']}: {key} {v} (the plant: {match[1]:.2f} {unit}), "
                        f"by {p['client']}"))
    if problems:
        raise Check("; ".join(problems))


EXERCISES = {1: ex1, 2: ex2, 3: ex3, 4: ex4, 5: ex5, 6: ex_bridge, 7: ex_status, 8: ex_freeze}


# ---------------------------------------------------------------- running
def state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def run(n, quiet=False):
    out = []
    try:
        EXERCISES[n](out)
        ok, why = True, None
    except Check as e:
        ok, why = False, str(e)
    except OSError as e:
        ok, why = False, f"cannot reach the lab: {e}"
    if not quiet:
        print(f"\nExercise {n} — {TITLES[n]}{'  (◆ deeper)' if n in DEEPER else ''}")
        for mark, line in out:
            print(f"  {mark} {line}")
        if not ok:
            print(f"  {NO} {why}")
            print(f"  {INFO} stuck? hint {n}")
    s = state()
    if ok and str(n) not in s:
        s[str(n)] = time.time()
        try:
            with open(STATE, "w") as f:
                json.dump(s, f)
        except OSError:
            pass
    return ok, out, why


REPORT_FILES = ["answers.txt", "measurements.json", "decode.py", "tree.json", "subscriptions.json",
                "bridge.py", "sensor.py"]


def banner(title):
    return ["", "=" * 76, title, "=" * 76, ""]


def report():
    import textwrap
    lines = ["LAB 1 — HOW DO OUR DATA TRAVEL TODAY? — REPORT",
             f"Written by `check report` on {datetime.now(PLANT_TZ):%Y-%m-%d at %H:%M} (plant time). "
             "Hand this file in as it is."]
    lines += banner("EXERCISES")
    lines.append("An exercise counts as passed from the first time `check` confirmed it; your programs")
    lines.append("do not need to be running when you write this report.")
    lines.append("")
    for n in EXERCISES:
        ok, _, why = run(n, quiet=True)
        s = state()
        name = f"{n}. {TITLES[n]}"
        if str(n) in s:
            lines.append(f"{name:<48} passed at {hhmm(s[str(n)])}")
        else:
            lines.append(f"{name:<48} NOT PASSED")
            lines += textwrap.wrap(why, 72, initial_indent="    ", subsequent_indent="    ")
    try:
        hints = json.load(open(os.path.join(WORK, ".hints.json")))
    except (OSError, json.JSONDecodeError):
        hints = {}
    lines += ["", "Hints opened: " + (", ".join(f"exercise {k} up to hint {v}"
                                                for k, v in sorted(hints.items())) or "none")]
    for name in REPORT_FILES:
        path = os.path.join(WORK, name)
        lines += banner(f"work/{name}")
        lines += [open(path, encoding="utf-8", errors="replace").read().rstrip()
                  if os.path.exists(path) else "(no such file)"]
    out = os.path.join(WORK, "report-lab1.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"written: {out} — hand this file in.")


def main():
    args = sys.argv[1:]
    if args and args[0] == "report":
        return report()
    todo = [int(a) for a in args if a.isdigit() and int(a) in EXERCISES] or list(EXERCISES)
    results = {n: run(n)[0] for n in todo}
    core = [n for n in todo if n in CORE]
    deeper = [n for n in todo if n in DEEPER]
    summary = []
    if core:
        summary.append(f"{sum(results[n] for n in core)}/{len(core)} passed")
    if deeper:
        summary.append(f"deeper: {sum(results[n] for n in deeper)}/{len(deeper)}")
    print("\n" + ", ".join(summary))


if __name__ == "__main__":
    main()
