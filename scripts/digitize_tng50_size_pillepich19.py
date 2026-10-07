import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1902.05553"
DOI = "10.1093/mnras/stz2338"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
MEAS = {(0.79, 0.22, 0.18): ("stellar3d", "TNG50-1 (3D stellar half-mass radius, star-forming galaxies, Pillepich+19)", "log10 median three-dimensional stellar half-mass radius R_stars", "3D radius enclosing half of the stellar mass (aperture 30 pkpc)"),
        (0.18, 0.56, 0.79): ("vband2d", "TNG50-1 (2D face-on V-band half-light radius, star-forming galaxies, Pillepich+19)", "log10 median two-dimensional face-on circularized V-band half-light radius", "face-on circularized 2D radius enclosing half of the V-band light (Johnson V, intrinsic, no dust)")}
records = []


def exp(t):
    return int(t[2:].replace("−", "-"))


for pdf in sorted((SRC / "figures").glob("TNG_L35n2160TNG_sizes_vs_Mstars_sfing_*.pdf")):
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    m = re.search(r"z\s*=\s*([0-9.]+)", page.get_text())
    assert m, pdf.name
    z = round(float(m.group(1).rstrip(".")), 2)
    fr = [f for f in vf.frames(page, 100, 100) if 90 < f.x0 < 100 and f.width > 600][0]
    W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
    xl = [(cx, exp(t)) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cy > fr.y1 and fr.x0 - 3 <= cx <= fr.x1 + 3]
    yl = [(cy, exp(t)) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < fr.x0 and fr.y0 - 3 <= cy <= fr.y1 + 3]
    assert len(xl) >= 4 and len(yl) >= 2, (pdf.name, xl, yl)
    fx = vf.axis_fit_log2(page, fr, "x", xl)[0]
    fy = vf.axis_fit_log2(page, fr, "y", yl)[0]
    for c in vf.curves(page, fr, fx, fy, min_items=8):
        if abs(c["width"] - 4.0) > 0.05 or c["color"] not in MEAS or not c["dashes"].startswith("[]"):
            continue
        slug, run, ydef, sdef = MEAS[c["color"]]
        pts = sorted((round(x, 3), round(y, 4)) for x, y in c["points"] if 6.5 < x < 12.2 and -1 < y < 2)
        pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
        assert len(pts) >= 10, (pdf.name, slug, len(pts))
        if slug == "stellar3d" and z == 4.0:
            v = min(pts, key=lambda q: abs(q[0] - 9.0))[1]
            assert 0.05 < v < 0.45, v
        records.append(vf.record(
            rid=f"pillepich19.tng50.size.{slug}.z{z:g}", source="IllustrisTNG", run=run, relation="size", z=z,
            axes={"xDefinition": "log10 stellar mass within 30 physical kpc", "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": "log10(kpc)"},
            points=pts, population="star-forming galaxies", interval="unspecified",
            definitions={"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "population": "star-forming", "sizeDefinition": sdef, "densityFrame": "unspecified"},
            citation=f"Pillepich et al. 2019, MNRAS 490, 3196 (arXiv:{ARXIV}), median sizes of TNG50 star-forming galaxies", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Median galaxy sizes of TNG50 star-forming galaxies as a function of stellar mass", panel=f"z = {z:g} panel, {slug} line", sha=sha, member=f"figures/{pdf.name}", calibration="prediction",
            calib="x and y: decade labels snapped to ticks and validated by the minor-tick pattern; log axes (sizes in physical kpc)",
            warning=f"Median {sdef} of TNG50-1 star-forming galaxies at z={z:g}, read from the vector line of Pillepich et al. 2019 (the gas and H-alpha size lines, the shaded 16-84% bands, the softening markers and the Shibuya+15 points are not extracted). The paper notes sizes of galaxies at low mass approach the gravitational softening. The cosmology is the published TNG cosmology; it is not restated in this paper's text.", uncertainty=0.02))
assert len(records) >= 4, len(records)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "pillepich19-tng50-size.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} TNG50 size records from Pillepich+19")
