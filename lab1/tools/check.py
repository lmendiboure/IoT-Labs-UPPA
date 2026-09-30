#!/usr/bin/env python3
"""check — tells you whether each exercise of Lab 1 is done.

    check            every exercise
    check 4          exercise 4 only
    check report     writes report-lab1.md, the file you hand in

It reads what the relay saw (every MQTT packet of the lab goes through it)
and the files you write in /work. Nothing here changes your work.
"""
import json
import os
import statistics
import sys
import time
import urllib.request
from datetime import datetime

VIEWER = os.getenv("VIEWER", "http://relay:8080")
HOST = os.getenv("MQTT_HOST", "relay")
PORT = int(os.getenv("MQTT_PORT", "1884"))
WORK = os.getenv("WORK", "/work")
LAB = os.path.dirname(os.path.realpath(__file__))
STATE = os.path.join(WORK, ".checks.json")
BUILDING = {"thermaline-gw", "KL-7F3A", "KL-1EEC", "chirpstack-ns", "door-ctrl", "bms"}
OK, NO, INFO = "✔", "✘", "·"

TITLES = {
    1: "The lab is running",
    2: "A message by hand, a subscription by hand",
    3: "Measure the building",
    4: "Your virtual sensor",
    5: "A topic tree for the building",
    6: "A retained status and a last will",
    7: "A link that dies in silence",
}


# ---------------------------------------------------------------- helpers
def api(path):
    with urllib.request.urlopen(VIEWER + path, timeout=5) as r:
        return json.loads(r.read())


def mine(client_id):
    """A client of yours: not the building, not this checker."""
    return bool(client_id) and client_id not in BUILDING and not client_id.startswith("checker-")


def load(name):
    path = os.path.join(WORK, name)
    if not os.path.exists(path):
        raise Check(f"{name} not found in /work")
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise Check(f"{name} is not valid JSON: {e.msg} at line {e.lineno}, column {e.colno}")


def hhmm(t):
    return datetime.fromtimestamp(t).strftime("%H:%M:%S")


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
    seen = sorted(recent & BUILDING)
    if len(seen) < 3:
        raise Check("the building is silent (fewer than 3 of its devices published in the last 90 s). "
                    "On the VM: docker compose logs building")
    out.append((OK, f"the building is talking: {', '.join(seen)}"))
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
    tl = [p for p in pubs if p["topic"] == "thermaline/A101/temperature"]
    cs = [p for p in pubs if (p["topic"] or "").startswith("application/adour-meters/")]
    if not tl or not cs:
        raise Check("the relay has not seen enough of the building yet: wait a minute")
    wrong = []

    def expect(key, ok, hint):
        v = m.get(key)
        if not isinstance(v, (int, float)):
            wrong.append(f"{key}: missing or not a number")
        elif not ok(v):
            wrong.append(f"{key} = {v}: {hint}")
        else:
            out.append((OK, f"{key} = {v}"))

    sizes = {p["payload_size"] for p in tl}
    expect("thermaline_payload_bytes", lambda v: v in sizes,
           "not what the viewer shows for thermaline/A101/temperature (payload column)")
    sizes = {p["size"] for p in tl}
    expect("thermaline_packet_bytes", lambda v: v in sizes,
           "not the size of the whole PUBLISH packet for that topic (packet column)")
    lo, hi = min(p["payload_size"] for p in cs), max(p["payload_size"] for p in cs)
    expect("chirpstack_payload_bytes", lambda v: lo * 0.95 <= v <= hi * 1.05,
           "not the payload size of a ChirpStack uplink event")
    expect("meter_data_bytes", lambda v: v == 10,
           "decode the base64 'data' field and count the bytes")
    window = 300
    since = time.time() - window
    recent = [p for p in pubs if p["t"] >= since and p["client"] in BUILDING]
    first = min((p["t"] for p in packets), default=time.time())
    span = min(window, time.time() - first)
    if span < 290:
        wrong.append("building_bytes_per_minute: the lab has been running for less than 5 minutes, "
                     "so the Topics tab does not cover 5 minutes yet. Measure again in a moment")
    else:
        truth = sum(p["size"] for p in recent) / span * 60
        expect("building_bytes_per_minute", lambda v: 0.8 * truth <= v <= 1.2 * truth,
               "more than 20 % away from what the relay measures now")
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


def ex6(out):
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


def ex7(out):
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


EXERCISES = {1: ex1, 2: ex2, 3: ex3, 4: ex4, 5: ex5, 6: ex6, 7: ex7}


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
        print(f"\nExercise {n} — {TITLES[n]}")
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


def report():
    s = state()
    lines = [f"# Lab 1 — report", "", f"Written {datetime.now():%Y-%m-%d %H:%M}.", "",
             "| Exercise | Now | First passed |", "|---|---|---|"]
    for n in EXERCISES:
        ok, _, why = run(n, quiet=True)
        first = hhmm(s[str(n)]) if str(n) in s else "—"
        lines.append(f"| {n} — {TITLES[n]} | {'passed' if ok else 'not yet: ' + why.replace('|', '/')} | {first} |")
    try:
        hints = json.load(open(os.path.join(WORK, ".hints.json")))
    except (OSError, json.JSONDecodeError):
        hints = {}
    lines += ["", "Hints opened: " + (", ".join(f"exercise {k}: {v}" for k, v in sorted(hints.items())) or "none"), ""]
    for name in ("measurements.json", "tree.json", "subscriptions.json"):
        path = os.path.join(WORK, name)
        if os.path.exists(path):
            lines += [f"## {name}", "", "```json", open(path).read().strip(), "```", ""]
    for name in ("sensor.py",):
        path = os.path.join(WORK, name)
        if os.path.exists(path):
            lines += [f"## {name}", "", "```python", open(path).read().strip(), "```", ""]
    path = os.path.join(WORK, "answers.md")
    if os.path.exists(path):
        lines += ["## Answers", "", open(path).read().strip(), ""]
    out = os.path.join(WORK, "report-lab1.md")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"written: {out} — hand this file in.")


def main():
    args = sys.argv[1:]
    if args and args[0] == "report":
        return report()
    todo = [int(a) for a in args if a.isdigit() and int(a) in EXERCISES] or list(EXERCISES)
    passed = sum(run(n)[0] for n in todo)
    print(f"\n{passed}/{len(todo)} passed")


if __name__ == "__main__":
    main()
