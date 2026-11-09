"""Wait for actual MQTT subscriptions; docker compose ps alone is not readiness."""
import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

SERVICES = {"edge": "http://edge:8080/health",
            "cloud": "http://cloud:8081/health",
            "uplink": "http://uplink:8083/health"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--without-uplink", action="store_true", help="WAN service is intentionally stopped")
    ap.add_argument("--without-edge", action="store_true", help="Edge processor is intentionally stopped")
    ap.add_argument("--timeout", type=int, default=45)
    args = ap.parse_args()
    selected = {k: v for k, v in SERVICES.items() if not ((args.without_uplink and k == "uplink") or (args.without_edge and k == "edge"))}
    deadline = time.monotonic() + args.timeout
    outstanding = set(selected)
    while time.monotonic() < deadline and outstanding:
        for name in list(outstanding):
            try:
                with urlopen(selected[name], timeout=1.5) as response:
                    if response.status == 200 and json.load(response).get("ready") is True:
                        outstanding.remove(name)
                        print(f"READY {name}: MQTT connected and subscriptions active")
            except (OSError, ValueError, HTTPError, URLError):
                pass
        if outstanding:
            time.sleep(0.35)
    if outstanding:
        print("NOT READY:", ", ".join(sorted(outstanding)))
        raise SystemExit(1)
    print("READY: all requested services")


if __name__ == "__main__":
    main()
