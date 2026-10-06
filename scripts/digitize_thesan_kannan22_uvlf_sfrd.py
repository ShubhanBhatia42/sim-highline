import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2110.00584"
DOI = "10.1093/mnras/stab3710"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
CITE = f"Kannan et al. 2022, MNRAS 511, 4005 (arXiv:{ARXIV})"
URL = f"https://arxiv.org/abs/{ARXIV}"
COLS = {(0.12, 0.47, 0.71): 6.0, (1.0, 0.5, 0.05): 7.0, (0.17, 0.63, 0.17): 8.0, (0.84, 0.15, 0.16): 9.0, (0.58, 0.4, 0.74): 10.0}
DEFS = {"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "densityFrame": "comoving", "uvBand": "rest-frame 1500 A, AB", "population": "all galaxies"}
records = []


def ylabels(page, fr):
    ws = sorted(((w[1] + w[3]) / 2, vf.number(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and w[2] < fr.x0 and fr.y0 <= (w[1] + w[3]) / 2 <= fr.y1)
    ticks = vf._tick_positions(page, fr, "y")
    assert len(ws) == len(ticks), (ws, ticks)
    return [(t, v) for t, (_, v) in zip(ticks, ws)]

pdf = SRC / "figures" / "UVLF.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 200)
fx, xt = vf.axis_fit(page, fr, "x")
fy, yt = vf.axis_fit(page, fr, "y", labels=ylabels(page, fr))
RUNS = {"[] 0": ("THESAN-1", "Vogelsberger+20 dust-to-metal scaling of the Gnedin 2014 attenuation"), "[ 11.1 4.8 ] 0": ("THESAN-2 (lower resolution)", "same dust scaling"),
        "[ 3 4.95 ] 0": ("THESAN-SDAO-2", "same dust scaling"), "[ 19.2 4.8 3 4.8 ] 0": ("THESAN-1 (dust-model attenuation)", "dust mass from the THESAN empirical dust model")}
curves = [c for c in vf.curves(page, fr, fx, fy, min_items=20) if c["width"] and abs(c["width"] - 3.0) < 0.05 and c["color"] in COLS and c["dashes"] in RUNS]
assert len(curves) == 16, len(curves)
for c in curves:
    z = COLS[c["color"]]
    run, dust = RUNS[c["dashes"]]
    pts = [(x, y + (z - 8.0)) for x, y in vf.clip(c["points"], -24, -11, -100, 100)]
    for a, b in zip(pts, pts[1:]):
        assert a[0] < b[0] + 1e-9, (run, z)
    pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0]]
    assert len(pts) >= 15, (run, z, len(pts))
    if run == "THESAN-1" and z == 6.0:
        ys = dict((round(x), y) for x, y in pts)
        assert -3.5 < ys[-20] < -2.6, ys[-20]
    slug = {"THESAN-1": "t1", "THESAN-2 (lower resolution)": "t2", "THESAN-SDAO-2": "sdao2", "THESAN-1 (dust-model attenuation)": "t1dust"}[run]
    records.append(vf.record(
        rid=f"kannan22.thesan.uvlf.{slug}.z{z:g}", source="THESAN-1", run=run, relation="uvlf", z=z,
        axes={"xDefinition": "absolute UV magnitude M_1500 (rest-frame 1500 A, AB, dust attenuated)", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"},
        points=pts, population="all galaxies", interval="unspecified", definitions=dict(DEFS, dustCorrection=f"dust attenuated ({dust})"),
        citation=f"{CITE}, UV luminosity functions at z=6-10, z={z:g}", doi=DOI, url=URL, figure="UV luminosity functions at z=6-10", panel=f"z={z:g}", sha=sha, member="figures/UVLF.pdf", calibration="prediction",
        calib="x and y: numeric tick labels snapped to tick marks; y includes the +(z-8) offset removal (curves are plotted offset by -(z-8))",
        warning=f"Dust-attenuated rest-frame 1500 A luminosity function of {run} at z={z:g}, read from the vector paths of Kannan et al. 2022. The figure plots each redshift offset by -(z-8) dex; that offset was added back, so y is the physical value. {dust}.",
        uncertainty=0.02))

pdf = SRC / "figures" / "sfrbin.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 200)
fx, xt = vf.axis_fit(page, fr, "x")
fy, yt = vf.axis_fit(page, fr, "y", labels=ylabels(page, fr))
SR = {(0.84, 0.15, 0.16): "THESAN-1", (0.12, 0.47, 0.71): "THESAN-2 (lower resolution)", (0.58, 0.4, 0.74): "THESAN-SDAO-2"}
sf = [c for c in vf.curves(page, fr, fx, fy, min_items=20) if c["width"] and abs(c["width"] - 4.0) < 0.05 and c["color"] in SR and c["dashes"] == "[] 0"]
assert len(sf) == 3
for c in sf:
    run = SR[c["color"]]
    pts = vf.clip(c["points"], 5, 16, -9, 1)
    pts = pts[::-1] if pts[0][0] > pts[-1][0] else pts
    assert 5.4 < pts[0][0] < 5.8 and pts[-1][0] > 14.9, (pts[0], pts[-1])
    if run == "THESAN-1":
        ys = {round(x): y for x, y in pts}
        assert -1.8 < ys[6] < -1.45 and -2.5 < ys[10] < -2.2, (ys[6], ys[10])
    slug = {"THESAN-1": "t1", "THESAN-2 (lower resolution)": "t2", "THESAN-SDAO-2": "sdao2"}[run]
    records.append(vf.record(
        rid=f"kannan22.thesan.sfrd.{slug}", source="THESAN-1", run=run, relation="sfrd", z=10.0,
        axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic star-formation rate density of all gas cells in the box", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
        points=pts, population="all galaxies in the box", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "densityFrame": "comoving", "sfrIndicator": "instantaneous SFR of star-forming gas", "population": "all galaxies"},
        citation=f"{CITE}, evolution of the star formation rate density", doi=DOI, url=URL, figure="Evolution of the star formation rate density", panel="total (thick solid line)", sha=sha, member="figures/sfrbin.pdf", calibration="prediction",
        calib="x and y: numeric tick labels snapped to tick marks (frame from the long axis strokes)",
        warning=f"Total cosmic SFR density of {run} versus redshift, read from the vector paths of Kannan et al. 2022. The halo-mass-split contributions (thin dashed, dash-dot, dotted lines) are not extracted. The paper notes the SFRD is converged below z=8 only; lower-resolution runs fall an order of magnitude short at high z."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "kannan22-thesan-uvlf-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} THESAN UV LF and SFR density records from Kannan+22")
