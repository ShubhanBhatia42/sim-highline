import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1609.01739"
DOI = "10.1093/mnras/stw2610"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
EPS = next(SRC.rglob("EAGLE_L100JstarsVsMstellar_redshift.eps"))
PDF = SRC / "pdf" / EPS.with_suffix(".pdf").name
if not PDF.exists():
    PDF.parent.mkdir(exist_ok=True)
    subprocess.run(["epstopdf", str(EPS), f"--outfile={PDF}"], check=True)
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frame_from_long_lines(page, 50)
fx, xt = vf.axis_fit(page, fr, "x")
fy, yt = vf.axis_fit(page, fr, "y")
assert len(xt) >= 6 and len(yt) >= 4
STYLES = [((0.0, 0.0, 0.0), 1.4, "[] 0", 0.0), ((0.0, 0.17, 0.37), 2.8, "[ 1.13386 2.83465 ] 0", 0.5), ((0.69, 0.12, 0.0), 2.3, "[ 5.6693 5.6693 ] 0", 1.2),
          ((0.09, 0.52, 0.0), 2.3, "[ 5.6693 2.83465 1.41733 2.83465 ] 0", 1.7), ((0.95, 0.78, 0.0), 2.3, "[ 11.3386 5.6693 ] 0", 3.0)]
close = lambda c, t: c is not None and all(abs(u - v) < 0.02 for u, v in zip(c, t))
records = []
for col, lw, dash, z in STYLES:
    ls = [d for d in page.get_drawings() if d["type"] == "s" and close(d["color"], col) and abs((d.get("width") or 0) - lw) < 0.05 and d["dashes"] == dash and len(d["items"]) >= 5]
    assert len(ls) == 1, (z, len(ls))
    its = ls[0]["items"]
    pts = [(fx(p.x), fy(p.y)) for p in [its[0][1]] + [i[2] for i in its]]
    assert all(a[0] < b[0] for a, b in zip(pts, pts[1:])) and all(0.5 < y < 3.5 for _, y in pts), z
    records.append(vf.record(
        rid=f"lagos17.eagle.jstar.z{z:g}", source="EAGLE", run="Ref-L100N1504 (median, all galaxies M*>1e9)", relation="jstar", z=z,
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 specific angular momentum of the stars within the stellar half-mass radius, j_stars(r50) [pkpc km/s]", "yUnit": "log10(kpc km/s)"},
        points=pts, population="all galaxies with M*>1e9 Msun and r50>1 pkpc", interval="unspecified",
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "massDefinition": "unspecified", "population": "all", "jDefinition": "stars within r50 (all particles)", "sfrStatistic": "median"},
        citation=f"Lagos et al. 2017, MNRAS 464, 3850 (arXiv:{ARXIV}), j_stars-M_stars relation at several redshifts, z={z:g}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="j_stars(r50) versus stellar mass at z=0 to 3", panel=f"z={z:g}", sha=sha, member=f"{EPS.name} (converted to PDF)", calibration="prediction",
        calib="x and y: numeric tick labels snapped to tick marks (frame from the long axis strokes)",
        warning=f"Median j_stars(r50) of all EAGLE Ref-L100N1504 galaxies with M*>1e9 Msun and r50>1 pkpc in stellar-mass bins at z={z:g}, read from the vector paths of Lagos et al. 2017; no table exists. "
                "The paper marks log M* = 9.5 as the conservative resolution limit above which j_stars is converged. The 16th-84th percentile regions (hatched fills, drawn for z=0 and 1.2 only) are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "lagos17-eagle-jstar.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE j_stars-M* records from Lagos+17")
