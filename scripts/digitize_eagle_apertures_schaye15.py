import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1407.7040"
DOI = "10.1093/mnras/stu2058"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
ROOT = Path(__file__).resolve().parent.parent
PDF = SRC / "mf_ref100_only_apertures.pdf"
CITE = f"Schaye et al. 2015, MNRAS 446, 521 (doi:{DOI}; arXiv:{ARXIV}), the EAGLE simulations"
# legend of the figure (text is outlined, read by eye at 5x zoom): colour -> aperture. The caption in the arXiv source says 30, 50 and 100 pkpc; the legend, which is what is drawn, says 10, 30 and 100.
LINES = [((0.53, 0.8, 0.93), "aperture-10pkpc", "10pkpc", "3D spherical aperture of 10 pkpc"), ((0.2, 0.13, 0.53), "aperture-30pkpc", "30pkpc", "3D spherical aperture of 30 pkpc"),
         ((0.27, 0.67, 0.6), "aperture-100pkpc", "100pkpc", "3D spherical aperture of 100 pkpc"), ((0.07, 0.47, 0.2), "petrosian-2D", "petrosian", "2D circular Petrosian aperture (R_P)"),
         ((0.8, 0.4, 0.47), "total-bound-subhalo", "all-bound", "no aperture (all stellar mass bound to the subhalo)")]
near = lambda c, t, tol=0.02: c is not None and all(abs(a - b) < tol for a, b in zip(c, t))

page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frame_from_long_lines(page, 100)
segs = [(it[1], it[2]) for d in page.get_drawings() for it in d["items"] if it[0] == "l"]
# the text is outlined, so the axes are calibrated on the major ticks (the longer ticks at the frame edge) whose values follow from the axis ranges 7 to 12.5 and -5 to -0.5 and the regular spacing
xmaj = sorted({round(a.x, 2) for a, b in segs if abs(a.x - b.x) < 0.05 and 7 < abs(a.y - b.y) < 8.5 and abs(max(a.y, b.y) - fr.y1) < 1})
ymaj = sorted({round(a.y, 2) for a, b in segs if abs(a.y - b.y) < 0.05 and 8 < abs(a.x - b.x) < 9 and abs(min(a.x, b.x) - fr.x0) < 1})
assert len(xmaj) == 6 and len(ymaj) == 5, (xmaj, ymaj)
assert max(abs(b - a - (xmaj[-1] - xmaj[0]) / 5) for a, b in zip(xmaj, xmaj[1:])) < 0.1 and max(abs(b - a - (ymaj[-1] - ymaj[0]) / 4) for a, b in zip(ymaj, ymaj[1:])) < 0.1
px, py = (xmaj[-1] - xmaj[0]) / 5, (ymaj[-1] - ymaj[0]) / 4
assert abs(fr.x0 - xmaj[0]) < 0.1 and abs(fr.y1 - ymaj[-1]) < 0.1 and abs((fr.x1 - fr.x0) / px - 5.5) < 0.05, (fr, px)
fx = lambda p: 7.0 + (p - xmaj[0]) / px
fy = lambda p: -5.0 + (ymaj[-1] - p) / py  # page y grows downwards: the bottom major tick is -5 and a dex spans py points
assert abs(fy(ymaj[0]) - -1.0) < 1e-6 and abs(fx(xmaj[-1]) - 12.0) < 1e-6, (fy(ymaj[0]), fx(xmaj[-1]))
solid = {}
for c in vf.curves(page, fr, lambda q: q, lambda q: q, min_items=8):
    if abs(c["width"] - 2.83) < 0.05 and c["dashes"].startswith("[]"):
        solid[tuple(c["color"])] = c
assert len(solid) == 5, sorted(solid)
records, got = [], {}
for col, mdef, slug, what in LINES:
    c = next(v for k, v in solid.items() if near(k, col))
    pts = sorted((round(fx(p.x), 3), round(fy(p.y), 4)) for p in c["raw"])
    pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
    got[mdef] = pts
    assert len(pts) >= 14 and all(-5.0 < y < -0.4 for _, y in pts) and all(a[1] >= b[1] - 0.02 for a, b in zip(pts, pts[1:])), (mdef, pts[:3])
    records.append(vf.record(
        rid=f"schaye15.eagle-ref-l100n1504.gsmf-ap-{slug}.z0.1", source="EAGLE", run=f"Ref-L100N1504 ({what.split(' (')[0]}, figure)", relation="gsmf", z=0.1,
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function, dn/dlog10(M*) (axis label cMpc^-3)", "yUnit": "log10(cMpc^-3 dex^-1)"},
        points=pts, population="all galaxies", interval="unspecified",
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "massDefinition": mdef, "densityFrame": "comoving", "population": "all"},
        citation=CITE + f", effect of the aperture on the stellar mass function ({what})", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="The effect of the choice of aperture on the GSMF", panel=f"Ref-L100N1504, z=0.1, {what}",
        sha=sha, member="mf_ref100_only_apertures.pdf", calibration="prediction", uncertainty=0.02, retrieved="2026-10-14",
        calib="x and y: the six and five major tick marks, whose values follow from the axis ranges (7 to 12.5 and -5 to -0.5) and the regular spacing; the text is outlined",
        warning=f"z=0.1 stellar mass function of EAGLE Ref-L100N1504 with stellar mass bound to the subhalo measured within a {what}, read from the vector paths of Schaye et al. 2015 (figure on the aperture). "
                "The legend of the figure lists 10, 30 and 100 pkpc spherical apertures, a circular Petrosian aperture and no aperture; the caption in the arXiv source says 30, 50 and 100 pkpc, and the legend, which is what is drawn, is used here. "
                "Solid segment only (the dotted low-mass end, fewer than 100 stellar particles, and the dashed high-mass end, fewer than 10 galaxies per bin, are not extracted). Within-run aperture comparison: the records of this figure differ only in the mass definition. Observational points not extracted."))
# independent check: the 30 pkpc curve against the EAGLE Ref-L100N1504 z=0.1 record that comes from another paper (Furlong+15)
ref = next(r for r in json.loads((vf.reference_root() / "data" / "curves" / "furlong15-eagle-gsmf.json").read_text())["records"] if r["id"] == "furlong15.eagle-ref.gsmf.z0.1")
rp = [(p["x"], p["y"]) for p in ref["representation"]["points"]]
interp = lambda pts, x: next((y0 + (y1 - y0) * (x - x0) / (x1 - x0) for (x0, y0), (x1, y1) in zip(pts, pts[1:]) if x0 <= x <= x1), None)
diffs = [(x, y - interp(rp, x)) for x, y in got["aperture-30pkpc"] if interp(rp, x) is not None]
print(f"30 pkpc curve vs Furlong+15 EAGLE record: {len(diffs)} shared points, max |diff| = {max(abs(d) for _, d in diffs):.3f} dex, median = {sorted(d for _, d in diffs)[len(diffs) // 2]:+.3f}")
assert len(diffs) >= 8 and max(abs(d) for _, d in diffs) < 0.08, diffs
out = ROOT / "data" / "curves" / "schaye15-eagle-apertures.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE aperture records from Schaye+15 vector paths")
for r in records:
    p = r["representation"]["points"]
    print(r["id"], len(p), "logM", p[0]["x"], "->", p[-1]["x"], "logPhi", p[0]["y"], "->", p[-1]["y"])
