"""Live MQTT edge processor. The decision function is written by students in /work."""
import json
import logging
import sys
import threading
from collections import deque

from lab4_common import RAW_TOPIC, SUMMARY_TOPIC, ALERT_TOPIC, new_client, encode, sample, window_size
from web_state import run_server

sys.path.insert(0, "/work")
from detect_student import step  # intentionally incomplete student exercise
from summary_student import extra_fields  # later extension of the summary payload

logging.basicConfig(level=logging.INFO, format="[edge] %(message)s")
lock = threading.RLock()
ready = threading.Event()
runs = {}
latest = None
client = new_client("lab4-edge")


def create_run(run_id):
    return {
        "raw_count": 0, "summary_count": 0, "alert_count": 0,
        "messages": 0, "payload_bytes": 0,
        "readings": [], "windows": [], "alerts": [], "errors": [],
        "seqs": [], "streak": 0, "buffer": [], "window_size": window_size(),
    }


def process_payload(payload):
    global latest
    data = json.loads(payload)
    run, seq, temp = sample(data)
    with lock:
        state = runs.setdefault(run, create_run(run))
        latest = run
        state["raw_count"] += 1
        state["messages"] += 1
        state["payload_bytes"] += len(payload)
        state["seqs"].append(seq)
        state["readings"].append({"seq": seq, "temperature": temp})
        if len(state["readings"]) > 100:
            state["readings"] = state["readings"][-100:]
        try:
            streak, alert = step(temp, state["streak"])
            if type(streak) is not int or type(alert) is not bool or not (0 <= streak <= 3):
                raise ValueError("step() must return (integer 0..3, bool)")
            state["streak"] = streak
        except Exception as error:
            state["errors"].append(f"seq {seq}: {type(error).__name__}: {error}")
            logging.warning("Student step error: %s", error)
            state["streak"], alert = 0, False
        if alert:
            event = {"device_id": "AC-1", "run_id": run, "seq": seq,
                     "temperature": temp, "rule": "three_consecutive_above_190"}
            state["alerts"].append({"seq": seq, "temperature": temp})
            state["alert_count"] += 1
            client.publish(ALERT_TOPIC, encode(event), qos=1)
            logging.info("ALERT run=%s seq=%s", run, seq)
        state["buffer"].append((seq, temp))
        if len(state["buffer"]) == state["window_size"]:
            entries = state["buffer"]
            event = {"device_id": "AC-1", "run_id": run,
                     "first_seq": entries[0][0], "last_seq": entries[-1][0],
                     "count": len(entries),
                     "mean": round(sum(t for _, t in entries) / len(entries), 2)}
            try:
                extra = extra_fields(entries)
                if not isinstance(extra, dict) or any(k in event for k in extra):
                    raise ValueError("summary extras must be a dict with non-conflicting keys")
                event.update(extra)
            except Exception as error:
                state["errors"].append(f"summary seq {seq}: {type(error).__name__}: {error}")
                logging.warning("Summary student code error: %s", error)
            state["windows"].append(event)
            state["summary_count"] += 1
            state["buffer"] = []
            client.publish(SUMMARY_TOPIC, encode(event), qos=1)
            logging.info("SUMMARY run=%s seq=%s..%s", run, event["first_seq"], event["last_seq"])


def on_connect(c, userdata, flags, reason_code, properties):
    ready.clear()
    if reason_code.is_failure:
        logging.error("MQTT CONNECT refused: %s", reason_code)
        return
    logging.info("MQTT connected; subscribing to site measurements")
    c.subscribe(RAW_TOPIC, qos=1)


def on_subscribe(c, userdata, mid, reason_codes, properties):
    if not any(reason.is_failure for reason in reason_codes):
        ready.set()
        logging.info("READY for AC-1 measurements")


def on_disconnect(c, userdata, flags, reason_code, properties):
    ready.clear()


def on_message(c, userdata, msg):
    try:
        process_payload(msg.payload)
    except Exception:
        logging.exception("Invalid measurement or processing error")


def state_for(run_id):
    with lock:
        target = run_id or latest
        s = runs.get(target)
        if s is None:
            return {"run_id": target, "data": {}}
        # Exclude internal state, buffers and mutable references from the HTTP response.
        return {"run_id": target, "data": {k: (v.copy() if isinstance(v, list) else v)
                                          for k, v in s.items()
                                          if k not in ("streak", "buffer")}}


if __name__ == "__main__":
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    thread = threading.Thread(target=run_server,
                              args=(8080, "Edge gateway", state_for, ready.is_set), daemon=True)
    thread.start()
    client.connect("site-broker", 1883, keepalive=30)
    client.loop_forever()
