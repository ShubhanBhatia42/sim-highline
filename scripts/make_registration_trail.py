"""The dated trail that shows the rules were written before the results: for each pre-registered study, the commits of its protocol (the first is the registration, later ones are amendments) and the first commit of its result file. Written from the git history to
data/registration-trail.json, which the studies page and scripts/test_registration.py read (so CI, which may have a shallow checkout, does not need the history). Re-run it when a protocol or a result changes. Usage: python3 scripts/make_registration_trail.py"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIES = {
    "harmonization": ("docs/PROTOCOL-harmonization.md", "data/analysis/harmonization.json"),
    "model-form": ("docs/PROTOCOL-model-form.md", "data/analysis/model-form.json"),
    "joint-reachability": ("docs/PROTOCOL-joint-reachability.md", "data/analysis/joint-reachability.json"),
    "quenching-shape": ("docs/PROTOCOL-quenching-shape.md", "data/analysis/quenching-shape.json"),
    "resolution": ("docs/PROTOCOL-resolution.md", "data/analysis/resolution.json"),
}


def log(path, first_only=False):
    out = subprocess.run(["git", "log", "--reverse", "--format=%H|%cI|%s", "--", path], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip().splitlines()
    rows = [dict(zip(("hash", "date", "subject"), l.split("|", 2))) for l in out]
    for r in rows:
        r["short"] = r["hash"][:7]
    return rows[:1] if first_only else rows


def main():
    trail = {}
    for name, (protocol, result) in STUDIES.items():
        p, r = log(protocol), log(result, True)
        trail[name] = {"protocol_file": protocol, "result_file": result, "protocol_commits": p, "result_first_commit": r[0] if r else None}
    (ROOT / "data" / "registration-trail.json").write_text(json.dumps(trail, indent=1) + "\n")
    for name, t in trail.items():
        print(f"{name}: protocol {t['protocol_commits'][0]['date'][:16]} ({len(t['protocol_commits'])} commits), result {t['result_first_commit']['date'][:16] if t['result_first_commit'] else 'none'}")


if __name__ == "__main__":
    main()
