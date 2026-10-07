"""Find new arXiv papers (astro-ph.GA) that mention a simulation suite sim-highline covers or tracks, and are not yet in the backlog.
    python3 scripts/watch-arxiv.py [--since YYYY-MM-DD] [--scan] [--state data/literature-watch.json] [--markdown OUT.md]
State (data/literature-watch.json) records the last check and every paper already reported, so each run lists only what is new.
--scan also fetches each new paper's source and reports which relations its captions cover and whether the figures are vector (needs PyMuPDF)."""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NS = {"a": "http://www.w3.org/2005/Atom"}
SKIP = {"AREPO (moving mesh)", "AREPO-RT", "ChaNGa", "ChaNGa moving mesh", "GADGET-4", "GIZMO (meshless)", "Galacticus", "Gasoline2", "RAMSES-RT", "SWIFT", "SAGE", "Shark", "L-Galaxies", "Dark Sage", "EMERGE", "FIRE", "Santa Cruz SAM and hydro review", "SPHINX"}
AMBIGUOUS = {"EDGE", "FLARES", "Auriga", "Aurora", "Renaissance", "Obelisk", "OWLS", "CoDa", "CROC", "VELA", "LYRA", "DREAMS", "Hydrangea", "MaGICC", "Illustris"}
EXTRA = ["FIRE-2", "FIRE-3", "SPHINX20", "TNG50", "TNG100", "TNG300", "TNG-Cluster", "MillenniumTNG", "CAMELS", "FLAMINGO", "COLIBRE", "THESAN-ZOOM"]


def suites():
    d = json.loads((ROOT / "data" / "literature-backlog.json").read_text())["entries"]
    names = {e["project"] for e in d if e["section"] in ("suite in sim-highline", "suite not in sim-highline")} - SKIP
    return sorted(names | set(EXTRA))


def query(names, since, until, start=0):
    terms = " OR ".join(f'abs:"{n}" OR ti:"{n}"' for n in names)
    q = f"({terms}) AND cat:astro-ph.GA AND submittedDate:[{since.strftime('%Y%m%d')}0000 TO {until.strftime('%Y%m%d')}2359]"
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": q, "start": start, "max_results": 100, "sortBy": "submittedDate", "sortOrder": "descending"})
    req = urllib.request.Request(url, headers={"User-Agent": "sim-highline-watch (https://github.com/ShubhanBhatia42/sim-highline)"})
    return ET.fromstring(urllib.request.urlopen(req, timeout=60).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--state", default=str(ROOT / "data" / "literature-watch.json"))
    ap.add_argument("--markdown")
    a = ap.parse_args()
    state_path = Path(a.state)
    state = json.loads(state_path.read_text()) if state_path.exists() else {"lastChecked": None, "reported": {}}
    today = datetime.date.today()
    since = datetime.date.fromisoformat(a.since) if a.since else (datetime.date.fromisoformat(state["lastChecked"]) - datetime.timedelta(days=2) if state["lastChecked"] else today - datetime.timedelta(days=30))
    known = {e["arxiv"] for e in json.loads((ROOT / "data" / "literature-backlog.json").read_text())["entries"]} | set(state["reported"])
    names = suites()
    found = {}
    for k in range(0, len(names), 6):
        batch = names[k:k + 6]
        root = query(batch, since, today)
        for e in root.findall("a:entry", NS):
            aid = re.sub(r"v\d+$", "", e.find("a:id", NS).text.rsplit("/", 1)[-1])
            if aid in known or aid in found:
                continue
            title = " ".join(e.find("a:title", NS).text.split())
            summ = " ".join(e.find("a:summary", NS).text.split())
            text = title + " " + summ
            if "simulat" not in text.lower():
                continue
            hit = [n for n in batch if re.search(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])", text, 0 if n in AMBIGUOUS else re.I)]
            if not hit:
                continue
            first = e.find("a:author/a:name", NS).text.split()[-1]
            found[aid] = {"arxiv": aid, "title": title, "firstAuthor": first, "published": e.find("a:published", NS).text[:10], "matches": hit, "status": "new"}
        time.sleep(3.1)
    if a.scan and found:
        sys.path.insert(0, str(ROOT / "scripts"))
        import scan_literature
        res = scan_literature.scan(list(found), None, progress=False)
        for aid, r in res.items():
            found[aid]["scan"] = r if "error" in r else {"relations": sorted({x for h in r["hits"] for x in h["rels"]}), "formats": sorted({h["fmt"] for h in r["hits"]})}
    state["reported"].update(found)
    state["lastChecked"] = today.isoformat()
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    lines = [f"{len(found)} new paper(s) mentioning a tracked simulation suite since {since.isoformat()}:", ""]
    for p in sorted(found.values(), key=lambda p: p["published"], reverse=True):
        s = p.get("scan")
        extra = f" — relations: {', '.join(s['relations']) or 'none matched'}; figures: {', '.join(s['formats']) or 'none'}" if s and "relations" in s else ""
        lines.append(f"- [{p['arxiv']}](https://arxiv.org/abs/{p['arxiv']}) {p['firstAuthor']} et al. ({p['published']}): {p['title']} [{', '.join(p['matches'])}]{extra}")
    text = "\n".join(lines) + "\n"
    if a.markdown:
        Path(a.markdown).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
