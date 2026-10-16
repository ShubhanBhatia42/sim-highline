"""The protocol of every pre-registered study was committed before its result file first existed (from data/registration-trail.json, written by scripts/make_registration_trail.py)."""
import json
import sys
from pathlib import Path

t = json.loads((Path(__file__).resolve().parent.parent / "data" / "registration-trail.json").read_text())
bad = []
for name, s in t.items():
    p, r = s["protocol_commits"], s["result_first_commit"]
    if not p or not r:
        bad.append(f"{name}: missing protocol or result commit")
    elif p[0]["date"] > r["date"]:
        bad.append(f"{name}: the protocol ({p[0]['date']}) is later than the result ({r['date']})")
if bad:
    print("registration trail:\n  " + "\n  ".join(bad)); sys.exit(1)
print(f"registration trail: OK ({len(t)} studies, protocol before result in each)")
