import json
import math
import sys
from pathlib import Path

import pymupdf
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2509.07960"
DOI = "10.1093/mnras/stag740"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
ROOT = Path(__file__).resolve().parent.parent
PDF = SRC / "plots" / "Appendix_apertures.pdf"
CITE = f"Chaikin et al. 2026, MNRAS 548, stag740 (doi:{DOI}; arXiv:{ARXIV}), COLIBRE galaxy stellar mass functions, star formation and quenching"
APERTURES = [("aperture-30pkpc", "30pkpc", "30 pkpc", 30), ("aperture-50pkpc", "50pkpc", "50 pkpc", 50), ("aperture-100pkpc", "100pkpc", "100 pkpc", 100), ("total-bound-subhalo", "all-bound", "all bound particles", None)]
near = lambda c, t, tol=0.02: c is not None and all(abs(a - b) < tol for a, b in zip(c, t))

page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page, 100, 100)[0]
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
exp = lambda t: int(t[2:].replace("−", "-"))
xl = [(cx, exp(t)) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cy > fr.y1 and fr.x0 - 3 <= cx <= fr.x1 + 3]
yl = [(cy, exp(t)) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < fr.x0 and fr.y0 - 3 <= cy <= fr.y1 + 3]
assert len(xl) == 6 and len(yl) == 5, (xl, yl)
fx, _ = vf.axis_fit_log2(page, fr, "x", xl)
fy, _ = vf.axis_fit_log2(page, fr, "y", yl)
# the legend gives the aperture of each colour: one short line per entry, in the order 30, 50, 100 pkpc, all bound
leg = sorted((d["rect"].y0, d["color"]) for d in page.get_drawings() if d["type"] == "s" and d["color"] is not None and abs((d.get("width") or 0) - 2.0) < 0.01 and len(d["items"]) <= 3
             and d["rect"].height < 0.01 and 30 < d["rect"].width < 60 and fr.contains(pymupdf.Point(d["rect"].x0 + 1, d["rect"].y0)))
leg = [c for _, c in leg if not near(c, (0.0, 0.0, 0.0))]
assert len(leg) == 4, leg
curves = {}
for c in vf.curves(page, fr, lambda q: q, lambda q: q, min_items=10):
    if abs(c["width"] - 2.0) < 0.05 and c["dashes"].startswith("[ 2 0 ]") and not near(c["color"], (0.0, 0.0, 0.0)):
        curves[tuple(c["color"])] = c
assert len(curves) == 4, sorted(curves)
records, got = [], {}
for (mdef, slug, label, kpc), col in zip(APERTURES, leg):
    c = next(v for k, v in curves.items() if near(k, col))
    pts = sorted((round(fx(p.x), 3), round(fy(p.y), 4)) for p in c["raw"])
    pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
    got[mdef] = pts
    assert len(pts) >= 20 and all(-5.2 < y < -0.5 for _, y in pts), (mdef, len(pts))
    records.append(vf.record(
        rid=f"chaikin26.colibre.l200m6.gsmf-ap-{slug}.z0", source="COLIBRE", run=f"m6 (L200, {label} aperture, figure)", relation="gsmf", z=0.0,
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function, dn/dlog10(M*) (axis label cMpc^-3), no Eddington-bias scatter added", "yUnit": "log10(cMpc^-3 dex^-1)"},
        points=pts, population="all galaxies", interval="unspecified",
        definitions={"imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "massDefinition": mdef, "densityFrame": "comoving", "population": "all"},
        citation=CITE + f", effect of the stellar-mass aperture on the z=0 stellar mass function ({label})", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="Effect of the aperture on the z=0 galaxy stellar mass function (appendix)",
        panel=f"L200m6, {label}", sha=sha, member="plots/Appendix_apertures.pdf", calibration="prediction", uncertainty=0.02, retrieved="2026-10-14",
        calib="x and y: decade labels snapped to ticks and validated by the minor-tick pattern (log axes)",
        warning=f"z=0 stellar mass function of COLIBRE L200m6 with stellar mass summed over bound particles {'within a 3D spherical aperture of ' + label if kpc else 'with no aperture cut'}, read from the vector paths of Chaikin et al. 2026 (appendix figure on the aperture); "
                "no Eddington-bias scatter is added in this figure. Solid (resolved, at least 10 galaxies per bin) segment only; the dotted ends are not extracted. Within-run aperture comparison: the four records of this figure differ only in the mass definition. Observational overlay not extracted."))
# ground truth: the collaboration's own table (gsmf_raw, L200m6, z=0.0, 0.2 dex bins) gives the 50 pkpc curve exactly
tab = yaml.safe_load((ROOT / "data" / "raw" / "2509.07960.yml").read_text())["COLIBRE_L200m6"]["gsmf_raw"]["z0.0"]
tmap = {round(a, 1): b for a, b in zip(tab["log10_bin_centers"], tab["log10_gsmf_values"]) if b is not None and math.isfinite(b)}
diffs = []
for x, y in got["aperture-50pkpc"]:
    k = round(x, 1)
    if k in tmap and abs(x - k) < 0.02:
        diffs.append(y - tmap[k])
print(f"50 pkpc curve vs released table: {len(diffs)} common bins, max |diff| = {max(abs(d) for d in diffs):.3f} dex, median diff = {sorted(diffs)[len(diffs) // 2]:+.3f}")
assert len(diffs) >= 15 and max(abs(d) for d in diffs) < 0.05, diffs
out = ROOT / "data" / "curves" / "chaikin26-colibre-apertures.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} COLIBRE aperture records from Chaikin+26 vector paths")
for r in records:
    p = r["representation"]["points"]
    print(r["id"], len(p), "logM", p[0]["x"], "->", p[-1]["x"], "logPhi", p[0]["y"], "->", p[-1]["y"])
