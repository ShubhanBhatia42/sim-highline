import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2309.03269"
DOI = "10.21105/astro.2309.03269"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "figures" / "uvlf_sphinx20.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 60, 60)
assert len(fs) == 2
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
fx, _ = vf.axis_fit(page, fs[1], "x")


def yfit(fr):
    labs = [(cy, int(t[2:].replace("−", "-"))) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < fr.x0 and fr.y0 + 2 <= cy <= fr.y1 + 2]
    assert len(labs) == 5, labs
    return vf.axis_fit_log2(page, fr, "y", labs)[0]


PAN = [({(0.28, 0.51, 0.71): 4.64, (0.74, 0.72, 0.42): 6.0, (1.0, 0.65, 0.0): 8.0, (0.5, 0.0, 0.0): 10.0}, fs[0]), ({(0.53, 0.81, 0.92): 5.0, (0.0, 0.39, 0.0): 7.0, (0.8, 0.36, 0.36): 9.0}, fs[1])]
SPOT = {4.64: (-19.0, -3.2, -1.5), 10.0: (-18.0, -5.0, -2.5)}
records = []
for cmap, fr in PAN:
    fy = yfit(fr)
    for c in vf.curves(page, fr, fx, fy, min_items=15):
        z = cmap.get(c["color"])
        if z is None or abs(c["width"] - 1.0) > 0.05 or len(c["points"]) < 15:
            continue
        pts = sorted((round(x, 3), round(y, 4)) for x, y in c["points"] if -24 < x < -15.5 and -7 < y < -1)
        pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
        assert len(pts) >= 12, (z, len(pts))
        if z in SPOT:
            xa, lo, hi = SPOT[z]
            v = min(pts, key=lambda q: abs(q[0] - xa))[1]
            assert lo < v < hi, (z, v)
        records.append(vf.record(
            rid=f"katz23.sphinx20.uvlf.z{z:g}", source="SPHINX20", run="SPHINX20 (UV luminosity function, mean over ten viewing angles, Katz+23)", relation="uvlf", z=z,
            axes={"xDefinition": "absolute UV magnitude M_UV (rest-frame 1500 A, AB)", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"},
            points=pts, population="SPHINX20 galaxies with SFR_10 >= 0.3 Msun/yr (the data-release selection)", interval="unspecified",
            definitions={"imf": "unspecified", "cosmology": "unspecified", "densityFrame": "comoving", "uvBand": "rest-frame 1500 A, AB", "dustCorrection": "dust radiative transfer, mean over ten viewing angles (inferred from the paper's statement that all galaxy emission is dust-processed; the caption does not say attenuated)", "population": "galaxies above the data-release SFR threshold"},
            citation=f"Katz et al. 2023, OJAp 6 (arXiv:{ARXIV}), UV luminosity function of SPHINX20 galaxies", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="UV luminosity function for SPHINX20 galaxies at different redshifts", panel=f"z = {z:g} curve ({'upper' if fr is fs[0] else 'lower'} panel)", sha=sha, member="figures/uvlf_sphinx20.pdf", calibration="prediction",
            calib="x: numeric tick labels (minus glyphs included) from the lower panel snapped to ticks and shared by both panels; y: decade labels per panel validated by the minor-tick pattern (log10); curve colours matched to redshifts through the legend swatches",
            warning=f"Mean UV luminosity function of SPHINX20 at z={z:g} (mean over ten viewing angles), read from the vector line of Katz et al. 2023; the standard-deviation bands and observational points are not extracted. The paper notes the bright cutoff reflects the finite box and the faint downturn the SFR threshold of 0.3 Msun/yr, so the faint end is incomplete by construction.", uncertainty=0.02))
assert sorted(r["epoch"]["zRepresentative"] for r in records) == [4.64, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0], [r["id"] for r in records]
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "katz23-sphinx20-uvlf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} SPHINX20 UV luminosity function records from Katz+23")
