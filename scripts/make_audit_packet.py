"""Builds the expert-audit packet: a self-contained page with a sample of the digitized curves, each with its plot, its source, its definitions, a few values to check by eye against the paper's figure, and a link that opens a pre-filled report.
The sample is deterministic, spread across simulations and relations, and sized by --n (default 60). Writes docs/audit-packet/packet.html and docs/audit-packet/values.csv.
Usage: python3 scripts/make_audit_packet.py [--n 60]"""
import base64
import collections
import csv
import hashlib
import html
import io
import json
import sys
import urllib.parse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
REPO = json.loads((ROOT / "data" / "release.json").read_text())["repo"]


def sample(recs, n):
    dig = [r for r in recs if r["kind"] == "simulation" and r["provenance"]["tier"] == "digitized-figure" and r["representation"].get("type") == "points" and len(r["representation"]["points"]) >= 4]
    by = collections.defaultdict(list)
    for r in sorted(dig, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest()):
        by[r["source"]].append(r)
    chosen, pools = [], {s: list(v) for s, v in sorted(by.items())}
    seen_rel = collections.defaultdict(set)
    while len(chosen) < n and any(pools.values()):
        for s in sorted(pools):
            if not pools[s] or len(chosen) >= n:
                continue
            # prefer a relation this simulation has not been sampled for yet
            i = next((k for k, r in enumerate(pools[s]) if r["relation"] not in seen_rel[s]), 0)
            r = pools[s].pop(i)
            seen_rel[s].add(r["relation"])
            chosen.append(r)
    return chosen


def plot(r):
    p = r["representation"]["points"]
    x, y = [q["x"] for q in p], [q["y"] for q in p]
    fig, ax = plt.subplots(figsize=(4.2, 2.8), dpi=110)
    ax.plot(x, y, "-o", ms=2.5, lw=1.2, color="#1648c8")
    ax.set_xlabel(f"{r['axes'].get('xDefinition', 'x')} [{r['axes'].get('xUnit', '')}]", fontsize=7)
    ax.set_ylabel(f"{r['axes'].get('yDefinition', 'y')} [{r['axes'].get('yUnit', '')}]", fontsize=7)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    b = io.BytesIO()
    fig.savefig(b, format="png")
    plt.close(fig)
    return base64.b64encode(b.getvalue()).decode()


def values(r, k=6):
    p = r["representation"]["points"]
    idx = sorted({round(i * (len(p) - 1) / (k - 1)) for i in range(k)})
    return [(p[i]["x"], p[i]["y"]) for i in idx]


def main():
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 60
    recs = json.loads((ROOT / "data" / "export" / "sim-highline-records.json").read_text())["records"]
    ch = sample(recs, n)
    out = ROOT / "docs" / "audit-packet"
    out.mkdir(exist_ok=True)
    rows, cards = [], []
    for i, r in enumerate(ch, 1):
        p, d = r["provenance"], r.get("definitions") or {}
        vals = values(r)
        rows.append([r["id"], r["source"], r.get("run") or "", r["relation"], r["epoch"]["zRepresentative"], p.get("citation"), p.get("figure"), p.get("panel"), "; ".join(f"({x:.4g}, {y:.4g})" for x, y in vals)])
        issue = f"{REPO}/issues/new?template=curve-error.yml&title={urllib.parse.quote('Audit: ' + r['id'])}&record={urllib.parse.quote(r['id'])}"
        defs = "".join(f"<li><b>{html.escape(k)}</b>: {html.escape(json.dumps(v) if isinstance(v, (dict, list)) else str(v))}</li>" for k, v in d.items() if k != "cosmology")
        vt = "".join(f"<tr><td>{x:.4g}</td><td>{y:.4g}</td></tr>" for x, y in vals)
        cards.append(f"""<section class="rec" id="r{i}"><h2>{i}. {html.escape(r['source'])}: {html.escape(r.get('run') or r['relation'])}</h2>
<p class="meta">{html.escape(r['relation'])} · z = {r['epoch']['zRepresentative']:g} · <code>{html.escape(r['id'])}</code></p>
<div class="grid"><img alt="Extracted curve of record {html.escape(r['id'])}" src="data:image/png;base64,{plot(r)}">
<div><p><b>Source</b>: {html.escape(p.get('citation') or '')}{f' (<a href="{html.escape(p["url"])}">link</a>)' if p.get('url') else ''}</p>
<p><b>Figure and panel</b>: {html.escape(str(p.get('figure') or ''))}; {html.escape(str(p.get('panel') or ''))}</p>
<p><b>x</b>: {html.escape(str(r['axes'].get('xDefinition')))} [{html.escape(str(r['axes'].get('xUnit')))}]<br><b>y</b>: {html.escape(str(r['axes'].get('yDefinition')))} [{html.escape(str(r['axes'].get('yUnit')))}]</p>
<table><thead><tr><th>x</th><th>y</th></tr></thead><tbody>{vt}</tbody></table></div></div>
<details><summary>Definitions recorded</summary><ul>{defs}</ul></details>
<p class="q">Is this the run and panel named? Do these values match the figure to about 0.1 dex? Are the definitions right? <a href="{issue}">Report a problem or confirm</a></p></section>""")
    css = "body{font:16px/1.5 Georgia,serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#0c1016}h1{font-size:1.6rem}h2{font-size:1.1rem;margin:0}.rec{border-top:2px solid #0c1016;padding:1rem 0}.meta{font:13px monospace;color:#5f6977;margin:.2rem 0 .6rem}.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:1rem}@media(max-width:700px){.grid{grid-template-columns:1fr}}img{max-width:100%}table{border-collapse:collapse;font:13px monospace}td,th{border-bottom:1px solid #dde1e6;padding:2px 10px;text-align:right}.q{font-size:14px;background:#f4f5f7;padding:.5rem .7rem}details{font-size:14px}"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>sim-highline audit packet</title><style>{css}</style></head><body>
<h1>sim-highline audit packet</h1>
<p>{len(ch)} curves that were read from published figures, chosen by a fixed rule so that every simulation with such curves appears and relations are spread. For each: the curve as stored, six of its values, where it came from and the definitions recorded. Please look at the cited figure and tell us whether it is the right run and panel, whether the values agree to about 0.1 dex, and whether the definitions are right. Five minutes per curve is plenty; one curve is useful. Nothing here is a claim that the curves are correct: nobody who knows these simulations has checked them yet.</p>
{''.join(cards)}</body></html>"""
    (out / "packet.html").write_text(page)
    with open(out / "values.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["record", "source", "run", "relation", "z", "citation", "figure", "panel", "six_values_x_y"])
        w.writerows(rows)
    print(f"audit packet: {len(ch)} curves from {len({r['source'] for r in ch})} simulations; {(out / 'packet.html').stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
