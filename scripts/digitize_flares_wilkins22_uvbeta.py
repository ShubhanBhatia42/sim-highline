"""FLARES V (Wilkins et al. 2023, MNRAS 519, 3118; arXiv:2204.09431): the median UV continuum slope against far-UV luminosity at z = 15 to 10 for three treatments of the light (stellar emission only, with nebular emission, with nebular emission and dust),
read from the vector figure figures/beta2.pdf (relation uvbeta; 18 curves). The luminosity axis (log10 L_FUV) is converted to M_UV with the same exact AB conversion as scripts/digitize_flares_wilkins22_uvlf.py.
The paper does not give the wavelength window of beta, so betaWindow is unspecified; it does not say whether the plotted L_FUV is the intrinsic or the dust-attenuated luminosity, which is stated in each record.
Checks inside this script (every assert must pass or nothing is written), against sentences of the paper that give numbers: the solid curves are about -2.4 below L_FUV = 10^28.5 (M_FUV > -19.5) and about -2 above 10^29, the dotted curves about -2.8 at the faint end and about -2.5 at 10^29.5, the dashed curves about -2.5,
and dust reddens the slope by about 0.5 above 10^29; the conversion of 10^28.5 erg/s/Hz gives the printed M_FUV of about -19.5.
Usage: python3 scripts/digitize_flares_wilkins22_uvbeta.py [SOURCE_DIR]   (writes data/curves/wilkins22-flares-uvbeta.json)"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "2204.09431"
DOI = "10.1093/mnras/stac3280"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "curves" / "wilkins22-flares-uvbeta.json"
pdf = SRC / "figures" / "beta2.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page, 100, 100)
assert len(fr) == 1
fr = fr[0]
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
ticks_x, ticks_y = vf._tick_positions(page, fr, "x"), vf._tick_positions(page, fr, "y")
fx, xt = vf.axis_fit(page, fr, "x", labels=[(min(ticks_x, key=lambda q: abs(q - cx)), float(t)) for t, cx, cy in W if t in ("28", "29", "30") and 0 < cy - fr.y1 < 15])
fy, yt = vf.axis_fit(page, fr, "y", labels=[(min(ticks_y, key=lambda q: abs(q - cy)), -float(t)) for t, cx, cy in W if t in ("1.6", "1.8", "2.0", "2.2", "2.4", "2.6", "2.8") and cx < 35])  # the minus signs are separate glyphs
assert len(xt) == 3 and len(yt) == 7
MCONST = 2.5 * math.log10(4 * math.pi * (10 * 3.0856775814913673e18) ** 2) - 48.6

# ---------------------------------------------------------------- definitions, each from a sentence of the paper
norm = lambda a: re.sub(r"\s+", " ", a).strip()
files = [SRC / "sections" / n for n in ("observational.tex", "flares.tex")]
log = []


def quote(s):
    for f in files:
        flat, idx = "", []
        for n, l in enumerate(f.read_text(errors="replace").splitlines(), 1):
            flat += norm(l) + " "
            idx += [n] * (len(norm(l)) + 1)
        k = flat.find(norm(s))
        if k >= 0:
            log.append(f"{f.name}:{idx[k]}: {norm(s)}")
            return f"{f.name}:{idx[k]}"
    raise AssertionError("quote not found: " + s[:80])


Q = {
    "treatments": quote(r"Here we show the median $\beta$ for unprocessed starlight (dotted line), starlight with reprocessing by gas (dashed line), and reprocessing with gas and dust (solid line, the same as that shown in Fig. \ref{fig:beta})."),
    "caption": quote(r"The dotted line shows the UV continuum slope predicted from just the pure stellar emission, the dashed line including nebular emission, and the solid line also including dust (i.e. that which would be observed)."),
    "faint": quote(r"At $L_{\rm FUV}< 10^{28.5}\ {\rm erg\ s^{-1}\ Hz^{-1}}$ ($M_{\rm FUV}>-19.5$) the slope is $\approx -2.4$ with little evolution with redshift."),
    "bright": quote(r"At $L_{\rm FUV}> 10^{29}\ {\rm erg\ s^{-1}\ Hz^{-1}}$ the average slope has reddened to $\approx -2$."),
    "stellar": quote(r"With no reprocessing the predicted slopes are $\approx -2.8$ at low-luminosity rising to $\approx -2.5$ at  $L_{\rm FUV}\approx 10^{29.5}\ {\rm erg\ s^{-1}\ Hz^{-1}}$"),
    "dust": quote(r"where dust is predicted to redden the slope by $\approx 0.5$"),
}
COL = {15: (0.27, 0.92, 0.93), 14: (0.3, 0.7, 0.98), 13: (0.47, 0.44, 0.99), 12: (0.54, 0.18, 0.73), 11: (0.44, 0.05, 0.34), 10: (0.25, 0.01, 0.02)}
KIND = {"[ 1 1.65 ] 0": "stellar", "[ 3.7 1.6 ] 0": "nebular", "[] 0": "dust"}
TXT = {
    "stellar": ("intrinsic", "unprocessed starlight: stellar emission only, no nebular emission, no dust", "stellar continuum only (dotted line)"),
    "nebular": ("intrinsic", "starlight reprocessed by gas: stellar plus nebular emission, no dust", "stellar plus nebular emission (dashed line)"),
    "dust": ("attenuated", "stellar plus nebular emission, attenuated by dust (the paper: 'that which would be observed')", "stellar plus nebular emission and dust (solid line)")}
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


check(abs((MCONST - 2.5 * 28.5) - (-19.5)) < 0.2, f"M_UV of L_FUV = 10^28.5 erg/s/Hz from the exact AB conversion is {MCONST - 2.5 * 28.5:.2f}, the paper prints about -19.5")
curves = {}
for d in page.get_drawings():
    if d["type"] != "s" or d["color"] is None or len(d["items"]) < 4 or d["dashes"] not in KIND:
        continue
    z = next((k for k, c in COL.items() if all(abs(a - b) < 0.02 for a, b in zip(d["color"], c))), None)
    if z is None:
        continue
    pts = [d["items"][0][1]] + [it[2] for it in d["items"]]
    curves[(z, KIND[d["dashes"]])] = [(fx(p.x), fy(p.y)) for p in pts]
check(len(curves) == 18, "18 curves: six redshifts, three treatments")
for (z, k), c in curves.items():
    xs = [p[0] for p in c]
    assert all(a < b for a, b in zip(xs, xs[1:])) and -3.0 < min(p[1] for p in c) and max(p[1] for p in c) < -1.5 and 27.4 < xs[0] and xs[-1] < 30.0, (z, k)
med = lambda k, lo, hi: [y for (z, kk), c in curves.items() if kk == k for x, y in c if lo <= x < hi]
m = med("dust", 27.0, 28.5)
check(-2.5 < float(np.median(m)) < -2.3 and min(m) > -2.55 and max(m) < -2.25, f"solid curves below L_FUV = 10^28.5: median {np.median(m):.2f}, range {min(m):.2f} to {max(m):.2f} (paper: about -2.4)")
m = [y for (z, kk), c in curves.items() if kk == "dust" for x, y in c if 29.0 <= x <= 29.3 and z in (10, 11, 12, 13)]
check(-2.1 < float(np.median(m)) < -1.9, f"solid curves at L_FUV = 10^29 to 10^29.3 (z = 10 to 13): median {np.median(m):.2f} (paper: about -2)")
m = med("stellar", 27.0, 28.2)
check(-2.9 < min(m) < -2.7, f"dotted curves at the faint end: lowest value {min(m):.2f} (paper: about -2.8)")
m = [y for (z, kk), c in curves.items() if kk == "stellar" and z in (10, 11) for x, y in c if x > 29.3 and y < -2.3]
m = [y for (z, kk), c in curves.items() if kk == "stellar" and z in (10, 11) for x, y in c if x > 29.3]
check(len(m) >= 3 and abs(float(np.mean(m)) + 2.5) < 0.15, f"dotted curves of z = 10 and 11 above 10^29.3: {', '.join(f'{v:.2f}' for v in m)}, mean {np.mean(m):.2f} (paper: about -2.5 at 10^29.5)")
m = med("nebular", 27.5, 29.0)
check(-2.62 < float(np.median(m)) < -2.45, f"dashed curves up to 10^29: median {np.median(m):.2f} (paper: about -2.5)")
dd = []
for z in (10, 11, 12, 13):
    xs = np.array([p[0] for p in curves[(z, "nebular")]])
    ys = np.array([p[1] for p in curves[(z, "nebular")]])
    xd = np.array([p[0] for p in curves[(z, "dust")]])
    yd = np.array([p[1] for p in curves[(z, "dust")]])
    for x0 in (29.0, 29.1):
        if xs[0] <= x0 <= xs[-1] and xd[0] <= x0 <= xd[-1]:
            dd.append(float(np.interp(x0, xd, yd) - np.interp(x0, xs, ys)))
check(len(dd) >= 4 and 0.3 < float(np.mean(dd)) < 0.7, f"dust minus nebular curve at L_FUV = 10^29 to 10^29.1: mean {np.mean(dd):.2f} over {len(dd)} values (paper: dust reddens the slope by about 0.5)")

records = []
for (z, k), c in sorted(curves.items(), key=lambda t: (-t[0][0], t[0][1])):
    dust, what, label = TXT[k]
    pts = sorted((round(MCONST - 2.5 * x, 3), round(y, 4)) for x, y in c)
    assert all(a[0] < b[0] for a, b in zip(pts, pts[1:]))
    notes_chk = "; ".join(checks[1:])
    records.append(vf.record(
        rid=f"wilkins22.flares.uvbeta.{k}.z{z}", source="FLARES", run=f"40 resimulated regions (EAGLE AGNdT9 model), {label}", relation="uvbeta", z=float(z),
        axes={"xDefinition": "absolute UV magnitude M_UV converted from the plotted far-UV luminosity L_FUV (the paper does not say whether it is the intrinsic or the dust-attenuated luminosity; AB, 10 pc)", "xUnit": "mag (AB)",
              "yDefinition": f"UV-continuum slope beta, f_lambda ~ lambda^beta, median of galaxies in bins of L_FUV: {what}", "yUnit": "dimensionless"},
        points=pts, population="FLARES galaxies of the 40 resimulated regions; whether the median is weighted by the region weights is not stated",
        warning=(f"Median beta of the FLARES galaxies at z = {z} in bins of L_FUV (the figure has no band or error bars), {what}, read from the vector paths of Wilkins et al. 2023 and converted to M_UV with the exact AB conversion M_UV = {MCONST:.4f} - 2.5 log10(L_FUV / erg s^-1 Hz^-1). "
                 "The paper does not give the wavelength window of beta (betaWindow unspecified) and does not say whether the plotted L_FUV is intrinsic or dust attenuated, so a comparison with observed M_UV may shift the bright end by the far-UV attenuation. The bright-end bins hold few galaxies."),
        definitions={"betaWindow": "unspecified", "dustTreatment": dust, "dustModel": ("line-of-sight dust model of the FLARES SED modelling (read, not restated in this paper)" if dust == "attenuated" else "no dust"), "betaMethod": "unspecified",
                     "stellarPopulation": what, "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "xVariable": "far-UV luminosity L_FUV converted to M_UV", "uvBand": "far-UV (1500 A), L_FUV", "statistic": "median", "population": "all galaxies of the resimulated regions"},
        citation=f"Wilkins et al. 2023, MNRAS 519, 3118 (arXiv:{ARXIV}), UV continuum slope against far-UV luminosity, {label}, z={z}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Average UV continuum slope against UV luminosity and redshift", panel=f"z={z}, {label}", sha=sha, member="figures/beta2.pdf", calibration="prediction",
        calib={"xTicks": [[round(p, 2), v] for p, v in xt], "yTicks": [[round(p, 2), v] for p, v in yt], "labels": "x: numeric tick labels 28 to 30; y: labels 1.6 to 2.8 read with the separate minus glyph"},
        uncertainty=0.02, retrieved="2026-10-25",
        note=f"Vector-path extraction; exact to PDF coordinate precision. The paper prints numbers that the extracted curves reproduce: {notes_chk}."))
    records[-1]["provenance"]["quotes"] = dict(Q)
    records[-1]["provenance"]["definitionBasis"] = ("dustTreatment and the stellar-population content are from the figure caption ('the solid line also including dust (i.e. that which would be observed)'). betaWindow and betaMethod: not stated in this paper. "
                                                    "imf and cosmology: as in the other FLARES records of this dataset (the paper's SED-modelling section refers to FLARES II).")
assert len(records) == 18
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} records; {len(checks)} checks passed:")
for c in checks:
    print("  -", c)
