"""Read independent application-side counters, not theoretical message estimates."""
import argparse
import json
import time
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def get(service, port, run):
    try:
        with urlopen(f"http://{service}:{port}/api/state?run={run}", timeout=1.5) as response:
            return json.load(response).get("data", {})
    except (OSError, URLError, HTTPError, ValueError):
        return None


def metrics(run):
    return get("edge", 8080, run), get("cloud", 8081, run), get("uplink", 8083, run)


def print_report(run, edge, cloud, uplink):
    edge, cloud = edge or {}, cloud or {}
    raw_count = cloud.get("raw_count", 0)
    summary_count = cloud.get("summary_count", 0)
    alerts = cloud.get("alerts", [])
    last_ranges = [(w.get("first_seq"), w.get("last_seq")) for w in cloud.get("windows", [])]
    print(f"\nRUN {run}")
    print(f"SITE : raw samples={edge.get('raw_count', 0)}, locally produced summaries={edge.get('summary_count', 0)}, local alerts={[a['seq'] for a in edge.get('alerts', [])]}")
    print(f"CLOUD: received MQTT publications={cloud.get('messages', 0)}, raw={raw_count}, summaries={summary_count}, edge/cloud alerts={[str(a.get('seq'))+'('+a.get('source','?')+')' for a in alerts]}")
    print(f"CLOUD: received MQTT application-payload bytes={cloud.get('payload_bytes', 0)}")
    print(f"CLOUD: raw sequence IDs={cloud.get('raw_seqs', [])}")
    print(f"CLOUD: summary ranges={last_ranges}")
    if uplink is None:
        print("UPLINK: not responding (intentionally stopped during a WAN fault?)")
    else:
        print(f"UPLINK: forwarded since its last start={uplink.get('messages', 0)} publications, {uplink.get('payload_bytes', 0)} application-payload bytes")
    if edge.get("errors"):
        print(f"EDGE ERRORS: {edge['errors'][-3:]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--expect-edge", type=int, default=None)
    p.add_argument("--expect-cloud", type=int, default=None)
    p.add_argument("--timeout", type=float, default=12)
    a = p.parse_args()
    deadline = time.monotonic() + a.timeout
    while True:
        edge, cloud, uplink = metrics(a.run)
        ecount = (edge or {}).get("raw_count", 0)
        ccount = (cloud or {}).get("messages", 0)
        okay = ((a.expect_edge is None or ecount >= a.expect_edge) and
                (a.expect_cloud is None or ccount >= a.expect_cloud))
        if okay or time.monotonic() >= deadline:
            break
        time.sleep(0.3)
    print_report(a.run, edge, cloud, uplink)
    if not okay:
        print(f"NOT READY: expected site>={a.expect_edge}, cloud>={a.expect_cloud}")
        raise SystemExit(1)
    print("REPORT READY")


if __name__ == "__main__":
    main()
