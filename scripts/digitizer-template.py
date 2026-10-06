"""Template for a new vector-figure digitizer. Copy to scripts/digitize_<suite>_<paper>_<what>.py and edit the CONFIG block.
It is not picked up by regress_digitizers.py until it is renamed to start with digitize_."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "0000.00000"
DOI = "10.0000/placeholder"
FIGURE_PDF = "figure.pdf"
RELATION = "gsmf"
Z = 0.0
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / FIGURE_PDF
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
fx, xt = vf.axis_fit(page, fr, "x")
fy, yt = vf.axis_fit(page, fr, "y")
curves = [c for c in vf.curves(page, fr, fx, fy, min_items=8)]
assert len(curves) == 1, len(curves)
pts = vf.clip(curves[0]["points"], -100, 100, -100, 100)
assert all(a[0] < b[0] for a, b in zip(pts, pts[1:]))
assert 0 < len(pts), "spot-check: compare two plotted values with the numbers you read from the figure and assert them here"
rec = vf.record(
    rid="author00.suite.relation.z0", source="SUITE", run="RUN", relation=RELATION, z=Z,
    axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 number density per dex", "yUnit": "log10(cMpc^-3 dex^-1)"},
    points=pts, population="all galaxies", interval="unspecified",
    definitions={"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "massDefinition": "unspecified", "population": "all", "densityFrame": "comoving"},
    citation=f"Author et al. YEAR, JOURNAL VOLUME, PAGE (arXiv:{ARXIV}), figure description", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
    figure="figure caption", panel="panel", sha=sha, member=FIGURE_PDF, calibration="prediction",
    calib="x and y: numeric tick labels snapped to tick marks",
    warning="What the curve is, what it is not, anything not extracted.")
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "author00-suite-relation.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print("Wrote 1 record")
