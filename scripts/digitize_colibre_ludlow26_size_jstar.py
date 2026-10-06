import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2603.26200"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "plots" / "size_j_redshift.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 50, 50)
assert len(fs) == 8
ZS = [0.0, 1.0, 2.0, 3.0]
fxs = [vf.axis_fit(page, fs[4 + c], "x")[0] for c in range(4)]


def fy_of(row):
    fr = fs[4 * row]
    ws = sorted(((w[1] + w[3]) / 2, float(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and 25 < (w[0] + w[2]) / 2 < 45 and fr.y0 - 3 <= (w[1] + w[3]) / 2 <= fr.y1 + 3)
    ticks = vf._tick_positions(page, fr, "y")
    return vf.axis_fit(page, fr, "y", labels=[(min(ticks, key=lambda t: abs(t - cy)), v) for cy, v in ws])[0]


fys = [fy_of(0), fy_of(1)]
SF, PA = (0.12, 0.56, 1.0), (0.98, 0.5, 0.45)
ALL = {(0.25, 0.41, 0.88): "sf", (0.86, 0.08, 0.24): "passive"}
REL = {0: ("size", "log10 stellar half-mass radius r_star,50 (3D, bound stellar particles within 50 kpc)", "log10(kpc)"), 1: ("jstar", "log10 stellar specific angular momentum j_star (all bound stellar particles, no aperture)", "log10(kpc km/s)")}
SPOT = {("size", 0.0): (10.0, 0.3, 0.7), ("jstar", 0.0): (10.0, 2.2, 2.8)}
records = []
for row in (0, 1):
    rel, ydef, yunit = REL[row]
    for c, z in enumerate(ZS):
        fr = fs[4 * row + c]
        fx, fy = fxs[c], fys[row]
        mk = {SF: [], PA: []}
        for d in page.get_drawings():
            if d["type"] == "fs" and d["fill"] is not None and tuple(round(v, 2) for v in d["fill"]) in mk and d["color"] == (0.0, 0.0, 0.0) and d.get("width") == 3.0:
                r = d["rect"]
                cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
                if fr.x0 <= cx <= fr.x1 and fr.y0 <= cy <= fr.y1 and not (row == 0 and c < 2 and cy > 125):
                    mk[tuple(round(v, 2) for v in d["fill"])].append((fx(cx), fy(cy)))
        dashed = {ALL[k["color"]]: k for k in vf.curves(page, fr, fx, fy, min_items=15) if k["color"] in ALL and k["width"] == 2.0}
        assert set(dashed) == {"sf", "passive"}, (rel, z, set(dashed))
        sets = [("centrals, star-forming", "cen-sf", sorted(set((round(x, 3), round(y, 4)) for x, y in mk[SF])), "connected circles (centrals)", True),
                ("centrals, passive", "cen-passive", sorted(set((round(x, 3), round(y, 4)) for x, y in mk[PA])), "connected circles (centrals)", True),
                ("all galaxies, star-forming", "all-sf", sorted(dashed["sf"]["points"]), "dashed line (all galaxies)", False),
                ("all galaxies, passive", "all-passive", sorted(dashed["passive"]["points"]), "dashed line (all galaxies)", False)]
        for pop, slug, pts, how, mk_pts in sets:
            pts = [(round(x, 3), round(y, 4)) for x, y in pts]
            pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0]]
            assert len(pts) >= 8 and all(6.5 < x < 12.8 for x, _ in pts), (rel, z, slug, len(pts))
            if slug == "cen-sf" and (rel, z) in SPOT:
                xa, lo, hi = SPOT[(rel, z)]
                yv = min(pts, key=lambda q: abs(q[0] - xa))[1]
                assert lo < yv < hi, (rel, z, yv)
            records.append(vf.record(
                rid=f"ludlow26.colibre.{rel}.{slug}.z{z:g}", source="COLIBRE", run=f"combined L025m5/L050m5, L200m6, L400m7 (Ludlow+26), {pop}", relation=rel, z=z,
                axes={"xDefinition": "log10 stellar mass within 50 kpc (bound stellar particles)", "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": yunit},
                points=pts, population=f"{pop}; star-forming means within 0.5 dex of the redshift-dependent main sequence, passive at least 0.5 dex below", interval="unspecified", connect=True,
                definitions={"massDefinition": "aperture-50pkpc", "imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "population": pop, "densityFrame": "comoving", "sfrStatistic": "median", "jDefinition": "all bound stellar particles relative to the most bound particle" if rel == "jstar" else None, "sizeDefinition": "3D radius enclosing half of M_star within 50 kpc" if rel == "size" else None},
                citation=f"Ludlow et al. 2026, COLIBRE sizes and angular momentum (arXiv:{ARXIV}), size and j_star versus stellar mass at z=0 to 3", doi=f"10.48550/arXiv.{ARXIV}", url=f"https://arxiv.org/abs/{ARXIV}",
                figure="Three-dimensional stellar half-mass radius and stellar specific angular momentum versus stellar mass at z=0, 1, 2, 3", panel=f"{'upper' if row == 0 else 'lower'} panel, z={z:g}, {how}", sha=sha, member="plots/size_j_redshift.pdf", calibration="prediction",
                calib="x: numeric tick labels (bottom row, per column) snapped to ticks; y: numeric tick labels (left column, per row) snapped to ticks; no minus signs occur",
                warning=f"Median {rel.replace('jstar', 'j_star')} of COLIBRE {pop} galaxies at z={z:g}, read from the vector paths of the paper's figure (marker centres for centrals, dashed-line vertices for all galaxies). The median relation combines galaxies from different runs above a resolution-dependent mass limit (L025m5 at z=0 and L050m5 at z>0, L200m6, L400m7). Only bins with at least 25 galaxies are drawn. The 16-84% bands are not extracted. Size units are kpc as labelled (physical or comoving not stated in the figure)."))
for r in records:
    r["definitions"] = {k: v for k, v in r["definitions"].items() if v is not None}
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ludlow26-colibre-size-jstar.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} COLIBRE size and j_star records from Ludlow+26")
