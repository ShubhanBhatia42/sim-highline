import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2204.09431"
DOI = "10.1093/mnras/stac3280"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "figures" / "UVLF_panel.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 100, 100)
assert len(fs) == 6
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
MCONST = 2.5 * math.log10(4 * math.pi * (10 * 3.0856775814913673e18) ** 2) - 48.6
DEXMAG = math.log10(0.4)


def cal_x(fr):
    pairs = [(cx, float(t)) for t, cx, cy in W if t in ("28", "29", "30") and fr.x0 - 5 <= cx <= fr.x1 + 5 and 0 < cy - fr.y1 < 15]
    ticks = vf._tick_positions(page, fr, "x")
    return vf.axis_fit(page, fr, "x", labels=[(min(ticks, key=lambda q: abs(q - cx)), v) for cx, v in pairs])[0]


def cal_y(fr):
    ys = sorted(((cy, -float(t)) for t, cx, cy in W if t in ("3", "4", "5", "6", "7") and cx < 50 and fr.y0 - 3 <= cy <= fr.y1 + 3))
    ticks = vf._tick_positions(page, fr, "y")
    return vf.axis_fit(page, fr, "y", labels=[(min(ticks, key=lambda q: abs(q - cy)), v) for cy, v in ys])[0]


COL = {15: (0.27, 0.92, 0.93), 14: (0.3, 0.7, 0.98), 13: (0.47, 0.44, 0.99), 12: (0.54, 0.18, 0.73), 11: (0.44, 0.05, 0.34), 10: (0.25, 0.01, 0.02)}
IDX = {15: 0, 14: 1, 13: 2, 12: 3, 11: 4, 10: 5}
TABLE_27_8 = {10: -2.37, 11: -2.53, 12: -2.78, 13: -3.14}
KINDS = {"[] 0": ("observed", "dust attenuated", "dust attenuated (SED modelling with a line-of-sight dust model)"), "[ 3.7 1.6 ] 0": ("intrinsic", "intrinsic", "none (intrinsic)")}
records = []
for z, i in IDX.items():
    fx, fy = cal_x(fs[3 + i % 3]), cal_y(fs[i])
    for c in vf.curves(page, fs[i], fx, fy, min_items=6):
        if c["color"] != COL[z] or c["dashes"] not in KINDS:
            continue
        kind, tag, dust = KINDS[c["dashes"]]
        logl = c["points"]
        if kind == "observed" and z in TABLE_27_8:
            assert abs(logl[0][0] - 27.8) < 0.02 and abs(logl[0][1] - TABLE_27_8[z]) < 0.04, (z, logl[0])
        pts = sorted((round(MCONST - 2.5 * x, 3), round(y + DEXMAG, 4)) for x, y in logl)
        assert all(a[0] < b[0] for a, b in zip(pts, pts[1:])) and len(pts) >= 6 and -24 < pts[0][0] < -17 and pts[-1][0] < -17, (z, kind)
        records.append(vf.record(
            rid=f"wilkins22.flares.uvlf.{kind}.z{z}", source="FLARES", run=f"40 resimulated regions (EAGLE AGNdT9 model), {tag}", relation="uvlf", z=float(z),
            axes={"xDefinition": f"absolute UV magnitude M_UV from the far-UV luminosity, {tag} (AB)", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"},
            points=pts, population="all galaxies in the weighted combination of the resimulated regions", interval="unspecified",
            definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "densityFrame": "comoving", "uvBand": "far-UV (1500 A), L_FUV", "dustCorrection": dust, "population": "all"},
            citation=f"Wilkins et al. 2023, MNRAS 519, 3118 (arXiv:{ARXIV}), far-UV luminosity function at z=15 to 10, {kind}, z={z}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Observed and intrinsic far-UV luminosity function at z=15 to 10", panel=f"z={z}, {'solid' if kind == 'observed' else 'dashed'} line", sha=sha, member="figures/UVLF_panel.pdf", calibration="prediction",
            calib="x: numeric tick labels snapped to ticks (log L_FUV); y: log phi per dex labels paired with ticks (minus glyphs are separate); x converted to M_UV, y to per magnitude",
            warning=f"{kind.capitalize()} far-UV luminosity function of FLARES at z={z}, read from the vector paths of Wilkins et al. 2023. Conversions (exact): M_UV = {MCONST:.4f} - 2.5 log10(L_FUV / erg s^-1 Hz^-1) (AB, 10 pc), and log phi per magnitude = log phi per dex + log10(0.4). Binned in 0.1 dex of log L_FUV; bright-end bins hold few galaxies and are noisy. The paper also tabulates space densities in 0.2 dex bins without saying whether they are attenuated or intrinsic; those are not used.",
            uncertainty=0.02))
assert len(records) == 12, len(records)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "wilkins22-flares-uvlf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FLARES UV luminosity function records from Wilkins+22")
