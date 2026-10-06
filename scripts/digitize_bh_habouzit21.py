import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2006.10094"
DOI = "10.1093/mnras/stab496"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "analysis" / "allsimu_scaling_mean_2_secondrow_medianonly.pdf"
PANELS = [("Illustris", "Illustris-1"), ("IllustrisTNG", "TNG100-1"), ("IllustrisTNG", "TNG300-1"), ("Horizon-AGN", "Horizon-AGN"), ("EAGLE", "Ref-L100N1504"), ("SIMBA", "m100n1024")]
ZCOL = {(0.0, 0.0, 0.8): 5, (0.12, 0.56, 1.0): 4, (0.0, 0.5, 0.5): 3, (1.0, 0.84, 0.0): 2, (0.82, 0.41, 0.12): 1, (1.0, 0.39, 0.28): 0}
close = lambda c, t: c is not None and all(abs(a - b) < 0.02 for a, b in zip(c, t))
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
grid = vf.grid_from_long_lines(page)
assert len(grid) == 2 and all(len(r) == 6 for r in grid)


def ticks(panel):
    xs, ys = [], []
    for d in page.get_drawings():
        r = d["rect"]
        if d["type"] != "fs" or d["color"] != (0.0, 0.0, 0.0) or len(d["items"]) != 1:
            continue
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if r.width < 0.5 and 7 < r.height < 9 and panel.x0 < cx < panel.x1 and (abs(cy - (panel.y0 + 4)) < 1 or abs(cy - (panel.y1 - 4)) < 1):
            xs.append(round(cx, 1))
        if r.height < 0.5 and 7 < r.width < 9 and panel.y0 < cy < panel.y1 and (abs(cx - (panel.x0 + 4)) < 1 or abs(cx - (panel.x1 - 4)) < 1):
            ys.append(round(cy, 1))
    return sorted(set(xs)), sorted(set(ys))


def linear(pos, vals):
    n = len(pos)
    mp, mv = sum(pos) / n, sum(vals) / n
    b = sum((p - mp) * (v - mv) for p, v in zip(pos, vals)) / sum((p - mp) ** 2 for p in pos)
    a = mv - b * mp
    assert all(abs(a + b * p - v) < 0.02 for p, v in zip(pos, vals)), "major ticks are not equally spaced"
    return lambda p: a + b * p


records = []
for k, (source, run) in enumerate(PANELS):
    top, bot = grid[0][k], grid[1][k]
    xt, yt = ticks(top)
    xb, yb = ticks(bot)
    assert len(xt) == 2 and len(yt) == 5 and len(xb) == 2 and len(yb) == 3, (k, xt, yt, xb, yb)
    fx = linear(xt, [10.0, 11.0])
    fy = linear(yt, [10.0, 9.0, 8.0, 7.0, 6.0])
    fd = linear(yb, [1.0, 0.0, -1.0])
    emp = [d for d in page.get_drawings() if d["type"] == "f" and close(d["fill"], (0.5, 0.5, 0.5)) and len(d["items"]) == 4 and abs(d["rect"].y1 - top.y1) < 25 and d["rect"].y0 < top.y0 + 30]
    if k == 0:
        e = emp[0]
        p = [e["items"][0][1]] + [i[2] for i in e["items"]]
        xl, xr = p[0].x, p[2].x
        edge = lambda a, b, x: a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x)
        lo, hi = (lambda x: fy(edge(p[1], p[2], x))), (lambda x: fy(edge(p[0], p[3], x)))
        fxx = lambda px: fx(px)
        for xv, elo, ehi in ((10.0, 7.08, 7.52), (11.0, 8.2, 8.69)):
            px = xt[0] + (xv - 10.0) * (xt[1] - xt[0])
            assert abs(lo(px) - elo) < 0.05, ("empirical band lower edge (Haring+04)", xv, lo(px))
    lines, polys = {}, {}
    for d in page.get_drawings():
        r = d["rect"]
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        z = next((z for c, z in ZCOL.items() if close(d["color"] if d["type"] == "s" else d["fill"], c)), None)
        if z is None or any(i[0] != "l" for i in d["items"]) or len(d["items"]) < 3:
            continue
        pts = [d["items"][0][1]] + [i[2] for i in d["items"]]
        if d["type"] == "s" and top.contains(pymupdf.Point(cx, cy)) and abs((d.get("width") or 0) - 2.0) < 0.05:
            lines.setdefault(z, []).append(pts)
        if d["type"] == "fs" and bot.contains(pymupdf.Point(cx, cy)):
            polys.setdefault(z, []).append(pts)
    seen = {}
    for z in sorted(lines):
        assert len(lines[z]) == 1 and len(polys.get(z, [])) == 1, (source, run, z, len(lines[z]), len(polys.get(z, [])))
        line, poly = lines[z][0], polys[z][0]
        pts = []
        for p in line:
            dev = sorted({round(fd(q.y), 4) for q in poly if abs(q.x - p.x) < 0.2})
            assert len(dev) == 2, (source, run, z, p.x, dev)
            y = fy(p.y)
            pts.append({"x": round(fx(p.x), 3), "y": round(y, 4), "yLow": round(y + min(dev), 4), "yHigh": round(y + max(dev), 4)})
        assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and all(3.5 < p["y"] < 11 for p in pts), (source, run, z)
        key = tuple((p["x"], p["y"]) for p in pts)
        if key in seen:
            print(f"skipped {run} z={z}: identical to z={seen[key]} (same curve drawn for two redshifts; not verifiable as a separate epoch)")
            continue
        seen[key] = z
        tag = run.lower().replace("-", "").replace(" ", "")
        records.append(vf.record(
            rid=f"habouzit21.{tag}.bh.z{z}", source=source, run=f"{run} (median, Habouzit+21)", relation="bh", z=float(z),
            axes={"xDefinition": "log10 total stellar mass of the host galaxy", "xUnit": "log10(Msun)", "yDefinition": "log10 black hole mass", "yUnit": "log10(Msun)"}, points=pts,
            population="BH-hosting galaxies with M* >= 5e8 Msun (all BHs in the volume)", interval="scatter",
            definitions={"imf": "unspecified", "cosmology": None, "massDefinition": "unspecified", "bhMassMethod": "intrinsic", "population": "all"},
            citation=f"Habouzit et al. 2021, MNRAS 503, 1940 (arXiv:{ARXIV}), median MBH-M* relation of all simulations, z={z}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="time evolution of the median MBH-M* relation (top) and 15th-85th percentile (bottom)", panel=f"{run}, z={z}", sha=sha, member=f"analysis/{PDF.name}", calibration="prediction",
            calib="outlined text: the equally spaced major ticks of each panel (x: 10, 11; y: 10 to 6; lower panel: 1, 0, -1) were assigned the values read from the rendered figure and validated against the lower edge of the grey empirical band (Haring+04: 7.08 and 8.2 at M* = 1e10 and 1e11, matched to 0.05 dex)",
            warning=f"Median M_BH in stellar-mass bins with more than 5 galaxies (coloured line, {run}) and the 15th-85th percentile band (offsets read from the lower panel and added to the median) at z={z}, read from the vector paths of Habouzit et al. 2021; no table exists. "
                    "Bins with 5 or fewer galaxies are drawn in the paper as individual points and are not extracted. Galaxies with M* below 5e8 Msun are excluded. Stellar mass is the total stellar mass of the galaxy as defined by each simulation's galaxy finder."))
for r in records:
    r["definitions"].pop("cosmology")
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "habouzit21-bh.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} MBH-M* median records for {len(PANELS)} simulations from Habouzit+21")
