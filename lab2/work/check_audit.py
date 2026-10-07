#!/usr/bin/env python3
import argparse
import collections
import json

p = argparse.ArgumentParser(description="Count application deliveries by stable cure-record id.")
p.add_argument("path", nargs="?", default="audit.jsonl")
a = p.parse_args()
rows = []
try:
    with open(a.path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
except FileNotFoundError:
    raise SystemExit(f"{a.path}: no such file")
counts = collections.Counter(row.get("record_id") for row in rows)
print(f"rows={len(rows)} distinct_record_ids={len(counts)}")
for rid, n in sorted(counts.items()):
    suffix = "  <-- duplicate delivery" if n > 1 else ""
    print(f"{rid}: {n}{suffix}")
