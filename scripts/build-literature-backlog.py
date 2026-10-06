import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = {"A": "suite in sim-highline", "B": "suite not in sim-highline", "C": "semi-analytic or empirical model", "D": "numerical method"}
ingested = set()
for f in (ROOT / "data" / "curves").glob("*.json"):
    for r in json.loads(f.read_text())["records"]:
        p = r["provenance"]
        ingested.update(re.findall(r"\d{4}\.\d{4,5}", f"{p.get('url', '')} {p.get('citation', '')}"))
prior = {}
out_path = ROOT / "data" / "literature-backlog.json"
if out_path.exists():
    prior = {e["arxiv"]: e for e in json.loads(out_path.read_text())["entries"]}
entries, sec = [], None
for line in (ROOT / "docs" / "literature-candidates.md").read_text().splitlines():
    m = re.match(r"## ([A-D])\.", line)
    if m:
        sec = m.group(1)
        continue
    m = re.match(r"\| (.+?) \| \[(\d{4}\.\d{4,5})\]\(.+?\) \| (\d{4}) \| (.+?) \| (.+?) \| (.*) \|$", line)
    if not (m and sec):
        continue
    proj, arxiv, year, first, title, note = m.groups()
    if any(e["arxiv"] == arxiv for e in entries):
        continue
    old = prior.get(arxiv, {})
    status = "ingested" if arxiv in ingested else old.get("status", "candidate")
    if status == "ingested" and arxiv not in ingested:
        status = "candidate"
    entries.append({"arxiv": arxiv, "project": proj, "year": int(year), "firstAuthor": first, "title": title, "section": SECTIONS[sec], "couldSupply": note,
                    "status": status, "statusNote": old.get("statusNote", "")})
assert len({e["arxiv"] for e in entries}) == len(entries)
doc = {"schemaVersion": "1.0.0", "note": "Papers found by arXiv API search (ids and titles returned by arXiv). Status: ingested (an id appears in data/curves provenance), queued, skipped (with reason), candidate. Regenerate from docs/literature-candidates.md with scripts/build-literature-backlog.py; edit status and statusNote here.", "entries": entries}
out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"{len(entries)} entries; {sum(e['status'] == 'ingested' for e in entries)} ingested")
