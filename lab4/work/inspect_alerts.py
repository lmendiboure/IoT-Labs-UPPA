"""Extension A: compare instantaneous and sustained alerts on the same observations."""
import argparse
from report import get

p = argparse.ArgumentParser()
p.add_argument("--run", required=True)
a = p.parse_args()
s = get("edge", 8080, a.run)
if not s or not s.get("readings"):
    raise SystemExit("No local readings for this run. Send the scenario first.")
instant = [v["seq"] for v in s["readings"] if v["temperature"] > 190]
sustained = [v["seq"] for v in s.get("alerts", [])]
print(f"RUN {a.run}  above-190 individual readings: {instant}")
print(f"RUN {a.run}  three-consecutive alerts: {sustained}")
print(f"Counts: {len(instant)} instantaneous threshold events vs {len(sustained)} sustained events")
