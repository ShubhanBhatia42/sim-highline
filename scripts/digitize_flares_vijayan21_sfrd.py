import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2008.06057"
DOI = "10.1093/mnras/staa3715"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "figures" / "sfrd.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page, 100, 100)[0]
fx, _ = vf.axis_fit(page, fr, "x")
fy, _ = vf.axis_fit(page, fr, "y")
KINDS = {(0.0, 0.0, 0.0): ("total", "total star formation", "Total"), (0.0, 0.5, 0.0): ("unobscured", "unobscured (UV) star formation", "Unobscured/UV"), (1.0, 0.0, 0.0): ("obscured", "obscured (IR) star formation", "Obscured/IR")}
SPOT = {"total": (5.0, -1.8, -1.5), "unobscured": (5.0, -2.2, -1.8), "obscured": (10.0, -3.8, -3.3)}
records = []
for c in vf.curves(page, fr, fx, fy, min_items=5):
    if c["color"] not in KINDS or abs(c["width"] - 1.2) > 1e-3 or len(c["points"]) != 6:
        continue
    slug, what, label = KINDS[c["color"]]
    pts = [(round(x, 3), round(y, 4)) for x, y in c["points"]]
    assert [round(x) for x, _ in pts] == [5, 6, 7, 8, 9, 10] and all(abs(x - round(x)) < 0.01 for x, _ in pts), pts
    z0, lo, hi = SPOT[slug]
    assert lo < dict((round(x), y) for x, y in pts)[int(z0)] < hi, (slug, pts)
    records.append(vf.record(
        rid=f"vijayan21.flares.sfrd.{slug}", source="FLARES", run=f"40 resimulated regions (EAGLE AGNdT9 model), {slug} SFR density (Vijayan+21)", relation="sfrd", z=7.5,
        axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": f"log10 cosmic star formation rate density, {what}", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
        points=pts, population=f"all galaxies in the weighted combination of the regions, {what}", interval="unspecified", z_range=(5.0, 10.0),
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "densityFrame": "comoving", "sfrIndicator": f"intrinsic SFR split by the dust model: {what}", "dustCorrection": "none" if slug != "unobscured" else "unobscured (UV-visible) fraction only", "population": "all galaxies"},
        citation=f"Vijayan et al. 2021, MNRAS (doi 10.1093/mnras/staa3715; arXiv:{ARXIV}), composite star formation rate density", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="FLARES composite total, obscured and unobscured star formation rate density, z 5 to 10", panel=f"{label} line", sha=sha, member="figures/sfrd.pdf", calibration="prediction",
        calib="x: numeric tick labels snapped to ticks; y: numeric tick labels (with minus glyphs) snapped to ticks",
        warning=f"FLARES composite (weighted) {what} density at z=5 to 10, one value per integer redshift read from the vector line of Vijayan et al. 2021. The Bouwens+20 and Khusanova+20 points are not extracted. The paper's dust model defines the obscured and unobscured split.",
        uncertainty=0.02, strict=True))
assert len(records) == 3
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "vijayan21-flares-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print("Wrote 3 FLARES SFR density records from Vijayan+21")
