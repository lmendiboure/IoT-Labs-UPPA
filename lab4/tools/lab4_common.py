"""Small shared helpers for the Lab 4 MQTT experiment."""
import json
from pathlib import Path

import paho.mqtt.client as mqtt

RAW_TOPIC = "plant/autoclave/AC-1/temperature"
SUMMARY_TOPIC = "edge/autoclave/AC-1/summary"
ALERT_TOPIC = "edge/autoclave/AC-1/alert"
SUBSCRIPTIONS = [(RAW_TOPIC, 1), (SUMMARY_TOPIC, 1), (ALERT_TOPIC, 1)]


def new_client(client_id):
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id,
                       protocol=mqtt.MQTTv311)


def encode(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def mode():
    value = Path("/control/mode.txt").read_text(encoding="utf-8").strip()
    if value not in ("raw", "edge"):
        raise RuntimeError(f"Invalid forwarding mode: {value!r}")
    return value


def window_size():
    n = int(Path("/control/window_size.txt").read_text(encoding="utf-8").strip())
    if n not in (5, 10, 20):
        raise RuntimeError(f"Invalid summary window: {n}")
    return n


def sample(data):
    """Validate only the minimum schema required by these experiments."""
    if not isinstance(data, dict) or data.get("device_id") != "AC-1":
        raise ValueError("Expected an AC-1 JSON object")
    run = data.get("run_id")
    seq = data.get("seq")
    temp = data.get("temperature")
    if not isinstance(run, str) or not run or len(run) > 48:
        raise ValueError("Invalid run_id")
    if type(seq) is not int or seq < 1 or type(temp) not in (int, float):
        raise ValueError("Invalid seq or temperature")
    return run, seq, float(temp)
