import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1510.05645"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = next(SRC.rglob("size_mass_simcomp.pdf"))
BINS = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0)]
POP = {(0.2, 0.13, 0.53): ("active", "active (sSFR above the redshift-dependent limit)"), (0.53, 0.13, 0.33): ("passive", "passive (sSFR below the redshift-dependent limit)")}
AX = {"xDefinition": "log10 stellar mass (within 2 x half-mass radius)", "xUnit": "log10(Msun)", "yDefinition": "log10 physical 3D stellar half-mass radius (public Illustris catalogue)", "yUnit": "log10(kpc)"}


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)
assert len(fr) == 4
fx, xt = vf.axis_fit(page, fr[2], "x")
fy, yt = vf.axis_fit(page, fr[0], "y")
assert [v for _, v in xt] == [9.0, 10.0, 11.0, 12.0] and [v for _, v in yt] == [1.5, 1.0, 0.5, 0.0]
words = page.get_text("words")
records = []
for i, ((lo, hi), r) in enumerate(zip(BINS, fr)):
    xr = vf.shifted(fx, fr[2 + i % 2].x0 - fr[2].x0)
    fyr = vf.shifted(fy, r.y0 - fr[0].y0)
    nums = sorted(float(w[4]) for w in words if re.fullmatch(r"\d\.\d", w[4]) and r.x0 + 30 < (w[0] + w[2]) / 2 < r.x1 and r.y0 < (w[1] + w[3]) / 2 < r.y0 + 40)
    assert nums[:2] == [lo, hi], (i, nums)
    cs = [c for c in vf.curves(page, r, xr, fyr, min_items=6) if c["width"] == 2.0 and c["dashes"] == "[ 6 6 ] 0" and any(near(c["color"], k) for k in POP)]
    assert len(cs) == 2, (i, len(cs))
    for c in cs:
        key, desc = POP[next(k for k in POP if near(c["color"], k))]
        pts = [(x, y) for x, y in c["points"] if xr(r.x0) <= x <= xr(r.x1) and -0.6 <= y <= 1.6]
        records.append(vf.record(
            rid=f"furlong17.illustris-1.size-{key}.z{lo:g}-{hi:g}", source="Illustris", run=f"Illustris-1 ({key})", relation="size", z=(lo + hi) / 2, z_range=(lo, hi), axes=AX, points=pts, population=f"{desc} galaxies",
            warning=f"Dashed Illustris median curve read from the vector paths of the EAGLE-versus-Illustris size-mass comparison in the appendix of Furlong et al. 2017 ({lo:g}<z<{hi:g} panel); no table exists, no percentile band is drawn. "
                    "Redshift bins, so the epoch is the bin with its midpoint as representative. Half-mass radii, masses and SFRs were taken from the public Illustris data release; stellar mass and SFR use an aperture of twice the half-mass radius. "
                    "Active and passive split at log10(sSFR_lim/Gyr^-1) = 0.5z - 2, as for EAGLE. Curve clipped to the plotted axis range.",
            definitions={"massDefinition": "aperture-2rhalf-stars", "imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.2726}, "sizeDefinition": "stellar-half-mass-3d-subhalo", "population": key,
                         "quenchingCriterion": "log10 sSFR_lim(z)/Gyr^-1 = 0.5z - 2"},
            citation=f"Furlong et al. 2017, MNRAS 465, 722, appendix comparison (size_mass_simcomp; arXiv source numbering), {lo:g}<z<{hi:g} panel", doi="10.1093/mnras/stw2740", url=f"https://arxiv.org/abs/{ARXIV}",
            figure="appendix size-mass comparison (fig:simcomp)", panel=f"{lo:g}<z<{hi:g}", sha=sha, member=f"{PDF.name} (Illustris {key} dashed curve)",
            calib="x: labelled ticks 9-12 (bottom-left panel); y: labelled ticks 0-1.5 (top-left panel); labels asserted", calibration="prediction"))
assert len(records) == 8
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "furlong17-illustris-sizes.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Illustris size-mass records (active/passive, 4 redshift bins) from the Furlong+17 appendix figure")
