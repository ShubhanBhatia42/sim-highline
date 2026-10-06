import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2608.19007"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "Figures" / "massive_galaxies_shmr.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 80, 80)
assert len(fs) == 8
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words") if w[4].startswith("10") and len(w[4]) > 2 and w[4][2:].replace("−", "-").lstrip("-").isdigit()]


def exp(t):
    return int(t[2:].replace("−", "-"))


def cal(fr, axis, below):
    labs = []
    for t, cx, cy in W:
        if axis == "x" and below and 0 < cy - fr.y1 < 25 and fr.x0 - 3 <= cx <= fr.x1 + 3:
            labs.append((cx, exp(t)))
        if axis == "y" and 0 < fr.x0 - cx < 40 and fr.y0 - 3 <= cy <= fr.y1 + 3:
            labs.append((cy, exp(t)))
    return vf.axis_fit_log2(page, fr, axis, labs)[0]


STY = {"[ 3.25 3.25 ] 0": 17.0, "[ 15 3 ] 0": 10.0, "[ 15 3.75 3.75 3.75 ] 0": 0.0}
SPOT = {("sfms", 10.0): (8.0, -0.6, 0.4), ("sfms", 0.0): (9.0, -1.5, -0.4), ("shmr", 10.0): (10.0, -3.0, -2.4), ("shmr", 0.0): (12.0, -1.8, -1.2)}
DEF = {"imf": "unspecified", "cosmology": "unspecified", "massDefinition": "aperture-50pkpc", "densityFrame": "comoving"}
records = []
for rel, fi, xdef, ydef, xunit, yunit, pop in (
        ("sfms", 0, "log10 stellar mass within 50 proper kpc (bound stellar particles)", "log10 median SFR of star-forming galaxies", "log10(Msun)", "log10(Msun/yr)", "star-forming galaxies, sSFR > 0.2 / t_H(z)"),
        ("shmr", 4, "log10 halo mass (subhalo; definition not stated in the figure)", "log10 median stellar-to-halo mass ratio of central subhaloes", "log10(Msun)", "log10(1)", "all central subhaloes")):
    fr = fs[fi]
    below = fs[0] if rel == "sfms" else fs[4]
    labs_x = [(cx, exp(t)) for t, cx, cy in W if 0 < cy - below.y1 < 25 and below.x0 - 3 <= cx < below.x1 - 3]
    fx = vf.axis_fit_log2(page, below, "x", labs_x)[0]
    fy = cal(fr, "y", False)
    cs = [c for c in vf.curves(page, fr, fx, fy, min_items=4) if c["width"] == 2.5 and c["dashes"] in STY]
    got = {STY[c["dashes"]]: c for c in cs}
    assert set(got) == {17.0, 10.0, 0.0}, (rel, set(got))
    for z, c in got.items():
        pts = vf.clip(c["points"], 5.5, 13.5, -6, 3)
        pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
        assert len(pts) >= 3, (rel, z, len(pts))
        if (rel, z) in SPOT:
            xa, lo, hi = SPOT[(rel, z)]
            yv = min(pts, key=lambda q: abs(q[0] - xa))[1]
            assert lo < yv < hi, (rel, z, xa, yv)
        records.append(vf.record(
            rid=f"chaikin26.colibre.{rel}.l200m6.z{z:g}", source="COLIBRE", run="L200m6 (Chaikin+26)", relation=rel, z=z,
            axes={"xDefinition": xdef, "xUnit": xunit, "yDefinition": ydef, "yUnit": yunit},
            points=pts, population=pop, interval="unspecified", definitions=dict(DEF, population=pop),
            citation=f"Chaikin et al. 2026, COLIBRE progenitors of z>10 JWST galaxies (arXiv:{ARXIV}), reference relations in the SFR-M* and SHMR appendix figure", doi=f"10.48550/arXiv.{ARXIV}", url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Redshift evolution of the SFR-M* relation and the stellar-to-halo mass ratio of massive galaxies", panel=f"{'upper' if rel == 'sfms' else 'lower'} row, black reference line at z={z:g}", sha=sha, member="Figures/massive_galaxies_shmr.pdf", calibration="prediction",
            calib="x and y: decade labels (10^n words, minus signs included) snapped to ticks and validated by the minor-tick pattern at log10(2..9); log axes; first column panel used",
            warning=f"Median {'SFR-M* relation of star-forming galaxies (sSFR > 0.2/t_H)' if rel == 'sfms' else 'stellar-to-halo mass ratio of central subhaloes'} of COLIBRE L200m6 at z={z:g}, read from the black reference lines of the paper's appendix figure (the same line is repeated in every panel). The coloured main-progenitor tracks and error bars are not extracted. Cosmology, IMF and the halo-mass definition are not stated near the figure."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "chaikin26-colibre-highz.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} COLIBRE high-redshift SFMS and SHMR records from Chaikin+26")
