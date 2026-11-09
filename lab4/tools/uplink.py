"""Application-level site/cloud forwarding link, deliberately stoppable for Lab 4.

It is NOT a full WAN emulator or network partition. Both MQTT brokers are real,
separate containers on separate Docker networks. Only this process forwards
production publications between the networks.
"""
import json
import logging
import threading

from lab4_common import RAW_TOPIC, SUMMARY_TOPIC, ALERT_TOPIC, SUBSCRIPTIONS, new_client, mode
from web_state import run_server

logging.basicConfig(level=logging.INFO, format="[uplink] %(message)s")
ready_site = threading.Event()
ready_cloud = threading.Event()
lock = threading.RLock()
runs = {}
latest = None
site = new_client("lab4-uplink-in")
cloud = new_client("lab4-uplink-out")


def ready():
    return ready_site.is_set() and ready_cloud.is_set()


def on_cloud_connect(c, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logging.error("Cloud broker connect failed %s", reason_code)
        return
    ready_cloud.set()


def on_cloud_disconnect(c, userdata, flags, reason_code, properties):
    ready_cloud.clear()


def on_site_connect(c, userdata, flags, reason_code, properties):
    ready_site.clear()
    if reason_code.is_failure:
        logging.error("Site broker connect failed %s", reason_code)
        return
    c.subscribe(SUBSCRIPTIONS)


def on_site_subscribe(c, userdata, mid, reason_codes, properties):
    if reason_codes and all(not code.is_failure for code in reason_codes):
        ready_site.set()
        logging.info("READY link (mode=%s)", mode())


def on_site_disconnect(c, userdata, flags, reason_code, properties):
    ready_site.clear()


def on_site_message(c, userdata, msg):
    global latest
    try:
        selected = mode()
        forward = msg.topic == RAW_TOPIC if selected == "raw" else msg.topic in (SUMMARY_TOPIC, ALERT_TOPIC)
        if not forward or not ready_cloud.is_set():
            return
        # Keeping the original MQTT payload and topic lets the remote application
        # count publications and bytes it actually received.
        info = cloud.publish(msg.topic, msg.payload, qos=1, retain=False)
        if info.rc != 0:
            logging.error("Publish failed: %s", info.rc)
            return
        record = json.loads(msg.payload)
        run = record["run_id"]
        with lock:
            state = runs.setdefault(run, {"messages": 0, "payload_bytes": 0, "topics": {}})
            state["messages"] += 1
            state["payload_bytes"] += len(msg.payload)
            state["topics"][msg.topic] = state["topics"].get(msg.topic, 0) + 1
            latest = run
    except Exception:
        logging.exception("Forwarding error")


def state_for(run_id):
    with lock:
        target = run_id or latest
        return {"run_id": target, "data": runs.get(target, {}).copy(), "mode": mode()}


if __name__ == "__main__":
    cloud.on_connect = on_cloud_connect
    cloud.on_disconnect = on_cloud_disconnect
    site.on_connect = on_site_connect
    site.on_subscribe = on_site_subscribe
    site.on_disconnect = on_site_disconnect
    site.on_message = on_site_message
    threading.Thread(target=run_server,
                     args=(8083, "WAN forwarder", state_for, ready), daemon=True).start()
    cloud.connect("cloud-broker", 1883, keepalive=30)
    cloud.loop_start()
    site.connect("site-broker", 1883, keepalive=30)
    site.loop_forever()
