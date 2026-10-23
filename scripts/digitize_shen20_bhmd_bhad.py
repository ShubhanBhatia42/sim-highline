"""Black-hole mass density (bhmd) curves of Shen et al. 2020 (arXiv:2001.02696, figure bh_mass_density.pdf, vector) and black-hole
accretion-rate densities (bhad) computed from the published bolometric QLF fits of Shen+20 (global fit A) and Hopkins+07 (Full fit).

Checks asserted below:
  * axis calibration of the bhmd figure: x labels 0..7 snapped to the major ticks; y labels 2.5..6.0 sit 3.27 pt above their ticks (constant
    offset of the text boxes), so the ticks at y = 51.32 .. 587.63 pt are assigned 6.0 .. 2.5; the calibration is validated by the ticks being
    equally spaced (0.5 dex = 76.62 pt) and by the integration check below.
  * the rho_BH(z) the paper integrates is recomputed from fit A with the paper's formula (d rho/dz = (1-eps)/(eps c^2 H(z)(1+z)) * int L phi dlogL,
    eps = 0.1, 43 <= log L <= 48, H0=70, Om=0.3, zero density at the starting redshift z_i) and compared with the three digitized curves
    (z_i = 4, 7, 10); max |difference| is asserted to be below 0.04 dex.
  * rho_BH(z=0) of the digitized curves is asserted to agree to 0.01 dex between the z_i = 4, 7, 10 curves' common end value 5.71-5.72.
The bhad records are computed, not tabulated by either paper (tier published-fit, rankable false, warning in the record).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pymupdf
from scipy import integrate

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

OUT = Path(os.environ.get("B_OUT_DIR") or Path(__file__).resolve().parent.parent / "data" / "curves") / "shen20-hopkins07-bhmd-bhad.json"
SHEN, HOP = "2001.02696", "astro-ph/0605678"
SHEN_SRC, HOP_SRC = vf.fetch_arxiv(SHEN), vf.fetch_arxiv(HOP)
SHEN_TEX, HOP_TEX = SHEN_SRC / "paper-arxiv.tex", HOP_SRC / "ms.tex"
FIG = SHEN_SRC / "figures" / "bh_mass_density.pdf"
LSUN = 3.9e33
MPC, C, MSUN, YR = 3.0857e24, 2.998e10, 1.989e33, 3.156e7
H0S = 70e5 / MPC


def quote(path, text):
    for i, line in enumerate(Path(path).read_text(errors="replace").splitlines(), 1):
        if text in line:
            return {"file": Path(path).name, "line": i, "text": text}
    raise AssertionError(f"quote not found in {path}: {text!r}")


SHEN_A = dict(a0=0.8569, a1=-0.2614, a2=0.0200, b0=2.5375, b1=-1.0425, b2=1.1201, c0=13.0088, c1=-0.5759, c2=0.4554, d0=-3.5426, d1=-0.3936)
HOP_FULL = dict(lphi=-4.825, L0=13.036, k1=0.632, k2=-11.76, k3=-14.25, g10=0.417, kg1=-0.623, g20=2.174, kb1=1.460, kb2=-0.793)
LOGLSUN = np.log10(LSUN)


def shen_logphi(logL, z):
    p, X = SHEN_A, 1 + z
    r = X / 3.0
    g1 = p["a0"] + p["a1"] * X + p["a2"] * (2 * X ** 2 - 1)
    g2 = 2 * p["b0"] / (r ** p["b1"] + r ** p["b2"])
    Ls = 2 * p["c0"] / (r ** p["c1"] + r ** p["c2"])
    u = logL - LOGLSUN - Ls
    return p["d0"] + p["d1"] * X - np.log10(10 ** (g1 * u) + 10 ** (g2 * u))


def hop_logphi(logL, z):
    p = HOP_FULL
    xi = np.log10((1 + z) / 3.0)
    g1 = p["g10"] * 10 ** (p["kg1"] * xi)
    g2 = max(2 * p["g20"] / (10 ** (p["kb1"] * xi) + 10 ** (p["kb2"] * xi)), 1.3)
    u = logL - LOGLSUN - (p["L0"] + p["k1"] * xi + p["k2"] * xi ** 2 + p["k3"] * xi ** 3)
    return p["lphi"] - np.log10(10 ** (g1 * u) + 10 ** (g2 * u))


def shen_lumdens(z):  # erg s^-1 Mpc^-3, 43 <= log L <= 48
    return integrate.quad(lambda lg: 10 ** lg * 10 ** shen_logphi(lg, z), 43, 48, limit=200)[0]


def hop_lumdens(z):  # erg s^-1 Mpc^-3, all L ('integrating the best-fit luminosity function to L=0')
    return integrate.quad(lambda lg: 10 ** lg * 10 ** hop_logphi(lg, z), 2 + LOGLSUN, 20 + LOGLSUN, limit=400, points=[HOP_FULL["L0"] + LOGLSUN])[0]


def drho_dz(z, eps=0.1):
    return (1 - eps) / (eps * C ** 2) * shen_lumdens(z) / ((1 + z) * H0S * np.sqrt(0.3 * (1 + z) ** 3 + 0.7)) / MSUN


def rho_bh(z, zi):
    return integrate.quad(drho_dz, z, zi, limit=200)[0]


# ------------------------------------------------------------------ digitize the three integrated-curve paths
page = vf.page_of(FIG)
frame = pymupdf.Rect(140.4, 36.0, 993.6, 633.6)
major = sorted({round(d["rect"].y0, 2) for d in page.get_drawings() if d["width"] == 3.0 and d["rect"].height == 0 and d["rect"].width > 10})
assert len(major) == 8 and abs(np.diff(major) - 76.62).max() < 0.05, major
Y_LABELS = {w[4]: (w[1] + w[3]) / 2 for w in page.get_text("words") if w[4] in ("2.5", "3.0", "3.5", "4.0", "4.5", "5.0", "5.5", "6.0")}
offs = [Y_LABELS[f"{v:.1f}"] - t for v, t in zip((6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5), major)]
assert max(offs) - min(offs) < 0.02 and -3.6 < offs[0] < -3.0, offs  # constant text-box offset, so ticks carry the labels
fx, xt = vf.axis_fit(page, frame, "x", snap=4.0)
assert len(xt) == 8
fy = lambda p: 6.0 - (p - major[0]) / (major[1] - major[0]) * 0.5
COL = {(0.25, 0.41): 7, (0.86, 0.08): 10, (0.18, 0.55): 4}  # caption: 'The red, blue and green lines ... z_i = 10, 7, 4 respectively'
CAPTION = quote(SHEN_TEX, "The red, blue and green lines represent the predictions with starting redshift of integration $z_{\\rm i}=10,7,4$ respectively.")
curves = {}
for d in page.get_drawings():
    if d["type"] == "s" and d["width"] == 4.0 and len(d["items"]) > 50:
        c = tuple(round(v, 2) for v in d["color"])
        verts = [d["items"][0][1]] + [it[-1] for it in d["items"]]
        pts = sorted({(round(fx(p.x), 4), round(fy(p.y), 4)) for p in verts if frame.x0 <= p.x <= frame.x1 and frame.y0 <= p.y <= frame.y1})
        curves[COL[c[:2]]] = [p for p in pts if p[0] >= 0]
assert sorted(curves) == [4, 7, 10]
check = {}
for zi, pts in curves.items():
    xs = [p[0] for p in pts]
    assert all(a < b for a, b in zip(xs, xs[1:])), zi
    errs = [abs(y - np.log10(rho_bh(z, zi))) for z, y in pts[::6] if z < zi - 0.1]
    check[zi] = {"maxAbsDiffDex": round(max(errs), 3), "n": len(errs), "rho0_digitized_log10": pts[0][1], "z0_point": pts[0][0]}
    assert max(errs) < 0.04, (zi, max(errs))
    assert 5.70 < pts[0][1] < 5.72, (zi, pts[0])

# ------------------------------------------------------------------ quotes
Q = {
    "cosmology": quote(SHEN_TEX, "$H_{0} = 100h \\kms  \\Mpc^{-1} = 70 \\kms \\Mpc^{-1}$"),
    "eps": quote(SHEN_TEX, "Assuming a constant averaged radiative efficiency $\\epsilon_{\\rm r}\\simeq 0.1$"),
    "lbol": quote(SHEN_TEX, "L_{\\rm bol}=\\epsilon_{\\rm r}\\dot{M}c^{2}."),
    "rate": quote(SHEN_TEX, "the integrated luminosity density can be translated to the rate of change in the total SMBH mass density as:"),
    "formula": quote(SHEN_TEX, "\\dfrac{{\\rm d}\\rho_{\\rm BH}}{{\\rm d}z}=\\dfrac{1-\\epsilon_{\\rm r}}{\\epsilon_{\\rm r}c^{2}H(z)(1+z)}"),
    "limits": quote(SHEN_TEX, "where we adopt $\\log{L_{\\rm min}}=43,\\log{L_{\\rm max}}=48$ here."),
    "caption": CAPTION,
    "fitA": quote(SHEN_TEX, "we will only show the result of the global fit A and refer to it as \"the global fit\" for simplicity."),
    "hop_eps": quote(HOP_TEX, "assuming $\\epsilon_{r}=0.1$."),
    "hop_lbol": quote(HOP_TEX, "L_{\\rm bol} = \\epsilon_{r}\\,\\dot{M}\\,c^{2}"),
    "hop_int": quote(HOP_TEX, "We determine the luminosity density by integrating the best-fit "),
    "hop_cosmo": quote(HOP_TEX, "$H_{0}=70\\,{\\rm km\\,s^{-1}\\,Mpc^{-1}}$ cosmology, "),
}
SHEN_ARCH = "b7d18324e929cde6bb2abe4dae39a89f032b42868c851d330e97ddd92629a327"
HOP_ARCH = "5d181e1a663171a4796e241115603c427fb0902823c9d554df32b05b4d0154cc"
RETR = "2026-10-18"
records = []

# ------------------------------------------------------------------ bhmd (digitized)
for zi in (7, 10, 4):
    pts = curves[zi]
    records.append({
        "id": f"shen20.bhmd.fitA.zi{zi}", "source": "Shen et al. 2020", "run": f"Shen et al. 2020 (integrated bolometric QLF, global fit A, z_i={zi})", "kind": "observation", "relation": "bhmd",
        "epoch": {"zRepresentative": round(pts[-1][0] / 2, 3), "zNominal": 0, "zMin": 0, "zMax": pts[-1][0], "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic black-hole mass density integrated from the bolometric QLF", "yUnit": "log10(Msun cMpc^-3)"},
        "domain": {"xMin": pts[0][0], "xMax": pts[-1][0]},
        "representation": {"type": "points", "intervalKind": "unspecified", "connect": True, "points": [{"x": round(x, 3), "y": round(y, 4)} for x, y in pts]},
        "scatter": None,
        "selection": {"population": "all AGN (global fit A of the bolometric QLF, 43 <= log L_bol <= 48)",
                      "warning": f"Model curve integrated by the authors from z_i={zi} (zero initial mass density) down to z with eps_r=0.1; the grey/coloured shaded +-2x eps_r bands are not extracted; points are the vertices of the plotted path inside the frame (the curve leaves the frame below log rho=2.2 at high z). It is a prediction of the fitted QLF, not a measurement of local BH masses."},
        "definitions": {"densityFrame": "comoving", "bhMassMethod": "integrated accreted mass (Soltan argument) from the bolometric QLF", "radiativeEfficiency": 0.1,
                        "radiativeEfficiencyQuote": Q["eps"]["text"], "bhmdFormula": Q["formula"]["text"], "luminosityBand": "bolometric", "luminosityRange": Q["limits"]["text"],
                        "startRedshift": zi, "cosmology": {"H0": 70, "Om": 0.3}},
        "provenance": {"tier": "digitized-figure", "citation": "Shen et al. 2020, MNRAS (arXiv:2001.02696), predicted evolution of the cosmic SMBH mass density (figure bh_mass_density)",
                       "doi": "10.1093/mnras/staa1381", "url": "https://arxiv.org/abs/2001.02696", "retrieved": RETR, "figure": "Predicted evolution of the cosmic SMBH mass density at z=0-7", "panel": f"line with z_i={zi}",
                       "checksumSha256": vf.sha256(FIG), "sourceMember": "figures/bh_mass_density.pdf", "sourceArchiveSha256": SHEN_ARCH,
                       "extractionMethod": "vector path vertices from the figure PDF (PyMuPDF get_drawings), transformed through axes calibrated on the drawn major ticks",
                       "axisCalibrationPixels": "x: labels 0..7 snapped to ticks; y: 8 major ticks at y=51.32..587.63 pt equally spaced by 76.62 pt (0.5 dex) assigned 6.0..2.5 (label centres sit a constant 3.27 pt above the ticks)",
                       "digitizationUncertaintyDex": 0.01, "verification": {"recomputedFromFitA_maxAbsDiffDex": check[zi], "colourToStartRedshift": Q["caption"]["text"]}, "quotes": Q},
        "calibration": "target", "rankable": False, "notes": "Vector-path extraction; the integration check against the paper's own formula is in provenance.verification."})


# ------------------------------------------------------------------ bhad (computed from the published fits)
def bhad_points(lumdens, factor, zmax, step=0.25):
    zs = np.round(np.arange(0, zmax + 1e-9, step), 3)
    return [{"x": float(z), "y": round(float(np.log10(factor * lumdens(z) / C ** 2 / MSUN * YR)), 4)} for z in zs]


shen_pts = bhad_points(shen_lumdens, (1 - 0.1) / 0.1, 7.0)
hop_pts = bhad_points(hop_lumdens, 1 / 0.1, 6.0)
# internal consistency: integrating the computed Shen BHAD over time must give the digitized curve's z=0 value (z_i=7)
assert abs(np.log10(rho_bh(0.0, 7.0)) - curves[7][0][1]) < 0.03


def bhad_record(rid, source, run, pts, zmax, defs, prov, warning, note):
    return {"id": rid, "source": source, "run": run, "kind": "observation", "relation": "bhad",
            "epoch": {"zRepresentative": zmax / 2, "zNominal": 0, "zMin": 0, "zMax": zmax, "mode": "observational-bin", "snapshot": None},
            "axes": {"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 comoving black-hole accretion-rate density", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
            "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "unspecified", "connect": True, "points": pts},
            "scatter": None, "selection": {"population": "all AGN", "warning": warning}, "definitions": defs, "provenance": prov, "calibration": "target", "rankable": False, "notes": note}


records.append(bhad_record(
    "shen20.bhad.fitA", "Shen et al. 2020", "Shen et al. 2020 (global fit A, computed)", shen_pts, 7.0,
    {"luminosityBand": "bolometric", "radiativeEfficiency": 0.1, "radiativeEfficiencyQuote": Q["eps"]["text"], "densityFrame": "comoving",
     "bhadDefinition": "rate of change of the SMBH mass density per unit proper time, (1-eps)/(eps c^2) * int L phi dlogL over 43 <= log L_bol <= 48 (the integrand of: " + Q["formula"]["text"] + ")",
     "luminosityRange": Q["limits"]["text"], "cosmology": {"H0": 70, "Om": 0.3}},
    {"tier": "published-fit", "citation": "Shen et al. 2020, MNRAS (arXiv:2001.02696): the published global fit A of the bolometric QLF integrated with the paper's own formula",
     "doi": "10.1093/mnras/staa1381", "url": "https://arxiv.org/abs/2001.02696", "retrieved": RETR, "figure": "global fit A parameters table + integral formula of the SMBH mass density section",
     "checksumSha256": vf.sha256(SHEN_TEX), "sourceMember": "paper-arxiv.tex", "sourceArchiveSha256": SHEN_ARCH,
     "extractionMethod": "computed by this script from the published fit by quadrature (scipy), z step 0.25; NOT a table of the paper",
     "verification": {"timeIntegralOfThisCurve_vs_digitizedPaperCurve": {k: v for k, v in check[7].items()}, "all_start_redshifts": check}, "quotes": Q},
    "Computed from the published global fit A (the paper shows only the time-integrated mass density, not this rate). Mass-growth convention (1-eps)/eps, so this is eps-dependent and is NOT the accretion rate L/(eps c^2) of Hopkins+07; fit A is constrained by data at 0<z<7 only.",
    "Derived curve; checked by integrating it in time and comparing with the paper's own digitized rho_BH(z) curves (max 0.04 dex)."))
records.append(bhad_record(
    "hopkins07.bhad.full", "Hopkins et al. 2007", "Hopkins et al. 2007 (Full fit, computed)", hop_pts, 6.0,
    {"luminosityBand": "bolometric", "radiativeEfficiency": 0.1, "radiativeEfficiencyQuote": Q["hop_eps"]["text"], "densityFrame": "comoving",
     "bhadDefinition": "accretion-rate density L_bol-density/(eps c^2) with L_bol = eps Mdot c^2 (no (1-eps) factor; the factor was selected because only this form reproduces the paper's quoted rho_BH(z=0)=4.81e5 to 1%), luminosity density from integrating the QLF to L=0",
     "luminosityDensityQuote": Q["hop_int"]["text"], "cosmology": {"H0": 70, "Om": 0.3}},
    {"tier": "published-fit", "citation": "Hopkins, Richards & Hernquist 2007, ApJ 654, 731 (arXiv:astro-ph/0605678): the 'Full' bolometric QLF fit integrated over luminosity",
     "doi": "10.1086/509629", "url": "https://arxiv.org/abs/astro-ph/0605678", "retrieved": RETR, "figure": "'Best-Fit QLF to all Redshifts' table, row Full",
     "checksumSha256": vf.sha256(HOP_TEX), "sourceMember": "ms.tex", "sourceArchiveSha256": HOP_ARCH,
     "extractionMethod": "computed by this script from the published fit by quadrature (scipy), z step 0.25; NOT a table of the paper",
     "verification": {"timeIntegralReproducesQuotedRhoBH0": "see transcribe_agnlf_hopkins07_shen20.py: 4.861 vs 4.81 (1.1%) for this exact expression and eps=0.1"}, "quotes": {k: v for k, v in Q.items() if k.startswith("hop_")}},
    "Computed from the published Full fit (the paper plots the luminosity density and the integrated mass density, not this curve); accretion-rate convention L/(eps c^2) inferred from the paper's quoted rho_BH(z=0); fit range z<=6 of the compiled data, the paper extrapolates beyond.",
    "Derived curve, rankable false."))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print("Wrote", len(records), "records to", OUT)
print(json.dumps(check))
print("BHAD shen z=0,2,7:", [shen_pts[i] for i in (0, 8, 28)], "hopkins z=0,2,6:", [hop_pts[i] for i in (0, 8, 24)])
