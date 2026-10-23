"""Artale et al. 2018 (arXiv:1805.06938, MNRAS 480, 3978): HOD of EAGLE (L0100N1504) and Illustris-1 at z=0 for stellar-mass-ranked samples of fixed
number density n = 0.0316, 0.01, 0.00316 h^3 Mpc^-3, halo mass M200 (critical).
 (a) digitized-figure records: measured <N(M200)> curves of the figure HOD-Comparison-EAGLE-Illustris (left panel, all galaxies, 3 n x 2 simulations) and
     HOD-Comparison-CenSat-ND0.0316 (right panel, n=0.0316, central and satellite, 2 simulations);
 (b) published-fit records: the paper's parametrisation (appendix, eqs. Cen_HOD, Sat_HOD, total) evaluated with the parameters of tables M1MminEAGLE / M1MminIllustris.
Verification: axes calibrated on the decade ticks (labels 10^10..10^14, 10^-2..10^2 asserted from the text layer), horizontal reference lines N=0.5 and N=1 of the figure,
and the tabulated log M_min (N_cen = 0.5) and log M_1 (N_sat = 1) against the digitized central/satellite curves; fit versus measured curve within the fit range.
Run: python3 -I digitize_hod_artale18.py [path-to-unpacked-arxiv-source]
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parent))      
import vector_figure as vf  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "hod-artale18.json"
ARXIV = "1805.06938"
DOI = "10.1093/mnras/sty2110"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
tex = (SRC / "Artale-HOD.tex").read_text(errors="replace").split("\n")
tmp = Path(tempfile.mkdtemp(prefix="a18_"))


def pdf_of(name):
    subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dEPSCrop", "-sDEVICE=pdfwrite", f"-sOutputFile={tmp/(name+'.pdf')}", str(SRC / (name + ".eps"))], check=True)
    return vf.page_of(tmp / (name + ".pdf")), vf.sha256(SRC / (name + ".eps"))


# ------------------------------------------------------------ tables
def table(label):
    i = next(k for k, l in enumerate(tex) if f"\\label{{{label}}}" in l)
    rows = {}
    for l in tex[i:i + 14]:
        m = re.match(r"^\s*(\d\.\d\d)\$\\times 10\^\{-(\d)\}\$\s*&(.*)\\\\", l)
        if m:
            n = float(m.group(1)) * 10 ** (-int(m.group(2)))
            v = [float(re.search(r"-?\d+\.\d+", c).group(0)) for c in m.group(3).split("&")]
            rows[round(n, 5)] = dict(alpha=v[0], lcut=v[1], sig=v[2], lm1=v[3], lmin=v[4], ratio=v[5])
    assert sorted(rows) == [0.00316, 0.01, 0.0316], rows.keys()
    return rows


TAB = {"EAGLE": table("tab:M1MminEAGLE"), "Illustris": table("tab:M1MminIllustris")}
assert TAB["EAGLE"][0.0316] == dict(alpha=0.92, lcut=11.49, sig=0.202, lm1=12.21, lmin=11.149, ratio=11.51)
assert TAB["Illustris"][0.01]["lm1"] == 12.62 and TAB["Illustris"][0.00316]["lmin"] == 12.094
# internal consistency of the table: M1/Mmin = 10^(log M1 - log Mmin) (3 s.f.)
for s in TAB:
    for n, p in TAB[s].items():
        assert abs(10 ** (p["lm1"] - p["lmin"]) - p["ratio"]) / p["ratio"] < 0.02, (s, n, 10 ** (p["lm1"] - p["lmin"]), p["ratio"])

# ------------------------------------------------------------ figures
GREEN, RED = (0.0, 0.5, 0.0), (1.0, 0.0, 0.0)


def calib(page):
    """log10 axes calibrated on the 6 pt major ticks; the decade labels of the text layer (10^10..10^14, 10^-2..10^2) are asserted to be present"""
    fr = vf.frames(page)[0]
    words = {w[4] for w in page.get_text("words")}
    assert {"1010", "1011", "1012", "1013", "1014", "10\u22122", "10\u22121", "100", "101", "102"} <= words
    xs, ys = set(), set()
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if abs(a.x - b.x) < 0.05 and abs(max(a.y, b.y) - fr.y1) < 1 and abs(abs(a.y - b.y) - 6.0) < 0.1:
                xs.add(round(a.x, 2))
            if abs(a.y - b.y) < 0.05 and abs(min(a.x, b.x) - fr.x0) < 1 and abs(abs(a.x - b.x) - 6.0) < 0.1:
                ys.add(round(a.y, 2))
    xs, ys = sorted(xs), sorted(ys)
    assert len(xs) == 5 and len(ys) == 5, (xs, ys)
    kx, cx = np.polyfit(xs, [10, 11, 12, 13, 14], 1)
    ky, cy = np.polyfit(ys, [2, 1, 0, -1, -2], 1)
    assert np.allclose(kx * np.array(xs) + cx, [10, 11, 12, 13, 14], atol=0.005) and np.allclose(ky * np.array(ys) + cy, [2, 1, 0, -1, -2], atol=0.005)
    return fr, (lambda p: kx * p + cx), (lambda p: ky * p + cy)


def dig(page, fx, fy, color, dash, nth=0, width=1.5):
    cs = [c for c in vf.curves(page, vf.frames(page)[0], fx, fy, min_items=4) if c["color"] == color and c["dashes"].startswith(dash)]
    cs.sort(key=lambda c: c["raw"][0].x if False else min(p.x for p in c["raw"]))
    return cs


pageL, shaL = pdf_of("HOD-Comparison-EAGLE-Illustris")
frL, fxL, fyL = calib(pageL)
pageR, shaR = pdf_of("HOD-Comparison-CenSat-ND0.0316")
frR, fxR, fyR = calib(pageR)
# calibration assertions: frame bottom is 10^-2, left edge is 10^10 (labels at the frame edge); N=1 and N=0.5 grey reference lines of the figure
assert abs(fyL(frL.y1) - (-2)) < 0.02 and abs(fxL(frL.x0) - 10) < 0.02, (fyL(frL.y1), fxL(frL.x0))  # frame bottom 10^-2, left edge 10^10
refs = []
for d in pageL.get_drawings():
    for it in d["items"]:
        if it[0] == "l" and abs(it[1].y - it[2].y) < 0.01 and abs(it[1].x - it[2].x) > 300 and frL.y0 + 1 < it[1].y < frL.y1 - 1:
            refs.append(round(fyL(it[1].y), 3))
refs = sorted(set(refs))
assert len(refs) == 2 and abs(refs[1] - 0.0) < 0.01 and abs(refs[0] - np.log10(0.5)) < 0.01, refs        # the figure's grey dotted lines at N=0.5 and N=1


def inframe(c, fr, fx, fy):
    pts = [(fx(p.x), fy(p.y)) for p in c["raw"] if fr.x0 - 0.01 <= p.x <= fr.x1 + 0.01 and fr.y0 - 0.01 <= p.y <= fr.y1 + 0.01]
    return pts


left = {}
for color, sim in ((GREEN, "EAGLE"), (RED, "Illustris")):
    cs = [c for c in vf.curves(pageL, frL, fxL, fyL, min_items=4) if c["color"] == color]
    cs.sort(key=lambda c: min(p.x for p in c["raw"] if p.y < frL.y1 - 0.5))
    assert len(cs) == 3
    for c, n in zip(cs, (0.0316, 0.01, 0.00316)):
        left[(sim, n)] = inframe(c, frL, fxL, fyL)
right = {}
for color, sim in ((GREEN, "EAGLE"), (RED, "Illustris")):
    cs = [c for c in vf.curves(pageR, frR, fxR, fyR, min_items=4) if c["color"] == color]
    for c in cs:
        kind = "all" if c["dashes"].startswith("[]") else "satellite" if c["dashes"].startswith("[ 5.6") else "central"
        right[(sim, kind)] = inframe(c, frR, fxR, fyR)
assert len(right) == 6

# the all-galaxy curve of the right panel must coincide with the left-panel n=0.0316 curve
for sim in ("EAGLE", "Illustris"):
    a, b = np.array(left[(sim, 0.0316)]), np.array(right[(sim, "all")])
    assert a.shape == b.shape and np.max(np.abs(a - b)) < 0.01, (sim, a.shape, b.shape)


def cross(pts, level):
    """first upward crossing of log10 N = level, linear interpolation between the plotted vertices"""
    p = np.array(pts)
    for (x0, y0), (x1, y1) in zip(p[:-1], p[1:]):
        if y0 < level <= y1:
            return x0 + (level - y0) * (x1 - x0) / (y1 - y0)
    raise AssertionError


CHK = {}
for sim in ("EAGLE", "Illustris"):
    t = TAB[sim][0.0316]
    cm = cross(right[(sim, "central")], np.log10(0.5))
    sm = cross(right[(sim, "satellite")], 0.0)
    CHK[sim] = (cm, t["lmin"], sm, t["lm1"])
    assert abs(cm - t["lmin"]) < 0.06 and abs(sm - t["lm1"]) < 0.06, (sim, CHK[sim])


# ------------------------------------------------------------ parametric evaluation
def model(lm, p, kind):
    ncen = 0.5 * (1 + erf((lm - p["lmin"]) / p["sig"]))
    m1s = 10 ** p["lm1"] - 10 ** p["lcut"]
    base = (10 ** lm - 10 ** p["lcut"]) / m1s
    nsat = np.where(base > 0, np.abs(base) ** p["alpha"], 0.0)
    return {"all": ncen + nsat, "central": ncen, "satellite": nsat}[kind]


from scipy.optimize import brentq
for sim in TAB:                                   # the evaluated expressions reproduce the tabulated characteristic masses (N_cen = 0.5 at M_min, N_sat = 1 at M_1)
    for n, p in TAB[sim].items():
        mmin = brentq(lambda lm: float(model(np.array(lm), p, "central")) - 0.5, p["lmin"] - 1, p["lmin"] + 1)
        mone = brentq(lambda lm: float(model(np.array(lm), p, "satellite")) - 1.0, p["lcut"] + 1e-6, p["lm1"] + 2)
        assert abs(mmin - p["lmin"]) < 1e-3 and abs(mone - p["lm1"]) < 1e-3, (sim, n, mmin, mone)

FITCHK = {}
for (sim, n), pts in left.items():
    p = np.array(pts)
    m = (10 ** p[:, 1] >= 0.1) & (10 ** p[:, 1] <= 31.6)          # fit range stated in the appendix: <N> = 10^-1 ... 10^1.5
    d = p[m, 1] - np.log10(model(p[m, 0], TAB[sim][n], "all"))
    FITCHK[(sim, n)] = (float(np.sqrt(np.mean(d ** 2))), float(np.max(np.abs(d))), int(m.sum()))
    assert FITCHK[(sim, n)][1] < 0.15, (sim, n, FITCHK[(sim, n)])

# ------------------------------------------------------------ records
SIMINFO = {
    "EAGLE": dict(source="EAGLE", run="L0100N1504 (Ref)", cosmo={"H0": 67.77, "Om": 0.307},
                  cq="Planck13 footnote of the paper: Omega_Lambda = 0.693, Omega_b = 0.0482, h = 0.6777 (the footnote prints 'Omega_m = 0.2588', which is Omega_dark in Artale+17; flat Omega_m = 0.307 is used)"),
    "Illustris": dict(source="Illustris", run="Illustris-1", cosmo={"H0": 70.4, "Om": 0.2726}, cq="footnote of the paper: Omega_m = 0.2726, Omega_Lambda = 0.7274, h = 0.704"),
}
Q_SEL = "ranking galaxies by stellar mass, corresponding to n = (0.0316,0.01,0.00316) h^3 Mpc^-3"
Q_HALO = ("the mass of the halo (M200) defined as the total mass (i.e., the sum over dark matter and baryonic mass) enclosed within a sphere with a density equal to 200 times the critical density")
CITE = "Artale et al. 2018, MNRAS 480, 3978 (arXiv:1805.06938)"


def base_rec(sim, n, kind, label, pts, tier, fig=None, sha=None, panel=None):
    info = SIMINFO[sim]
    sel = f"galaxies ranked by stellar mass at fixed comoving number density n = {n:g} h^3 Mpc^-3 (z = 0); {sim} {info['run']}; central/satellite as provided by the simulation teams"
    xs = [round(float(x), 3) for x, _ in pts]
    r = {"id": f"artale18.{sim.lower()}.hod.n{str(n).replace('.', 'p')}.{kind}.{label}", "source": info["source"], "run": f"{info['run']}, n = {n:g} h^3 Mpc^-3, {kind} ({label})",
         "kind": "simulation", "relation": "hod",
         "epoch": {"zRepresentative": 0, "zNominal": 0, "zMin": 0, "zMax": 0, "mode": "published-epoch", "snapshot": None},
         "axes": {"xDefinition": "log10 halo mass M200 (total mass within a sphere of 200 times the critical density, from the hydrodynamical run)", "xUnit": "log10(h^-1 Msun)",
                  "yDefinition": f"log10 mean number of {kind if kind != 'all' else 'central plus satellite'} galaxies per halo <N(M200)>", "yUnit": "log10(number per halo)"},
         "domain": {"xMin": xs[0], "xMax": xs[-1]}, "scatter": None,
         "definitions": {"galaxyType": kind, "sampleSelection": sel, "sampleSelectionQuote": Q_SEL, "haloMassDefinition": "M200crit", "haloMassDefinitionQuote": Q_HALO, "massUnit": "h^-1 Msun",
                         "massDefinition": "unspecified", "imf": "chabrier03", "cosmology": info["cosmo"], "cosmologyQuote": info["cq"], "numberDensity": n, "numberDensityUnit": "h^3 Mpc^-3 (comoving)"},
         "provenance": {"tier": tier, "citation": CITE, "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-18"},
         "calibration": "prediction", "rankable": tier != "digitized-figure"}
    return r


recs = []
for (sim, n), pts in left.items():
    r = base_rec(sim, n, "all", "measured, Fig. HOD-ND left", pts, "digitized-figure")
    r["representation"] = {"type": "points", "intervalKind": "unspecified", "connect": True, "points": [{"x": round(float(x), 3), "y": round(float(y) + 0.0, 4)} for x, y in pts]}
    r["selection"] = {"population": f"all galaxies of the stellar-mass-ranked sample n = {n:g} h^3 Mpc^-3",
                      "warning": "Measured mean occupation (halo-mass bins of ~0.24 dex, points joined by lines in the paper) read from the vector paths of the left panel of the figure comparing EAGLE and Illustris HODs (Artale+18). "
                                 "Curve is clipped by the frame at <N> >= 0.01. No uncertainties are drawn (the paper's jackknife errors are in its tables of fit parameters). The galaxy sample is defined by number density, so the stellar-mass cut differs between simulations; the paper gives no table of the curve. "
                                 "Stellar-mass aperture is not stated in this paper."}
    r["provenance"].update({"figure": "Figure 'HOD-ND' (left panel)", "panel": "left", "checksumSha256": shaL, "sourceMember": "HOD-Comparison-EAGLE-Illustris.eps",
                            "extractionMethod": "vector path vertices (EPS converted with ghostscript, PyMuPDF get_drawings), log axes calibrated on decade labels/ticks",
                            "axisCalibrationPixels": "x decades 10^10..10^14 and y decades 10^-2..10^2 from the text layer; frame bottom = 10^-2, left = 10^10; grey reference lines at N=1 and 0.5 reproduced",
                            "digitizationUncertaintyDex": 0.01})
    r["notes"] = "Vector-path extraction; exact to PDF coordinate precision."
    recs.append(r)
for (sim, kind), pts in right.items():
    if kind == "all":
        continue
    n = 0.0316
    r = base_rec(sim, n, kind, "measured, Fig. HOD-ND right", pts, "digitized-figure")
    r["representation"] = {"type": "points", "intervalKind": "unspecified", "connect": True, "points": [{"x": round(float(x), 3), "y": round(float(y) + 0.0, 4)} for x, y in pts]}
    r["selection"] = {"population": f"{kind} galaxies of the stellar-mass-ranked sample n = {n:g} h^3 Mpc^-3",
                      "warning": f"Measured mean {kind} occupation read from the right panel of the figure (central: dotted line, satellite: dashed line, per caption). Clipped by the frame at <N> >= 0.01. "
                                 f"Checked against the table: curve crosses <N_cen> = 0.5 at log M = {CHK[sim][0]:.3f} (table log M_min = {CHK[sim][1]}) and <N_sat> = 1 at log M = {CHK[sim][2]:.3f} (table log M_1 = {CHK[sim][3]})."}
    r["provenance"].update({"figure": "Figure 'HOD-ND' (right panel)", "panel": "right", "checksumSha256": shaR, "sourceMember": "HOD-Comparison-CenSat-ND0.0316.eps",
                            "extractionMethod": "vector path vertices (EPS converted with ghostscript, PyMuPDF get_drawings), log axes calibrated on decade labels/ticks",
                            "axisCalibrationPixels": "as for the left panel (same axes)", "digitizationUncertaintyDex": 0.01})
    r["notes"] = "Vector-path extraction; exact to PDF coordinate precision."
    recs.append(r)
EQ = ("<N_cen> = 1/2[1 + erf((log M_h - log M_min)/sigma_logM)]; <N_sat> = ((M_h - M_cut)/M_1*)^alpha with M_1 = M_1* + M_cut; <N_gal> = <N_cen> + <N_sat> (Artale+18 appendix, eqs. Cen_HOD, Sat_HOD)")
for sim in ("EAGLE", "Illustris"):
    for n in (0.0316, 0.01, 0.00316):
        p = TAB[sim][n]
        pts0 = left[(sim, n)]
        lo, hi = min(x for x, _ in pts0), max(x for x, _ in pts0)
        grid = np.round(np.arange(np.ceil(lo * 100) / 100, hi + 1e-9, 0.01), 3)
        N = model(grid, p, "all")
        keep = (N >= 0.1) & (N <= 31.6)
        pts = [(float(x), float(np.log10(v))) for x, v in zip(grid[keep], N[keep])]
        r = base_rec(sim, n, "all", "fit of the paper", pts, "published-fit")
        r["representation"] = {"type": "points", "intervalKind": "unspecified", "connect": True, "points": [{"x": x, "y": round(y + 0.0, 4)} for x, y in pts]}
        r["domain"] = {"xMin": pts[0][0], "xMax": pts[-1][0]}
        r["selection"] = {"population": f"all galaxies of the stellar-mass-ranked sample n = {n:g} h^3 Mpc^-3",
                          "warning": f"Evaluated by sim-highline from the paper's fit parameters (alpha = {p['alpha']}, log M_cut = {p['lcut']}, sigma_logM = {p['sig']}, log M_1 = {p['lm1']}, log M_min = {p['lmin']}; halo masses in h^-1 Msun): {EQ}. "
                                     "Evaluated every 0.01 dex over the fit range <N> = 10^-1 ... 10^1.5 (appendix) and inside the measured halo-mass range; below M_cut the satellite term is set to zero (the printed power law is undefined there). "
                                     "The fit is to the measured HOD with jackknife errors from 27 sub-volumes (parameter errors in the table are not propagated)."}
        r["provenance"].update({"figure": f"Table of HOD parameters ({'M1MminEAGLE' if sim == 'EAGLE' else 'M1MminIllustris'}), appendix 'Fitting the HOD predicted by EAGLE and Illustris'",
                                "sourceMember": "Artale-HOD.tex", "extractionMethod": "published parameterisation evaluated numerically"})
        f = FITCHK[(sim, n)]
        r["notes"] = f"Verified against the measured curve of the paper's figure (digitized): rms {f[0]:.3f}, max {f[1]:.3f} dex over {f[2]} points of the fit range; table internal consistency M_1/M_min = 10^(log M_1 - log M_min) reproduces the tabulated ratio to 2 per cent."
        recs.append(r)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=1) + "\n")
print(f"wrote {len(recs)} records")
print("cross checks (central@0.5, table Mmin, satellite@1, table M1):", {k: tuple(round(x, 3) for x in v) for k, v in CHK.items()})
print("fit vs measured (rms, max, n):", {f"{k[0]} n={k[1]}": tuple(round(x, 3) for x in v) for k, v in FITCHK.items()})
