"""Controlled AC-1 simulator. Sends real QoS-1 MQTT PUBLISH packets to the site broker."""
import argparse
import threading
import time
import sys

sys.path.insert(0, "/lab")
from lab4_common import RAW_TOPIC, encode, new_client

STANDARD = [
    180, 179, 195, 181, 165,  # window 1: mean 180, hidden isolated peak 195
    180, 191, 193, 195, 180,  # window 2: sustained high sequence at 7,8,9
    182, 180, 178, 181, 179,
    182, 180, 181, 179, 180,
]
NOISY = [
    180, 194, 181, 192, 180,
    195, 178, 191, 180, 193,
    179, 192, 180, 195, 180,
    182, 191, 180, 193, 179,
]
SEGMENTS = {"all": (1, 20), "before": (1, 5), "outage": (6, 15), "after": (16, 20)}


def planned(profile, segment):
    values = STANDARD if profile == "standard" else NOISY
    first, last = SEGMENTS[segment]
    return [(i, values[i - 1]) for i in range(first, last + 1)]


def main():
    ap = argparse.ArgumentParser(description="Publish a deterministic AC-1 temperature scenario")
    ap.add_argument("--run", required=True, help="unique run ID, e.g. RAW-1")
    ap.add_argument("--segment", choices=SEGMENTS, default="all")
    ap.add_argument("--profile", choices=["standard", "noisy"], default="standard")
    ap.add_argument("--interval", type=float, default=0.18,
                    help="seconds between samples (default 0.18)")
    args = ap.parse_args()
    if not args.run or len(args.run) > 48 or not all(c.isalnum() or c in "-_" for c in args.run):
        ap.error("--run must be 1–48 letters, digits, hyphens or underscores")
    if args.interval < 0.05:
        ap.error("--interval must be >= 0.05 seconds")
    connected = threading.Event()
    c = new_client(f"lab4-sensor-{int(time.time() * 1000000) % 1000000000}")
    def on_connect(client, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            connected.set()
    c.on_connect = on_connect
    try:
        c.connect("site-broker", 1883, keepalive=30)
        c.loop_start()
        if not connected.wait(8):
            raise RuntimeError("Cannot connect to site-broker")
        for seq, temperature in planned(args.profile, args.segment):
            message = {"device_id": "AC-1", "run_id": args.run,
                       "seq": seq, "temperature": temperature}
            info = c.publish(RAW_TOPIC, payload=encode(message), qos=1, retain=False)
            if info.rc != 0:
                raise RuntimeError(f"MQTT publish failed: rc={info.rc}")
            info.wait_for_publish(timeout=5)
            if not info.is_published():
                raise TimeoutError(f"No PUBACK for seq={seq}")
            print(f"PUBACK run={args.run} seq={seq:02d} temperature={temperature} topic={RAW_TOPIC}")
            time.sleep(args.interval)
        print(f"SENT {len(planned(args.profile, args.segment))} MQTT messages (QoS 1) for run={args.run}")
    finally:
        c.disconnect()
        c.loop_stop()


if __name__ == "__main__":
    main()
