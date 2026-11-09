"""Cloud-side MQTT processor and read-only dashboard."""
import json
import logging
import threading
from collections import deque

from lab4_common import RAW_TOPIC, SUMMARY_TOPIC, ALERT_TOPIC, SUBSCRIPTIONS, new_client, sample
from web_state import run_server

logging.basicConfig(level=logging.INFO, format="[cloud] %(message)s")
lock = threading.RLock()
ready = threading.Event()
runs = {}
latest = None
client = new_client("lab4-cloud-analytics")


def create_run():
    return {"messages": 0, "raw_count": 0, "summary_count": 0,
            "alert_count": 0, "payload_bytes": 0, "readings": [],
            "windows": [], "alerts": [], "raw_seqs": [],
            "last_three": deque(maxlen=3), "previous_above": False,
            "previous_seq": None,
            "observed_topics": {}}


def process(topic, payload):
    global latest
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("run_id"), str):
        raise ValueError("Invalid run payload")
    run = data["run_id"]
    with lock:
        state = runs.setdefault(run, create_run())
        latest = run
        state["messages"] += 1
        state["payload_bytes"] += len(payload)
        state["observed_topics"][topic] = state["observed_topics"].get(topic, 0) + 1
        if topic == RAW_TOPIC:
            _, seq, temp = sample(data)
            state["raw_count"] += 1
            # A missing or out-of-order sequence must not be treated as an
            # uninterrupted series of consecutive physical measurements.
            if state["previous_seq"] is not None and seq != state["previous_seq"] + 1:
                state["last_three"].clear()
                state["previous_above"] = False
            state["previous_seq"] = seq
            state["raw_seqs"].append(seq)
            state["readings"].append({"seq": seq, "temperature": temp})
            state["last_three"].append(temp)
            # Cloud reference rule uses a sliding measurement window rather than
            # the counter-based function the students implement at the edge.
            above = (len(state["last_three"]) == 3 and
                     all(v > 190 for v in state["last_three"]))
            if above and not state["previous_above"]:
                state["alerts"].append({"seq": seq, "temperature": temp, "source": "cloud"})
                state["alert_count"] += 1
                logging.info("CLOUD ALERT run=%s seq=%s", run, seq)
            state["previous_above"] = above
        elif topic == SUMMARY_TOPIC:
            state["summary_count"] += 1
            state["windows"].append(data)
            logging.info("CLOUD SUMMARY run=%s seq=%s..%s", run, data.get("first_seq"), data.get("last_seq"))
        elif topic == ALERT_TOPIC:
            state["alert_count"] += 1
            state["alerts"].append({"seq": data.get("seq"), "temperature": data.get("temperature"), "source": "edge"})
            logging.info("EDGE ALERT RECEIVED run=%s seq=%s", run, data.get("seq"))
        else:
            raise ValueError("Unexpected topic")
        if len(state["readings"]) > 100:
            state["readings"] = state["readings"][-100:]


def on_connect(c, userdata, flags, reason_code, properties):
    ready.clear()
    if reason_code.is_failure:
        logging.error("MQTT connection refused: %s", reason_code)
        return
    c.subscribe(SUBSCRIPTIONS)


def on_subscribe(c, userdata, mid, reason_codes, properties):
    if reason_codes and all(not code.is_failure for code in reason_codes):
        ready.set()
        logging.info("READY for cloud MQTT topics")


def on_disconnect(c, userdata, flags, reason_code, properties):
    ready.clear()


def on_message(c, userdata, msg):
    try:
        process(msg.topic, msg.payload)
    except Exception:
        logging.exception("Invalid cloud MQTT message")


def state_for(run_id):
    with lock:
        target = run_id or latest
        s = runs.get(target)
        if s is None:
            return {"run_id": target, "data": {}}
        return {"run_id": target, "data": {k: (v.copy() if isinstance(v, list) else v)
                                          for k, v in s.items()
                                          if k not in ("last_three", "previous_above", "previous_seq")}}


if __name__ == "__main__":
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    threading.Thread(target=run_server,
                     args=(8081, "Cloud analytics", state_for, ready.is_set), daemon=True).start()
    client.connect("cloud-broker", 1883, keepalive=30)
    client.loop_forever()
