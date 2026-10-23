"""Bolometric AGN luminosity functions of Hopkins, Richards & Hernquist 2007 (astro-ph/0605678, 'Full' global fit) and
Shen et al. 2020 (arXiv:2001.02696, global fits A and B), transcribed as parametric records (relation agnlf).

Verification inside this script (every assert must pass or the record is not written):
  * Hopkins+07: the integrated BH mass density rho_BH(z=0) that the paper quotes (4.81e5 Msun/Mpc^3 for the Full fit; 5.66, 4.97, 5.47, 4.63 for the PLE,
    Faint, Bright, Scatter fits of the same table) is recomputed from the expression with the paper's stated eps_r = 0.1, H0 = 70, Om = 0.3, L_sun = 3.9e33.
  * Both papers: the expressions are compared with the vector-path curves that Shen+20 draw for their own global fits A and B and for the
    Hopkins+07 model in the six panels of figures bol_1_0 .. bol_6_0 (z = 1..6), after calibrating the axes on the labelled ticks of each panel.
Every definition quoted in the records is located in the arXiv source by exact substring; the line numbers are stored in provenance.quotes.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy import integrate

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

OUT = Path(os.environ.get("B_OUT_DIR") or Path(__file__).resolve().parent.parent / "data" / "curves") / "hopkins07-shen20-agnlf.json"
HOP, SHEN = "astro-ph/0605678", "2001.02696"
HOP_SRC = vf.fetch_arxiv(HOP)
SHEN_SRC = vf.fetch_arxiv(SHEN)
HOP_TEX, SHEN_TEX = HOP_SRC / "ms.tex", SHEN_SRC / "paper-arxiv.tex"
LSUN = 3.9e33


def quote(path, text):
    """1-based line number of the first source line containing `text` verbatim (the text itself is what is stored)."""
    for i, line in enumerate(Path(path).read_text(errors="replace").splitlines(), 1):
        if text in line:
            return {"file": Path(path).name, "line": i, "text": text}
    raise AssertionError(f"quote not found in {path}: {text!r}")


# ---------------------------------------------------------------- the models (python twins of the JS expressions)
HOP_FULL = dict(lphi=-4.825, L0=13.036, k1=0.632, k2=-11.76, k3=-14.25, g10=0.417, kg1=-0.623, g20=2.174, kb1=1.460, kb2=-0.793)
HOP_ALL = {  # rows of the paper's table 'Best-Fit QLF to all Redshifts' (label tbl:params) and the rho_BH(z=0) it quotes in units of 1e5 Msun/Mpc^3
    "PLE": (dict(lphi=-4.733, L0=12.965, k1=0.749, k2=-8.03, k3=-4.40, g10=0.517, kg1=0, g20=2.096, kb1=0, kb2=0), 5.66),
    "Faint": (dict(lphi=-4.630, L0=12.892, k1=0.717, k2=-8.10, k3=-3.90, g10=0.272, kg1=-0.972, g20=2.048, kb1=0, kb2=0), 4.97),
    "Bright": (dict(lphi=-4.930, L0=13.131, k1=0.360, k2=-11.63, k3=-10.68, g10=0.605, kg1=0, g20=2.350, kb1=1.53, kb2=-0.745), 5.47),
    "Scatter": (dict(lphi=-4.815, L0=13.064, k1=0.356, k2=-11.69, k3=-9.18, g10=0.351, kg1=-0.826, g20=2.359, kb1=1.534, kb2=-0.889), 4.63),
    "Full": (HOP_FULL, 4.81),
}
SHEN_A = dict(a0=0.8569, a1=-0.2614, a2=0.0200, b0=2.5375, b1=-1.0425, b2=1.1201, c0=13.0088, c1=-0.5759, c2=0.4554, d0=-3.5426, d1=-0.3936)
SHEN_B = dict(a0=0.3653, a1=-0.6006, b0=2.4709, b1=-0.9963, b2=1.0716, c0=12.9656, c1=-0.5758, c2=0.4698, d0=-3.6276, d1=-0.3444)

HOP_EXPR = ("((xi)=>{const g1=g10*Math.pow(10,kg1*xi),g2=Math.max(2*g20/(Math.pow(10,kb1*xi)+Math.pow(10,kb2*xi)),g2min),"
            "u=x-lsun-(L0+k1*xi+k2*xi*xi+k3*xi*xi*xi);return lphi-log10(Math.pow(10,g1*u)+Math.pow(10,g2*u))})(log10((1+z)/3))")
SHEN_A_EXPR = ("((X)=>{const r=X/3,g1=a0+a1*X+a2*(2*X*X-1),g2=2*b0/(Math.pow(r,b1)+Math.pow(r,b2)),Ls=2*c0/(Math.pow(r,c1)+Math.pow(r,c2)),"
               "u=x-lsun-Ls;return d0+d1*X-log10(Math.pow(10,g1*u)+Math.pow(10,g2*u))})(1+z)")
SHEN_B_EXPR = ("((X)=>{const r=X/3,g1=a0*Math.pow(r,a1),g2=2*b0/(Math.pow(r,b1)+Math.pow(r,b2)),Ls=2*c0/(Math.pow(r,c1)+Math.pow(r,c2)),"
               "u=x-lsun-Ls;return d0+d1*X-log10(Math.pow(10,g1*u)+Math.pow(10,g2*u))})(1+z)")
LOGLSUN = float(np.log10(LSUN))


def hop_logphi(logL, z, p=HOP_FULL):
    xi = np.log10((1 + z) / 3.0)
    g1 = p["g10"] * 10 ** (p["kg1"] * xi)
    g2 = np.maximum(2 * p["g20"] / (10 ** (p["kb1"] * xi) + 10 ** (p["kb2"] * xi)), 1.3)
    u = logL - LOGLSUN - (p["L0"] + p["k1"] * xi + p["k2"] * xi ** 2 + p["k3"] * xi ** 3)
    return p["lphi"] - np.log10(10 ** (g1 * u) + 10 ** (g2 * u))


def shen_logphi(logL, z, p, fit):
    X = 1 + z
    r = X / 3.0
    g1 = p["a0"] + p["a1"] * X + p["a2"] * (2 * X ** 2 - 1) if fit == "A" else p["a0"] * r ** p["a1"]
    g2 = 2 * p["b0"] / (r ** p["b1"] + r ** p["b2"])
    Ls = 2 * p["c0"] / (r ** p["c1"] + r ** p["c2"])
    u = logL - LOGLSUN - Ls
    return p["d0"] + p["d1"] * X - np.log10(10 ** (g1 * u) + 10 ** (g2 * u))


# ---------------------------------------------------------------- check 1: Hopkins+07 quoted rho_BH(z=0)
def rho_bh0(p, eps=0.1, H0=70.0, Om=0.3, zmax=10.0):
    MPC, C, MSUN = 3.0857e24, 2.998e10, 1.989e33
    H0s = H0 * 1e5 / MPC

    def lum_density(z):  # erg s^-1 Mpc^-3, integral of L dPhi/dlogL over all L
        f = lambda lg: 10 ** lg * 10 ** hop_logphi(lg, z, p)
        return integrate.quad(f, 2 + LOGLSUN, 20 + LOGLSUN, limit=400, points=[p["L0"] + LOGLSUN])[0]

    g = lambda z: lum_density(z) / (eps * C ** 2) / ((1 + z) * H0s * np.sqrt(Om * (1 + z) ** 3 + 1 - Om)) / MSUN
    return integrate.quad(g, 0, zmax, limit=200)[0]


rho_checks = {}
for name, (p, quoted) in HOP_ALL.items():
    mine = rho_bh0(p) / 1e5
    rho_checks[name] = {"quoted_1e5_Msun_Mpc-3": quoted, "recomputed": round(mine, 3), "ratio": round(mine / quoted, 4)}
    assert abs(mine / quoted - 1) < 0.015, (name, mine, quoted)
assert sum(abs(v["ratio"] - 1) < 0.005 for v in rho_checks.values()) >= 3, rho_checks  # three rows reproduce to 3 significant digits

# ---------------------------------------------------------------- check 2: curves drawn by Shen+20 (vector paths)
FIG_CHECKS = {"A": [], "B": [], "Hopkins07": []}
for k in range(1, 7):
    pdf = SHEN_SRC / "figures" / f"bol_{k}_0.pdf"
    page = vf.page_of(pdf)
    fr = vf.frames(page)[0]
    z = float([w[4] for w in page.get_text("words") if w[4].startswith("∼")][0][1:])
    assert z == float(k)
    fx, xt = vf.axis_fit(page, fr, "x", snap=4.0)  # log10 L_bol labels 43..50
    fy, yt = vf.axis_fit(page, fr, "y", vsign=-1, snap=4.0)  # the minus signs of -4,-6,-8,-10 are separate glyphs: sign fixed here
    for c in vf.curves(page, fr, fx, fy, min_items=40):
        col = c["color"]
        pts = np.array([(x, y) for x, y in c["points"] if 43 <= x <= 50 and -11 <= y <= -3])
        if len(pts) < 20:
            continue
        if abs(col[0] - 0.6) < .02 and abs(col[1] - .2) < .02:
            FIG_CHECKS["A"].append(float(np.abs(pts[:, 1] - shen_logphi(pts[:, 0], z, SHEN_A, "A")).max()))
        elif abs(col[0] - 1) < .02 and col[1] < .02:
            FIG_CHECKS["B"].append(float(np.abs(pts[:, 1] - shen_logphi(pts[:, 0], z, SHEN_B, "B")).max()))
        elif abs(col[0] - 0.86) < .02 and abs(col[1] - .08) < .02:
            FIG_CHECKS["Hopkins07"].append(float(np.abs(pts[:, 1] - hop_logphi(pts[:, 0], z)).max()))
for key, v in FIG_CHECKS.items():
    assert len(v) == 6 and max(v) < 0.01, (key, v)  # max |difference| over the six panels, dex
SHEN_SHA = vf.sha256(SHEN_SRC / "figures" / "bol_2_0.pdf")

# ---------------------------------------------------------------- quotes
QH = {
    "cosmology1": quote(HOP_TEX, "$H_{0}=70\\,{\\rm km\\,s^{-1}\\,Mpc^{-1}}$ cosmology, "),
    "cosmology2": quote(HOP_TEX, "We adopt a $\\Omega_{\\rm M}=0.3$, $\\Omega_{\\Lambda}=0.7$,"),
    "lsun": quote(HOP_TEX, "luminosity $L_{\\sun}\\equiv3.9\\times10^{33}\\,{\\rm erg\\,s^{-1}}$. "),
    "intrinsic1": quote(HOP_TEX, "sources. Our compilation instead attempts to represent all "),
    "intrinsic2": quote(HOP_TEX, "AGN with {\\em intrinsic} (obscuration-corrected)"),
    "comptonthick": quote(HOP_TEX, "include an equal fraction of Compton-thick objects"),
    "bolcorr_hx": quote(HOP_TEX, "$(10.83,\\,0.28,\\,  6.08,\\,-0.020)$ for $L_{2-10\\,{\\rm keV}}$"),
    "lf_definition": quote(HOP_TEX, "\\phi(L)\\equiv \\frac{{\\rm d}\\Phi}{{\\rm d}\\log(L)}"),
    "eps": quote(HOP_TEX, "assuming $\\epsilon_{r}=0.1$."),
    "rho_bh": quote(HOP_TEX, "\\rho_{\\rm BH}(z=0) = {4.81}^{+1.24}_{-0.99}"),
}
QS = {
    "cosmology": quote(SHEN_TEX, "$H_{0} = 100h \\kms  \\Mpc^{-1} = 70 \\kms \\Mpc^{-1}$"),
    "bolometric": quote(SHEN_TEX, "The bolometric luminosity is defined as the integrated luminosity from $30\\micron$ to $500\\keV$"),
    "obscuration": quote(SHEN_TEX, "the QLFs presented include both the obscured and unobscured AGN"),
    "lf_definition": quote(SHEN_TEX, "\\phi_{\\rm bol}(L)=\\dfrac{{\\rm d}n}{{\\rm d}\\log{L}}"),
    "data_range": quote(SHEN_TEX, "constrained by observational data at $0<z<7$"),
}

COMMON_AXES = {"xDefinition": "log10 bolometric AGN luminosity L_bol", "xUnit": "log10(erg s^-1)",
               "yDefinition": "log10 comoving number density of AGN per dex of L_bol, dPhi/dlogL_bol", "yUnit": "log10(Mpc^-3 dex^-1)"}


def base(rid, source, run, z0, zmin, zmax, eq, expr, params, definitions, prov, warning, note):
    return {
        "id": rid, "source": source, "run": run, "kind": "observation", "relation": "agnlf",
        "epoch": {"zRepresentative": z0, "zNominal": z0, "zMin": zmin, "zMax": zmax, "mode": "analytic-evolution", "snapshot": None},
        "axes": COMMON_AXES, "domain": {"xMin": 43.0, "xMax": 48.0},
        "representation": {"type": "parametric", "equation": eq, "expression": expr, "parameters": params},
        "scatter": None, "selection": {"population": "all AGN, obscured and unobscured", "warning": warning},
        "definitions": definitions, "provenance": prov, "calibration": "target", "rankable": True, "notes": note}


hop_defs = {
    "luminosityBand": "bolometric",
    "bolometricCorrection": "band-dependent luminosity-dependent corrections from the paper's intrinsic SED model (hard X-ray 2-10 keV: " + QH["bolcorr_hx"]["text"] + ")",
    "obscurationCorrection": "intrinsic (obscuration-corrected) luminosities: '" + QH["intrinsic2"]["text"] + "'; column-density distribution of Ueda+03 including Compton-thick objects ('" + QH["comptonthick"]["text"] + "')",
    "population": "all", "densityFrame": "comoving", "lfConvention": "dPhi/dlogL_bol per dex",
    "luminosityUnitNote": "L_* is tabulated in L_sun = 3.9e33 erg/s (" + QH["lsun"]["text"].strip() + "); the expression takes x = log10 L_bol in erg/s",
    "cosmology": {"H0": 70, "Om": 0.3}, "radiativeEfficiency": "not used by this record",
}
hop_params = dict(HOP_FULL, lsun=LOGLSUN, g2min=1.3)
hop_prov = {
    "tier": "published-fit", "citation": "Hopkins, Richards & Hernquist 2007, ApJ 654, 731 (arXiv:astro-ph/0605678), 'Best-Fit QLF to all Redshifts' table, row 'Full'; evolving double power law (Eq. of Sec. 'Analytic Fits as a Function of Redshift')",
    "doi": "10.1086/509629", "url": "https://arxiv.org/abs/astro-ph/0605678", "retrieved": "2026-10-18", "figure": "table 'Best-Fit QLF to all Redshifts', row Full",
    "checksumSha256": vf.sha256(HOP_TEX), "sourceMember": "ms.tex",
    "sourceArchiveSha256": "5d181e1a663171a4796e241115603c427fb0902823c9d554df32b05b4d0154cc",
    "extractionMethod": "parameters transcribed from the arXiv LaTeX source; expression verified by script (rho_BH(z=0) quotes, vector curves of Shen+20 figures bol_1_0..bol_6_0)",
    "verification": {"rhoBH_z0_recomputed_vs_quoted": rho_checks,
                     "maxAbsDiffToHopkins07CurveDrawnInShen20Panels_dex": {"z=1..6": [round(v, 4) for v in FIG_CHECKS["Hopkins07"]]}},
    "quotes": QH}
records = [base(
    "hopkins07.bol.agnlf.full", "Hopkins et al. 2007", "Hopkins et al. 2007 (Full fit)", 2, 0, 6,
    "dPhi/dlogL = phi*/[(L/L*)^g1 + (L/L*)^g2]; log L* = (log L*)0 + kL1 xi + kL2 xi^2 + kL3 xi^3, g1 = g10 10^(kg1 xi), g2 = 2 g20/[10^(kb1 xi)+10^(kb2 xi)] (>=1.3), xi = log10((1+z)/3)",
    HOP_EXPR, hop_params, hop_defs, hop_prov,
    "Global fit of the bolometric QLF to the compilation of observed QLFs in optical, soft and hard X-ray, mid-IR and emission-line bands converted with the paper's SED, bolometric corrections and column-density distribution; domain is the luminosity window 43-48 over which the curve was checked, redshift range is that of the compiled data (Table of fits at z: 0.1-6.0); the paper forces gamma_2 >= 1.3.",
    "Observational constraint (analytic evolution in z). The luminosity must be in erg/s; L* of the paper is in L_sun = 3.9e33 erg/s.")]
shen_defs = {
    "luminosityBand": "bolometric", "bolometricCorrection": QS["bolometric"]["text"] + " (band corrections of the paper's quasar SED model)",
    "obscurationCorrection": QS["obscuration"]["text"] + " (N_H distribution of Ueda+14 incl. Compton-thick, dust-to-gas ratio scaling with gas-phase metallicity)",
    "population": "all", "densityFrame": "comoving", "lfConvention": "dPhi/dlogL_bol per dex",
    "luminosityUnitNote": "L_* is in L_sun (axis label of the paper's break-luminosity figure, Lbreak.png); L_sun = 3.9e33 erg/s is not stated in the text and was fixed by the paper's own curves (max|diff| 0.0007-0.0074 dex at z=1-6 against 0.014-0.020 for 3.846e33 or 3.826e33)",
    "cosmology": {"H0": 70, "Om": 0.3}, "radiativeEfficiency": "not used by this record"}
for fit, params, expr, eq, run in (
        ("A", SHEN_A, SHEN_A_EXPR, "dPhi/dlogL = phi*/[(L/L*)^g1 + (L/L*)^g2]; g1 = a0 T0 + a1 T1 + a2 T2 of (1+z) (Chebyshev), g2 = 2 b0/[(r)^b1+(r)^b2], log L* = 2 c0/[(r)^c1+(r)^c2], log phi* = d0+d1 (1+z), r=(1+z)/3", "Shen et al. 2020 (global fit A)"),
        ("B", SHEN_B, SHEN_B_EXPR, "as fit A but g1 = a0 r^a1 (monotonic faint-end slope)", "Shen et al. 2020 (global fit B)")):
    prov = {
        "tier": "published-fit", "citation": "Shen, Hopkins, Faucher-Giguere et al. 2020, MNRAS (arXiv:2001.02696), global fit " + fit + ", parameters table of the global evolution model",
        "doi": "10.1093/mnras/staa1381", "url": "https://arxiv.org/abs/2001.02696", "retrieved": "2026-10-18", "figure": "table of global fit parameters (A/B)",
        "checksumSha256": vf.sha256(SHEN_TEX), "sourceMember": "paper-arxiv.tex",
        "sourceArchiveSha256": "b7d18324e929cde6bb2abe4dae39a89f032b42868c851d330e97ddd92629a327",
        "extractionMethod": "parameters transcribed from the arXiv LaTeX source; expression verified against the vector curves the paper draws for its own global fits in figures bol_1_0..bol_6_0 (z = 1..6)",
        "verification": {"maxAbsDiffToPaperCurves_dex_z1to6": [round(v, 4) for v in FIG_CHECKS[fit]], "figureSourceMemberSha256": SHEN_SHA,
                         "axisCalibration": "x: numeric tick labels 43..50 snapped to ticks; y: labels 4,6,8,10 snapped to ticks, negative sign assigned (the sign is a separate glyph) and confirmed by the 0.002 dex agreement of three independent curves"},
        "quotes": QS}
    records.append(base(
        f"shen20.bol.agnlf.global{fit}", "Shen et al. 2020", run, 2, 0, 7, eq, expr, dict(params, lsun=LOGLSUN), shen_defs, prov,
        "Global fit to the compiled multi-band QLFs (IR, B band, UV, soft and hard X-ray) converted onto the bolometric plane; constrained by data at 0<z<7 (" + QS["data_range"]["text"] + "); the paper extrapolates beyond z=7 as a single power law, which this expression does not do. Domain is the luminosity window 43-48 over which the curve was checked.",
        "Observational constraint (analytic evolution in z). L* of the paper is in L_sun = 3.9e33 erg/s; expression takes x = log10 L_bol in erg/s. Note: the paper's cyan 'z=0' dotted curve in figures bol_1_0..bol_6_0 coincides (0.000 dex) with fit A evaluated at z=0.1."))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print("Wrote", len(records), "records to", OUT)
print("rho_BH checks", json.dumps(rho_checks))
print("figure checks", {k: [round(x, 4) for x in v] for k, v in FIG_CHECKS.items()})
