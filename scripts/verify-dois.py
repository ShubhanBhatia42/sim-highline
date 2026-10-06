"""Network check, not part of the offline chain: every distinct DOI in data/curves resolves at Crossref (or DataCite for 10.48550 arXiv DOIs),
and where the stored citation states 'Journal VOL, PAGE' the volume and first page agree with Crossref. Usage: python3 scripts/verify-dois.py [--cache FILE]"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cache_path = Path(sys.argv[sys.argv.index("--cache") + 1]) if "--cache" in sys.argv else None
cache = json.loads(cache_path.read_text()) if cache_path and cache_path.exists() else {}
seen = {}
for f in sorted((ROOT / "data" / "curves").glob("*.json")):
    for r in json.loads(f.read_text())["records"]:
        d = r["provenance"].get("doi")
        if d:
            seen.setdefault(d, set()).add(r["provenance"]["citation"])


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sim-highline-doi-check (mailto:s.bhatia@campus.lmu.de)"})
    return json.load(urllib.request.urlopen(req, timeout=30))


problems = []
for d, cites in sorted(seen.items()):
    if d not in cache:
        try:
            if d.startswith("10.48550/"):
                m = get("https://api.datacite.org/dois/" + urllib.parse.quote(d))["data"]["attributes"]
                cache[d] = {"title": m["titles"][0]["title"], "volume": None, "page": None, "authors": [a.get("familyName") or a.get("name") or "" for a in m.get("creators", [])][:3], "year": m.get("publicationYear")}
            else:
                m = get("https://api.crossref.org/works/" + urllib.parse.quote(d))["message"]
                cache[d] = {"title": " ".join(re.sub("<[^>]+>", "", m["title"][0]).split()) if m.get("title") else "", "volume": m.get("volume"), "page": m.get("page") or m.get("article-number"), "authors": [a.get("family", "") for a in m.get("author", [])][:3], "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0]}
        except Exception as e:
            cache[d] = {"error": str(e)[:80]}
        time.sleep(0.2)
    c = cache[d]
    if "error" in c:
        problems.append((d, "does not resolve", c["error"]))
        continue
    for cite in cites:
        first = re.match(r"\s*([A-Za-z'\- ]+?)(?: et al\.| &|,| \(|\d)", cite)
        fold = lambda t: re.sub(r"[^a-z]", "", __import__('unicodedata').normalize('NFKD', t.lower()).encode('ascii', 'ignore').decode())
        if first and c.get("authors") and len(fold(first.group(1))) > 3 and not any(fold(first.group(1))[:6] in fold(a) or fold(a)[:6] in fold(first.group(1)) for a in c["authors"]):
            problems.append((d, f"first author {first.group(1).strip()!r} not among Crossref authors {c['authors']}", cite[:90]))
        m = re.search(r"\b[A-Za-z&. ]+ (\d{2,4}), ([A-Za-z]?\d+)\b", cite)
        v = re.search(r"(?:MNRAS|ApJS?|ApJL?|AJ|A&A|ARA&A|Nature) (\d+), ([A-Za-z]?\d+)", cite)
        if v and c["volume"] and c["page"]:
            if str(c["volume"]) != v.group(1) or not str(c["page"]).startswith(v.group(2).lstrip("L")) and v.group(2) not in str(c["page"]):
                problems.append((d, f"citation says {v.group(1)}, {v.group(2)}; Crossref has {c['volume']}, {c['page']}", cite[:90]))
if cache_path:
    cache_path.write_text(json.dumps(cache, indent=1))
print(f"{len(seen)} distinct DOIs checked; {len(problems)} problem(s)")
for p in problems:
    print(" ", *p)
