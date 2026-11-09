"""Extension D: apply the student algorithm to real observations from both services."""
import argparse
from report import get
from gaps_student import missing_ranges

p = argparse.ArgumentParser()
p.add_argument("--run", required=True)
a = p.parse_args()
edge, cloud = get("edge", 8080, a.run), get("cloud", 8081, a.run)
if not edge or not edge.get("seqs"):
    raise SystemExit("No local data for run. Run the WAN scenario first.")
if cloud is None:
    raise SystemExit("Cloud dashboard is unavailable.")
coverage = [(seq, seq) for seq in cloud.get("raw_seqs", [])]
coverage.extend((w["first_seq"], w["last_seq"]) for w in cloud.get("windows", []))
print("LOCAL sequence IDs:", edge["seqs"])
print("CLOUD covered ranges:", coverage)
print("MISSING ranges:", missing_ranges(edge["seqs"], coverage))
