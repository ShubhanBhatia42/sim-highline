import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2502.20437"
DOI = "10.33232/001c.145804"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
CITE = f"Kannan et al. 2025, OJAp 8 (arXiv:{ARXIV})"
URL = f"https://arxiv.org/abs/{ARXIV}"
RUN = "THESAN-ZOOM (14 zoom-in galaxies, Kannan+25)"
BASE = {"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "densityFrame": "comoving", "population": "all galaxies of the zoom sample, as drawn"}
WARN_ZOOM = "THESAN-ZOOM resimulates 14 selected high-redshift galaxies and their surroundings; how the sample is combined into volume-averaged functions is described in the paper, not in the figure."
records = []


def numw(page, fr, axis):
    W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words") if vf.number(w[4]) is not None]
    return W


def fit(page, frame, axis, labs):
    ticks = vf._tick_positions(page, frame, axis)
    return vf.axis_fit(page, frame, axis, labels=[(min(ticks, key=lambda q: abs(q - p)), v) for p, v in labs])[0]


def panel_fits(page, fs):
    W = numw(page, None, None)
    fxs, fys = [], []
    for c in range(3):
        fr = fs[3 + c]
        fxs.append(fit(page, fr, "x", [(cx, vf.number(t)) for t, cx, cy in W if 0 < cy - fr.y1 < 40 and fr.x0 - 3 <= cx < fr.x1 - 3]))
    for r in range(2):
        fr = fs[3 * r]
        fys.append(fit(page, fr, "y", [(cy, vf.number(t)) for t, cx, cy in W if 0 < fr.x0 - cx < 40 and fr.y0 <= cy <= fr.y1]))
    return fxs, fys


def clean(pts, lo, hi, ylo=-6.5, yhi=0.2):
    pts = sorted((round(x, 3), round(y, 4)) for x, y in pts if lo <= x <= hi and ylo < y < yhi)
    out = []
    for p in pts:
        if not out or p[0] > out[-1][0]:
            out.append(p)
    return out


# GSMF
pdf = SRC / "Figures" / "GSMF.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 100, 100)
fxs, fys = panel_fits(page, fs)
ZB = [(3.5, 4.5), (4.5, 5.5), (5.5, 6.5), (6.5, 7.5), (7.5, 8.5), (8.5, 9.5)]
for i, (a, b) in enumerate(ZB):
    fx, fy = fxs[i % 3], fys[i // 3]
    cs = [c for c in vf.curves(page, fs[i], fx, fy, min_items=8) if c["color"] == (0.0, 0.0, 0.0) and c["width"] == 4.0]
    assert len(cs) == 1, (i, len(cs))
    pts = clean(cs[0]["points"], 6.0, 12.0)
    zc = (a + b) / 2
    if i == 0:
        assert -2.6 < min(pts, key=lambda q: abs(q[0] - 9.0))[1] < -1.6, pts
    assert len(pts) >= 8
    records.append(vf.record(
        rid=f"kannan25.thesanzoom.gsmf.z{zc:g}", source="THESAN-zoom", run=RUN, relation="gsmf", z=zc, z_range=(a, b),
        axes={"xDefinition": "log10 stellar mass within twice the stellar half-mass radius", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function per dex", "yUnit": "log10(cMpc^-3 dex^-1)"},
        points=pts, population="galaxies of the THESAN-ZOOM sample", interval="unspecified", definitions=dict(BASE, massDefinition="aperture-2rhalf-stars"),
        citation=CITE + f", galaxy stellar mass function, {a:g} <= z < {b:g}", doi=DOI, url=URL, figure="Galaxy stellar mass function at z=3.5-9.5", panel=f"{a:g}<=z<{b:g}", sha=sha, member="Figures/GSMF.pdf", calibration="prediction",
        calib="x: numeric tick labels (bottom row, per column) snapped to ticks; y: numeric tick labels (left column, per row, minus glyphs included) snapped to ticks",
        warning=f"Stellar mass function of THESAN-ZOOM in the redshift bin {a:g}-{b:g}, read from the vector path of Kannan et al. 2025 (observational points not extracted). {WARN_ZOOM}", uncertainty=0.02))

# UVLF
pdf = SRC / "Figures" / "UVLF.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 100, 100)
fxs, fys = panel_fits(page, fs)
ZU = [(3.5, 4.5), (5.5, 6.5), (7.5, 8.5), (9.5, 10.5), (11.5, 12.5), (13.5, 14.5)]
KIND = {"[] 0": ("fiducial", "fiducial THESAN-ZOOM dust model (attenuated)"), "[ 14.8 6.4 ] 0": ("bouwens16", "Bouwens+16 empirical attenuation relation applied to the intrinsic luminosities")}
for i, (a, b) in enumerate(ZU):
    fx, fy = fxs[i % 3], fys[i // 3]
    got = {c["dashes"]: c for c in vf.curves(page, fs[i], fx, fy, min_items=8) if c["color"] == (0.0, 0.0, 0.0) and c["width"] == 4.0 and c["dashes"] in KIND}
    assert len(got) == 2, (i, list(got))
    zc = (a + b) / 2
    for d, (slug, dust) in KIND.items():
        pts = clean(got[d]["points"], -26, -12)
        assert len(pts) >= 8 and pts[0][0] < -17, (i, slug, len(pts))
        if i == 0 and slug == "fiducial":
            assert -2.9 < min(pts, key=lambda q: abs(q[0] + 20))[1] < -1.9, pts
        records.append(vf.record(
            rid=f"kannan25.thesanzoom.uvlf.{slug}.z{zc:g}", source="THESAN-zoom", run=RUN + f", {slug} dust", relation="uvlf", z=zc, z_range=(a, b),
            axes={"xDefinition": "absolute UV magnitude M_UV (rest-frame 1500 A, AB, attenuated)", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"},
            points=pts, population="galaxies of the THESAN-ZOOM sample", interval="unspecified", definitions=dict(BASE, uvBand="rest-frame 1500 A, AB", dustCorrection=dust),
            citation=CITE + f", UV luminosity function, {a:g} <= z < {b:g}", doi=DOI, url=URL, figure="UV luminosity function at z=3.5-14.5", panel=f"{a:g}<=z<{b:g}, {'solid' if slug == 'fiducial' else 'dashed'} black curve", sha=sha, member="Figures/UVLF.pdf", calibration="prediction",
            calib="x: numeric tick labels (bottom row, per column) snapped to ticks (axis runs from -14 to -24); y: numeric tick labels (left column, per row) snapped to ticks",
            warning=f"UV luminosity function of THESAN-ZOOM in the redshift bin {a:g}-{b:g} with the {dust}, read from the vector path of Kannan et al. 2025. The paper notes the fiducial dust model overshoots the bright end at z below about 7 because of too little dust. Observations and the TNG and MillenniumTNG comparison curves are not extracted. {WARN_ZOOM}", uncertainty=0.02))

# SFRD
pdf = SRC / "Figures" / "SFRD.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page, 100, 100)[0]
W = numw(page, None, None)
fx = fit(page, fr, "x", [(cx, vf.number(t)) for t, cx, cy in W if cy > fr.y1 and cy - fr.y1 < 40 and fr.x0 - 3 <= cx <= fr.x1 + 3])
fy = fit(page, fr, "y", [(cy, vf.number(t)) for t, cx, cy in W if cx < fr.x0 and fr.y0 <= cy <= fr.y1])
got = {c["dashes"]: c for c in vf.curves(page, fr, fx, fy, min_items=8) if c["color"] == (0.0, 0.0, 0.0) and c["width"] == 4.0 and c["dashes"] in KIND}
assert len(got) == 2
for d, (slug, dust) in KIND.items():
    pts = clean(got[d]["points"], 2.5, 15, -4.5, -0.5)
    near = lambda z: min(pts, key=lambda q: abs(q[0] - z))[1]
    assert len(pts) >= 6 and -1.5 < near(4.0) < -1.0 and -4.0 < near(14.0) < -3.2, (slug, pts[:2], near(4), near(14))
    records.append(vf.record(
        rid=f"kannan25.thesanzoom.sfrd.{slug}", source="THESAN-zoom", run=RUN + f", {slug} dust", relation="sfrd", z=8.5, z_range=(pts[0][0], pts[-1][0]),
        axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 star formation rate density of galaxies brighter than M_UV = -17 (attenuated)", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
        points=pts, population="galaxies of the THESAN-ZOOM sample brighter than M_UV = -17", interval="unspecified",
        definitions=dict(BASE, sfrIndicator="instantaneous SFR", sfrIntegrationLimit="integrated down to M_UV = -17", dustCorrection=dust),
        citation=CITE + ", star formation rate density", doi=DOI, url=URL, figure="Evolution of the star formation rate density, z=3-14", panel=f"{'solid' if slug == 'fiducial' else 'dashed'} black curve", sha=sha, member="Figures/SFRD.pdf", calibration="prediction",
        calib="x and y: numeric tick labels (minus glyphs included) snapped to ticks",
        warning=f"SFR density of THESAN-ZOOM galaxies brighter than M_UV=-17 versus redshift (z 3 to 14) with the {dust}, read from the vector path of Kannan et al. 2025; the observational points and the MillenniumTNG curve are not extracted. {WARN_ZOOM}", uncertainty=0.02))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "kannan25-thesanzoom.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} THESAN-ZOOM records from Kannan+25")
