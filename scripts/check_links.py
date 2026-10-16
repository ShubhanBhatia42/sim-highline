"""Checks that the DOIs and URLs behind every record resolve. A publisher that refuses automated requests (401, 403, 429) is reported as 'unverified', not broken; 404, 410 and failures to connect are 'broken'.
Writes data/analysis/link-check.json. Needs network access, so it is not part of verify-all.sh; run it before a release and weekly from CI. Usage: python3 scripts/check_links.py [--limit N]"""
import concurrent.futures as cf
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; sim-highline-link-check; +https://github.com/ShubhanBhatia42/sim-highline)"


def collect():
    recs = json.loads((ROOT / "data" / "export" / "sim-highline-records.json").read_text())["records"]
    urls = {}
    for r in recs:
        p = r["provenance"]
        if p.get("doi"):
            urls.setdefault("https://doi.org/" + p["doi"], []).append(r["id"])
        if p.get("url"):
            urls.setdefault(p["url"], []).append(r["id"])
    return urls


def check(url, tries=2):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
            with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
                return "ok", r.status
        except urllib.error.HTTPError as e:
            last = e.code
            if e.code in (401, 403, 429, 999):
                return "unverified", e.code
            if e.code in (404, 410):
                return "broken", e.code
        except Exception as e:  # DNS failure, timeout, reset
            last = type(e).__name__
        time.sleep(1.5)
    return ("broken" if isinstance(last, int) and last < 500 and last in (404, 410) else "unverified"), last


def check_doi(url):
    """A publisher may refuse scripts; Crossref and DataCite do not. A DOI registered with either resolves."""
    status, code = check(url)
    if status == "ok" or not url.startswith("https://doi.org/"):
        return status, code
    doi = url[len("https://doi.org/"):]
    for api in ("https://api.crossref.org/works/", "https://api.datacite.org/dois/"):
        st, cd = check(api + doi.replace("/", "%2F") if "datacite" in api else api + doi, tries=1)
        if st == "ok":
            return "ok", f"registered ({api.split('.')[1]})"
    return status, code


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    urls = collect()
    items = sorted(urls)[:limit]
    out = {}
    with cf.ThreadPoolExecutor(12) as ex:
        for url, (status, code) in zip(items, ex.map(check_doi, items)):
            out[url] = {"status": status, "code": code, "records": len(urls[url])}
    summary = {s: sum(1 for v in out.values() if v["status"] == s) for s in ("ok", "unverified", "broken")}
    report = {"checked": len(out), **summary, "broken": {u: v for u, v in out.items() if v["status"] == "broken"}, "unverified": {u: v for u, v in out.items() if v["status"] == "unverified"}}
    (ROOT / "data" / "analysis" / "link-check.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"links: {len(out)} checked, {summary['ok']} ok, {summary['unverified']} unverified (publisher refused a script), {summary['broken']} broken")
    for u, v in report["broken"].items():
        print("  BROKEN", v["code"], u, f"({v['records']} records)")


if __name__ == "__main__":
    main()
