import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2403.08853"
DOI = "10.3847/2041-8213/ad4cee"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "Gas_Fraction_z5_z12.pdf"
COLORS = {5: (0.0, 0.0, 1.0), 7: (0.0, 0.5, 0.0), 9: (1.0, 0.65, 0.0), 12: (1.0, 0.0, 0.0)}
near = lambda c, t, tol=0.02: c is not None and all(abs(a - b) < tol for a, b in zip(c, t))

page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = min(vf.frames(page, 400, 400), key=lambda r: (r.x0, r.y0))
assert abs(fr.width - 521.7) < 1 and abs(fr.height - 484.1) < 1, fr
words = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
yt = vf._tick_positions(page, fr, "y")
zero = next(cy for t, cx, cy in words if t == "0.0" and cx < fr.x0)
ylabs = [(min(yt, key=lambda q: abs(q - cy)), (1 if cy < zero - 1 else -1) * float(t)) for t, cx, cy in words if t in ("0.5", "1.0", "1.5", "2.0") and cx < fr.x0 and fr.y0 - 5 < cy < fr.y1 + 5]
ylabs.append((min(yt, key=lambda q: abs(q - zero)), 0.0))
assert len(ylabs) == 8, ylabs
fx, xt = vf.axis_fit(page, fr, "x")
fy, _ = vf.axis_fit(page, fr, "y", labels=ylabs)
drawings = page.get_drawings()
legend = lambda r: r.x0 > fr.x0 + 0.7 * fr.width and r.y0 < fr.y0 + 0.4 * fr.height
AX = {"xDefinition": "log10 stellar mass (within 0.2 Rvir)", "xUnit": "log10(Msun)", "yDefinition": "log10 gas-to-stellar mass ratio Mgas/M* (total gas and stellar mass within 0.2 Rvir)", "yUnit": "dex"}
DEF = {"imf": "kroupa01", "cosmology": {"H0": 67.66, "Om": 0.3111}, "massDefinition": "aperture-0.2Rvir", "gasDefinition": "total gas mass within 0.2 Rvir", "gasStatistic": "median",
       "population": "central galaxies of the zoom suite, M* > 1e6 Msun"}
SPOT = {5: (6.4, 0.5, 1.0), 12: (6.3, 0.9, 1.5)}
records = []
for z, col in COLORS.items():
    sq = sorted((d for d in drawings if d["type"] == "fs" and near(d["fill"], col) and abs(d["rect"].width - 8.0) < 0.2 and abs(d["rect"].height - 8.0) < 0.2
                 and fr.x0 <= (d["rect"].x0 + d["rect"].x1) / 2 <= fr.x1 and fr.y0 <= (d["rect"].y0 + d["rect"].y1) / 2 <= fr.y1 and not legend(d["rect"])), key=lambda d: d["rect"].x0)
    bars = [(it[1].x, min(it[1].y, it[2].y), max(it[1].y, it[2].y)) for d in drawings if d["type"] == "s" and near(d["color"], col) and abs((d.get("width") or 0) - 1.5) < 0.01
            for it in d["items"] if it[0] == "l" and abs(it[1].x - it[2].x) < 0.01 and fr.x0 < it[1].x < fr.x1]
    assert len(sq) >= 3, (z, len(sq))
    pts = []
    for d in sq:
        r = d["rect"]
        mx, my = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        b = [t for t in bars if abs(t[0] - mx) < 0.3 and t[1] - 0.5 <= my <= t[2] + 0.5]
        assert len(b) == 1, (z, mx, my, b)
        p = {"x": round(fx(mx), 3), "y": round(fy(my), 4)}
        if b[0][1] > fr.y0 + 0.5:
            p["yHigh"] = round(fy(b[0][1]), 4)
        if b[0][2] < fr.y1 - 0.5:
            p["yLow"] = round(fy(b[0][2]), 4)
        pts.append(p)
    assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and all(p.get("yLow", p["y"]) <= p["y"] <= p.get("yHigh", p["y"]) for p in pts), z
    if z in SPOT:
        xa, lo, hi = SPOT[z]
        q = min(pts, key=lambda t: abs(t["x"] - xa))
        assert abs(q["x"] - xa) < 0.2 and lo < q["y"] < hi, (z, q)
    records.append(vf.record(
        rid=f"marszewski24.fire2.gas.z{z}", source="FIRE-2", run="FIRE-2 high-z zooms (Marszewski+24 medians)", relation="gas", z=float(z), axes=AX, points=pts, population="central galaxies of the zoom suite",
        interval="scatter", definitions=dict(DEF), citation=f"Marszewski et al. 2024, ApJL 967, L41 (arXiv:{ARXIV}), gas fractions in stellar mass bins, z={z}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Gas fraction Mgas/M* in stellar mass bins (left panel)", panel=f"z={z}", sha=sha, member=PDF.name, calibration="prediction", uncertainty=0.02, retrieved="2026-10-14",
        calib="x: labelled decades 6-10 snapped to ticks; y: labelled ticks -1.5 to 2.0 (signs set from the position of 0.0) snapped to ticks; both linear",
        warning=f"Median gas fraction Mgas/M* of the FIRE-2 high-redshift zoom galaxies at z={z} in stellar mass bins with at least five galaxies (solid squares, left panel), read from the vector paths of Marszewski et al. 2024; no table exists. "
                "Error bars are the plotted 16th-84th percentiles of the galaxies in the bin (a scatter, not an error of the median); where a bar runs off the plotted range its end is not recorded. Mass and gas are within 0.2 Rvir of central galaxies with M* > 1e6 Msun (satellites and halos contaminated by low-resolution particles excluded). "
                "The individual galaxies, the open squares (bins with fewer than five galaxies), the authors' best-fit lines and the Mgas/(M*+Mgas) panel are not extracted. Zoom-in sample, not a volume."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "marszewski24-fire2-gas.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIRE-2 gas-fraction records from Marszewski+24 vector paths")
for r in records:
    print(r["id"], [(p["x"], p["y"], p.get("yLow"), p.get("yHigh")) for p in r["representation"]["points"]])
