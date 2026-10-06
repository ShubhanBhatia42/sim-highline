import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1607.01028"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "pdf" / "4x4_new.pdf"
if not PDF.exists():
    PDF.parent.mkdir(exist_ok=True)
    subprocess.run(["epstopdf", str(next(SRC.rglob("4x4_new.eps"))), f"--outfile={PDF}"], check=True)
RED = (1.0, 0.0, 0.0)
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
frame = next(r for r in vf.frames(page) if abs(r.x0 - 90) < 2 and abs(r.y0 - 72) < 2 and abs(r.y1 - 322) < 2)
fx, xt = vf.axis_fit(page, frame, "x")
fy, yt = vf.axis_fit(page, frame, "y")
assert [v for _, v in xt] == [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0] and [v for _, v in yt][:2] == [2.5, 2.0], (xt, yt)
pts = sorted(vf.markers(page, frame, fx, fy, RED, max_size=7.5, min_size=5.0))
assert len(pts) >= 60, len(pts)
rec = vf.record(
    rid="maccio16.nihao.stfr-hi-v50.galaxies.z0", source="NIHAO zoom suite", run="NIHAO zoom sample (per galaxy, HI-profile V50i)", relation="stfr", z=0.0,
    axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 inclination-corrected rotational velocity V50i from the mock HI line width at 50% (W50/2)", "yUnit": "log10(km/s)"},
    points=pts, population="individual zoom galaxies (not volume complete)",
    warning="Marker centres of the NIHAO galaxies (red squares) read from the vector paths of NIHAO X (Maccio et al. 2016, MNRAS 463, L69), Tully-Fisher panel of the HI-tests figure (4x4_new, upper left); no table is published. "
            "V50 is the velocity width of mock HI profiles at 50 per cent of the peak divided by two, evaluated for the sample's mock observations and inclination-corrected (V50i); not the same velocity as the V_HI of NIHAO XII. Zoom selections are not volume complete.",
    interval="scatter", connect=False, strict=False,
    definitions={"imf": "chabrier03", "cosmology": {"H0": 67.1, "Om": 0.3175}, "massDefinition": "unspecified", "velocityDefinition": "V50 = W50/2 of mock HI profile, inclination corrected", "population": "zoom-centrals"},
    citation="Maccio et al. 2016 (NIHAO X), MNRAS 463, L69, HI-tests figure (4x4_new), Tully-Fisher panel", doi="10.1093/mnrasl/slw147", url=f"https://arxiv.org/abs/{ARXIV}",
    figure="4x4_new (fig:Hitest), upper left", panel="Tully-Fisher panel", sha=sha, member=f"{PDF.name} (converted from 4x4_new.eps; red squares)",
    calib="x: labelled ticks 4-12; y: labelled ticks 1.0-2.5; asserted", calibration="unknown")
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "maccio16-nihao-hi-tf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print(f"Wrote 1 NIHAO X record with {len(pts)} galaxies (stellar TF, mock-HI V50i)")
