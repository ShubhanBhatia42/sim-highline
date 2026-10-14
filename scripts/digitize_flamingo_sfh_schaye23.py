import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2306.04024"
DOI = "10.1093/mnras/stad2419"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
ROOT = Path(__file__).resolve().parent.parent
CITE = f"Schaye et al. 2023, MNRAS 526, 4978 (doi:{DOI}; arXiv:{ARXIV}), the FLAMINGO simulations"
BIN = 0.05
D3A, PLANCK = {"H0": 68.1, "Om": 0.306}, {"H0": 67.3, "Om": 0.316}
# left panel: fiducial model and cosmology at different resolutions and volumes (legend read against the swatch positions: column 1 L1_m9, L2p8_m9, L1_m10; column 2 L1_m8, MillenniumTNG, BAHAMAS)
LEFT = [((0.067, 0.467, 0.2), "L1_m9", "1 cGpc box, intermediate (m9) resolution, the fiducial run"), ((0.2, 0.133, 0.533), "L2p8_m9", "2.8 cGpc box, intermediate (m9) resolution"),
        ((0.867, 0.8, 0.467), "L1_m10", "1 cGpc box, low (m10) resolution"), ((0.8, 0.4, 0.467), "L1_m8", "1 cGpc box, high (m8) resolution")]
# right panel: the model variations in the 1 cGpc box at m9 resolution (legend columns, top to bottom, positions in the figure), as in the variation digitizer of the other FLAMINGO figures
VARS = [
    ("fgas+2s", (0.671, 0.816, 0.902), "fgas+2sigma", "cluster gas fractions shifted by +2 sigma before calibration, thermal AGN", D3A),
    ("fgas-2s", (0.416, 0.682, 0.839), "fgas-2sigma", "cluster gas fractions shifted by -2 sigma before calibration, thermal AGN", D3A),
    ("fgas-4s", (0.216, 0.529, 0.753), "fgas-4sigma", "cluster gas fractions shifted by -4 sigma before calibration, thermal AGN", D3A),
    ("fgas-8s", (0.063, 0.357, 0.643), "fgas-8sigma", "cluster gas fractions shifted by -8 sigma before calibration, thermal AGN", D3A),
    ("mstar-s", (1.0, 0.549, 0.251), "M*-sigma", "observed stellar masses decreased by the 0.14 dex systematic error before calibration, thermal AGN", D3A),
    ("mstar-s-fgas-4s", (0.8, 0.263, 0.078), "M*-sigma_fgas-4sigma", "stellar masses shifted by -1 sigma (0.14 dex) and cluster gas fractions by -4 sigma, thermal AGN", D3A),
    ("jet", (0.494, 1.0, 0.294), "Jet", "kinetic jet-like AGN feedback instead of thermal", D3A),
    ("jet-fgas-4s", (0.333, 0.882, 0.557), "Jet_fgas-4sigma", "kinetic jet AGN feedback with cluster gas fractions shifted by -4 sigma", D3A),
    ("planck", (0.267, 0.667, 0.6), "Planck", "Planck cosmology (h=0.673, Om=0.316, sigma8=0.812), fiducial galaxy formation model", PLANCK),
    ("planck-nu0p24fix", (0.6, 0.6, 0.2), "PlanckNu0p24Fix", "Planck cosmology with sum m_nu = 0.24 eV, other parameters fixed (sigma8=0.769)", PLANCK),
    ("planck-nu0p24var", (0.667, 0.267, 0.6), "PlanckNu0p24Var", "Planck-based cosmology with sum m_nu = 0.24 eV and h=0.662, Om=0.328 (sigma8=0.772)", {"H0": 66.2, "Om": 0.328}),
    ("ls8", (0.533, 0.133, 0.333), "LS8", "low-S8 cosmology (h=0.682, Om=0.305, sigma8=0.760)", {"H0": 68.2, "Om": 0.305}),
]
# the grey dashed (BAHAMAS) and dot-dashed (MillenniumTNG) curves drawn for reference in both panels are other simulations and are not extracted


def near(c, t, tol=0.01):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


page = vf.page_of(SRC / "Images" / "SFH_2_Panel.pdf")
sha = vf.sha256(SRC / "Images" / "SFH_2_Panel.pdf")
left, right = vf.frames(page)
assert abs(left.y0 - right.y0) < 0.1 and abs(left.y1 - right.y1) < 0.1
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]


def xfit(fr):
    lab = [(cx, math.log10(1 + float(t))) for t, cx, cy in W if t in ("0", "0.2", "0.5", "1", "2", "3", "5", "10") and fr.x0 <= cx <= fr.x1 and cy > fr.y1]
    assert len(lab) == 8, (fr, lab)
    return vf.axis_fit(page, fr, "x", labels=lab)[0]


ylab = [(cy, float(t[2:].replace("−", "-"))) for t, cx, cy in W if t in ("10−1", "10−2", "10−3") and cx < left.x0]
assert len(ylab) == 3, ylab
fy, _ = vf.axis_fit_log2(page, left, "y", ylab)
fxl, fxr = xfit(left), xfit(right)
# Behroozi+19, Novak+17, Gruppioni+20, Enia+22 and Khusanova+21 are overlaid in the figure: the axes are cross-checked against the SFR density at which the legend text sits on the grid (the decade labels), nothing else is needed


def trace(frame, fx, colour):
    got = []
    for c in vf.curves(page, frame, fx, fy, min_items=40):
        if c["width"] == 1.5 and c["dashes"] == "[] 0" and near(c["color"], colour):
            got.append(c)
    assert len(got) == 1, (colour, len(got))
    pts = []
    for (rx, ry), (x, y) in zip(got[0]["raw"], got[0]["points"]):
        if frame.x0 - 0.3 <= rx <= frame.x1 + 0.3 and frame.y0 + 0.8 <= ry <= frame.y1 - 0.8:
            pts.append((10 ** x - 1, y))
    pts.sort()
    bins = {}
    for z, y in pts:
        if -0.001 <= z <= 14:
            bins.setdefault(int(z / BIN + 1e-9), []).append((z, y))
    out = [(round(float(np.mean([p[0] for p in v])), 3), round(float(np.mean([p[1] for p in v])), 4)) for k, v in sorted(bins.items())]
    assert len(out) > 40 and all(a[0] < b[0] for a, b in zip(out, out[1:])), (colour, len(out))
    return out


def at(pts, z):
    return float(np.interp(z, [p[0] for p in pts], [p[1] for p in pts]))


curves = {}
for colour, name, what in LEFT:
    curves[name] = trace(left, fxl, colour)
for v in VARS:
    curves[v[2]] = trace(right, fxr, v[1])
# the fiducial run is drawn in both panels
fid_r = trace(right, fxr, LEFT[0][0])
a, b = curves["L1_m9"], fid_r
grid = np.arange(0.2, min(a[-1][0], b[-1][0]) - 0.1, 0.1)
dd = [abs(at(a, z) - at(b, z)) for z in grid]
print(f"L1_m9 left vs right panel: median |dlog10 SFRD| = {np.median(dd):.4f}, max = {max(dd):.3f}")
assert np.median(dd) < 0.01 and max(dd) < 0.03, (np.median(dd), max(dd))
# spot checks read from the axes: the fiducial rate peaks near z = 2 at about 0.1 Msun/yr/Mpc^3 and falls to about 0.015 at z = 0; the high-resolution run is the highest at z = 6, and the low-resolution run lies above the intermediate one at z = 6 (the paper explains this by its lower star formation threshold density) and below it at z = 1
f = curves["L1_m9"]
assert abs(at(f, 2.0) - math.log10(0.105)) < 0.12 and abs(at(f, 0.0) - math.log10(0.015)) < 0.12, (at(f, 2), at(f, 0))
assert at(curves["L1_m8"], 6.0) > at(f, 6.0) + 0.2 and at(curves["L1_m10"], 6.0) > at(f, 6.0) and at(curves["L1_m10"], 1.0) < at(f, 1.0), "m8 above m9 at z = 6 and, as the paper says, m10 above m9 at very high z because of its lower star formation threshold"
assert max(abs(at(curves["L2p8_m9"], z) - at(f, z)) for z in np.arange(0.3, 6, 0.3)) < 0.08, "L2p8_m9 lies on top of L1_m9 (the paper says the L1 runs are converged with box size)"
# independent check against the Illustris-1 and EAGLE records: the same physical quantity at z = 2 within a factor of about 2
ref = {}
for fname, rid in (("vogelsberger14-illustris.json", "vogelsberger14.illustris.sfrd.total"), ("furlong15-eagle-sfrd.json", "furlong15.eagle.sfrd.refl100n1504")):
    p = vf.reference_root() / "data" / "curves" / fname
    if p.exists():
        r = next((r for r in json.loads(p.read_text())["records"] if r["id"] == rid), None)
        if r:
            pts = [(q["x"], q["y"]) for q in r["representation"]["points"]]
            ref[rid] = at(pts, 2.0)
            assert abs(ref[rid] - at(f, 2.0)) < 0.3, (rid, ref[rid], at(f, 2.0))
print("FLAMINGO L1_m9 log SFRD at z=2:", round(at(f, 2.0), 3), "| references:", {k: round(v, 3) for k, v in ref.items()})

records = []


def mk(name, run, slug, what, cosmo, panel, desc):
    pts = curves[name]
    return vf.record(
        rid=f"schaye23.flamingo-{slug}.sfrd", source="FLAMINGO", run=run, relation="sfrd", z=2.0,
        axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 cosmic star formation rate density of the simulated volume", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
        points=pts, population="all star formation in the simulated volume", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
        definitions={"imf": "chabrier03", "cosmology": cosmo, "densityFrame": "comoving", "population": "all galaxies", "sfrIndicator": "instantaneous SFR", "sfrIntegrationLimit": "all gas particles in the simulated volume", "dustCorrection": "none"},
        citation=CITE + f", cosmic star formation rate density ({desc})", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="cosmic star formation rate density as a function of redshift", panel=panel, sha=sha, member="Images/SFH_2_Panel.pdf",
        calibration="prediction", uncertainty=0.02,
        calib="x: the eight tick labels (0 to 10) as log10(1+z); y: the three decade labels 10^-3 to 10^-1, validated by the minor-tick pattern of a log axis (the right panel shares the y axis)",
        warning=f"Cosmic star formation rate density of FLAMINGO {desc}, read from the vector path of Schaye et al. 2023 ({panel}); computed on the fly by summing the instantaneous SFRs of all gas particles (the paper's text). "
                "The curves lie below the data at z > 2 beyond a resolution-dependent redshift, where the haloes that dominate star formation are no longer resolved; the kink at z = 7.8 is reionization photo-heating and the small one at z = 2.9 the change of softening, as the paper explains. "
                "The paper does not say whether the density is comoving; the observational compilation in the same panel (Behroozi+19, Novak+17, Gruppioni+20, Enia+22, Khusanova+21) is comoving and the curves agree with it at z < 2, so comoving is inferred. "
                "The line is resampled on bins of 0.05 in z by the mean of log10 SFRD. The BAHAMAS and MillenniumTNG curves drawn for reference in the figure and the observational data are not extracted.")


for colour, name, what in LEFT:
    records.append(mk(name, name, name.lower(), what, D3A, "left panel (fiducial model and cosmology)", f"{name}: {what}"))
for slug, colour, name, desc, cosmo in VARS:
    records.append(mk(name, f"L1_m9 variation {name} (sfrd)", f"l1_m9-{slug}", desc, cosmo, "right panel (model variations)", f"variation {name} of the L1_m9 model: {desc}"))
out = ROOT / "data" / "curves" / "schaye23-flamingo-sfh.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FLAMINGO cosmic star formation history records")
for r in records:
    p = r["representation"]["points"]
    print(f"{r['id']:52s} {len(p):4d} z {p[0]['x']:.2f}->{p[-1]['x']:.2f}  log SFRD {p[0]['y']:.2f} -> {p[-1]['y']:.2f}  at z=2: {at([(q['x'], q['y']) for q in p], 2.0):.2f}")
