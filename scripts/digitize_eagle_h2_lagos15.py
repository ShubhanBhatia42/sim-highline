import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1503.04807"
DOI = "10.1093/mnras/stv1488"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
EPS = next(SRC.rglob("EAGLE_H2MstellarScaling_COLDGASS2.eps"))
PDF = SRC / "pdf" / EPS.with_suffix(".pdf").name
if not PDF.exists():
    PDF.parent.mkdir(exist_ok=True)
    subprocess.run(["epstopdf", str(EPS), f"--outfile={PDF}"], check=True)
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frame_from_long_lines(page, 50)
fx, xt = vf.axis_fit(page, fr, "x")
fy, yt = vf.axis_fit(page, fr, "y")
assert len(xt) >= 4 and len(yt) >= 5
RUNS = [("Ref-L100N1504 (GK11)", (0.0, 0.0, 0.0), 1.7, "[] 0", "GK11", "median H2 fraction of galaxies with M*>1e10 Msun above the COLD GASS detection limit, GK11 prescription"),
        ("Recal-L025N0752 (GK11)", (0.0, 0.0, 1.0), 2.27, "[ 5.6693 5.6693 ] 0", "GK11", "median H2 fraction of galaxies with M*>1e10 Msun above the COLD GASS detection limit, GK11 prescription, Recal-L025N0752"),
        ("Ref-L100N1504 (K13)", (0.91, 0.58, 0.0), 2.6, "[ 11.3386 5.6693 ] 0", "K13", "median H2 fraction of galaxies with M*>1e10 Msun above the COLD GASS detection limit, K13 prescription")]
conv = lambda y: math.log10(10 ** y / (1 - 10 ** y))
records = []
for run, col, lw, dash, method, what in RUNS:
    lines = [d for d in page.get_drawings() if d["type"] == "s" and d["color"] and all(abs(a - b) < 0.02 for a, b in zip(d["color"], col)) and abs((d.get("width") or 0) - lw) < 0.05 and d["dashes"] == dash and len(d["items"]) >= 4]
    assert len(lines) == 1, (run, len(lines))
    its = lines[0]["items"]
    pts = [(fx(p.x), fy(p.y)) for p in [its[0][1]] + [i[2] for i in its]]
    assert all(a[0] < b[0] for a, b in zip(pts, pts[1:])) and all(-3 < y < -0.3 for _, y in pts), run
    assert all(9.99 <= x <= 11.6 for x, _ in pts), (run, pts)
    records.append(vf.record(
        rid=f"lagos15.eagle.h2-fraction.{run.split()[0].lower().replace('-', '')}.{method.lower()}.z0", source="EAGLE", run=f"{run}, M*>1e10 above COLD GASS limit", relation="h2-fraction", z=0.0,
        axes={"xDefinition": "log10 stellar mass (3D 30 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": "log10 median H2-to-stellar mass ratio MH2/M*, converted from the plotted log10 MH2/(MH2+M*) (galaxies above the COLD GASS detection limit only)", "yUnit": "dex"},
        points=[(x, conv(y)) for x, y in pts], population="galaxies with M*>1e10 Msun and MH2 above the COLD GASS sensitivity limit", interval="unspecified",
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "massDefinition": "aperture-30pkpc", "population": "galaxies-above-detection-threshold", "gasPhase": "H2", "gasMethod": method, "gasStatistic": "median"},
        citation=f"Lagos et al. 2015, MNRAS 452, 3815 (arXiv:{ARXIV}), H2 fraction versus stellar mass compared with COLD GASS", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="H2 fraction versus stellar mass (COLD GASS comparison)", panel="z=0", sha=sha, member=f"{EPS.name} (converted to PDF)", calibration="prediction",
        calib="x and y: numeric tick labels snapped to tick marks (frame from the long axis strokes)",
        warning=f"The {what}, read from the vector paths of Lagos et al. 2015; no table exists. The plotted quantity MH2/(MH2+M*) was converted exactly to MH2/M*. The sample is selected on detectability (M*>1e10 Msun, MH2 above the COLD GASS limit), so it is a biased subset, not the all-galaxy median. "
                "The 16th-84th percentile region (a hatched fill) and the COLD GASS observations are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "lagos15-eagle-h2.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE H2-fraction records from Lagos+15")
