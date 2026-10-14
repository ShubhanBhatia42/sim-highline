import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2205.15325"
DOI = "10.1093/mnras/stad1205"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "fig6.pdf"
CITE = f"Feldmann et al. 2023, MNRAS 522, 3831 (arXiv:{ARXIV}), FIREbox galaxy properties"
SETS = {"all": ((0.7, 0.13, 0.13), "all galaxies"), "cen": ((0.27, 0.51, 0.71), "central galaxies"), "sat": ((0.0, 0.5, 0.5), "satellite galaxies")}
near = lambda c, t, tol=0.02: c is not None and all(abs(a - b) < tol for a, b in zip(c, t))

page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page, 100, 60)[0]
drawings = page.get_drawings()
words = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
segs = [(it[1], it[2]) for d in drawings for it in d["items"] if it[0] == "l"]
# ticks straddle the axis lines here (drawn in and out), which the shared tick finder does not accept
xticks = sorted({round(a.x, 2) for a, b in segs if abs(a.x - b.x) < 0.05 and 3 < abs(a.y - b.y) < 10 and abs((a.y + b.y) / 2 - fr.y1) < 1.0})
yticks = sorted({round(a.y, 2) for a, b in segs if abs(a.y - b.y) < 0.05 and 3 < abs(a.x - b.x) < 10 and abs((a.x + b.x) / 2 - fr.x0) < 1.0})
snap = lambda ticks, p: min(ticks, key=lambda t: abs(t - p))
xl = [(snap(xticks, cx), float(t)) for t, cx, cy in words if t in ("8.0", "8.5", "9.0", "9.5", "10.0", "10.5", "11.0", "11.5") and cy > fr.y1]
yl = [(snap(yticks, cy), float(t)) for t, cx, cy in words if t in ("0.0", "0.2", "0.4", "0.6", "0.8", "1.0") and cx < fr.x0]
assert len(xl) == 8 and len(yl) == 6, (xl, yl)


def linfit(pairs):
    n = len(pairs)
    mp, mv = sum(p for p, _ in pairs) / n, sum(v for _, v in pairs) / n
    b = sum((p - mp) * (v - mv) for p, v in pairs) / sum((p - mp) ** 2 for p, _ in pairs)
    a = mv - b * mp
    assert all(abs(a + b * p - v) < 0.002 * abs(pairs[-1][1] - pairs[0][1]) + 1e-9 for p, v in pairs), pairs
    return lambda p: a + b * p


fx, fy = linfit(sorted(xl)), linfit(sorted(yl))
inside = lambda r: fr.x0 - 0.5 <= (r.x0 + r.x1) / 2 <= fr.x1 and fr.y0 <= (r.y0 + r.y1) / 2 <= fr.y1
legend = lambda r: (r.x0 + r.x1) / 2 < fr.x0 + 130 and (r.y0 + r.y1) / 2 < fr.y0 + 120
AX = {"xDefinition": "log10 galaxy stellar mass", "xUnit": "log10(Msun)", "yDefinition": "quiescent fraction: fraction of galaxies in the stellar mass bin with sSFR below the threshold (sSFR averaged over the last 100 Myr)", "yUnit": "fraction"}
SPOT = {"all": (8.0, 0.4, 0.6), "cen": (8.0, 0.4, 0.55), "sat": (8.0, 0.5, 0.7)}
records = []
for key, (col, pop) in SETS.items():
    mk = sorted((d for d in drawings if d["type"] == "fs" and near(d["fill"], col) and d.get("fill_opacity") is not None and abs(d["fill_opacity"] - 0.8) < 0.01
                 and 3 < d["rect"].width < 12 and inside(d["rect"]) and not legend(d["rect"])), key=lambda d: d["rect"].x0)
    assert len(mk) >= 7, (key, len(mk))
    bars = [(it[1].x, min(it[1].y, it[2].y), max(it[1].y, it[2].y)) for d in drawings if d["type"] == "s" and near(d["color"], col) and d.get("stroke_opacity") is not None and abs(d["stroke_opacity"] - 0.8) < 0.01
            and d["rect"].width < 0.05 and d["rect"].height > 0.5 for it in d["items"] if it[0] == "l"]
    solid = []
    for d in mk:
        r = d["rect"]
        mx, my = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        b = [t for t in bars if abs(t[0] - mx) < 0.3 and t[1] - 0.5 <= my <= t[2] + 0.5]
        assert len(b) == 1, (key, mx, my, b)
        solid.append({"x": round(fx(mx), 3), "y": round(fy(my), 4) + 0.0, "yLow": round(max(fy(b[0][2]), 0.0), 4) + 0.0, "yHigh": round(min(fy(b[0][1]), 1.0), 4) + 0.0, "_px": mx})
    assert all(a["x"] < b["x"] for a, b in zip(solid, solid[1:])) and all(p["yLow"] - 1e-4 <= p["y"] <= p["yHigh"] + 1e-4 for p in solid), key
    xa, lo, hi = SPOT[key]
    first = solid[0]
    assert abs(first["x"] - xa) < 0.1 and lo < first["y"] < hi, (key, first)
    dotted = [d for d in drawings if d["type"] == "s" and near(d["color"], col) and d["dashes"] and d["dashes"].startswith(("[ 2 3.3 ]", "[ 1.5 2.475 ]")) and len(d["items"]) >= 5 and not legend(d["rect"])]
    assert len(dotted) == 1, (key, len(dotted))
    dv = [dotted[0]["items"][0][1]] + [it[-1] for it in dotted[0]["items"]]
    kept = []
    for p in solid:
        m = [v for v in dv if abs(v.x - p["_px"]) < 0.3]
        assert len(m) == 1, (key, p["x"], len(m))
        kept.append({"x": p["x"], "y": round(fy(m[0].y), 4) + 0.0})
    assert all(a["x"] < b["x"] for a, b in zip(kept, kept[1:])) and all(-0.01 <= p["y"] <= 1.01 for p in kept), key
    for p in solid:
        del p["_px"]
    for tag, crit, run_thr, pts, interval in (("ssfr10p5", "ssfr<10^-10.5", "sSFR<10^-10.5", solid, "uncertainty"), ("ssfr11", "ssfr<1e-11", "sSFR<1e-11", kept, "unspecified")):
        what = ("Solid line and markers of the quiescent-fraction figure (threshold sSFR < 10^-10.5 /yr) with the plotted 16-84 per cent bootstrap error bars; bins with fewer than four galaxies (light shaded symbols without error bars) are not recorded."
                if tag == "ssfr10p5" else
                "Dotted line of the quiescent-fraction figure (threshold sSFR < 10^-11 /yr), no error bars drawn; only the bins that have at least four galaxies in the solid-marker series are recorded.")
        records.append(vf.record(
            rid=f"feldmann23.firebox.quenched.{key}-{tag}.z0", source="FIREbox", run=f"FIREbox (FB1024, 22.1 cMpc box), {pop}, {run_thr}", relation="quenched", z=0.0, axes=AX, points=pts, population=pop, interval=interval,
            definitions={"imf": "kroupa01", "cosmology": {"H0": 67.74, "Om": 0.3089}, "massDefinition": "unspecified", "population": pop, "quenchingCriterion": crit, "sfrTimescaleMyr": 100},
            citation=CITE + f", quiescent fraction ({pop}, {run_thr})", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="Fraction of quiescent galaxies at z=0 (fig6.pdf)", panel=f"{pop}, {run_thr}", sha=sha, member="fig6.pdf",
            calibration="prediction", uncertainty=0.01, retrieved="2026-10-14",
            calib="x and y: numeric tick labels snapped to ticks (linear axes)",
            warning=f"FIREbox quiescent fraction at z=0 for {pop}. {what} A galaxy is quiescent when its sSFR averaged over the last 100 Myr is below the threshold. "
                    "The stellar-mass aperture is not restated for this figure (the paper defines galaxy stellar mass as the mass within R_g = 3 R_half elsewhere). The observational and empirical overlays (Leja+21, Behroozi+19) are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "feldmann23-firebox-quenched.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIREbox quiescent-fraction records from Feldmann+23 vector paths")
for r in records:
    p = r["representation"]["points"]
    print(r["id"], len(p), "logM", p[0]["x"], "->", p[-1]["x"], "qf", p[0]["y"], "->", p[-1]["y"])
