"""REXCESS cluster scaling relations from two papers (arXiv sources parsed from the LaTeX tables):
 Pratt et al. 2009 (arXiv:0809.3784, A&A 498, 361): L_X - M500 (bolometric and [0.1-2.4] keV; with core, R<R500, and core-excised, 0.15-1 R500)
 Arnaud et al. 2010 (arXiv:0910.1234, A&A 517, A92): Y_SZ - M500 (Y_sph(R500) from the REXCESS pressure profiles, and the universal-profile Y_cyl relations).
Records: lxm published-table points (31 clusters x 4 luminosity definitions), lxm published-fit (BCES Y|X and orthogonal fits of the raw relations), ysz published-table points and published-fit.
M500 is not tabulated: it is computed from the tabulated R500 and z with the paper's own definition  M500 = 500 rho_c(z) (4 pi/3) R500^3, rho_c = h^2(z) 3 H0^2/(8 pi G),
h^2(z) = Omega_M (1+z)^3 + Omega_Lambda, H0 = 70, Omega_M = 0.3 (Pratt+09 footnote of Sect. 'Scaling'). Checked against the M500-Y_X relation of the papers.
Run: python3 -I ingest_rexcess_pratt09_arnaud10.py   (fetches the two arXiv sources through vector_figure.fetch_arxiv unless two paths are given)
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))      
import vector_figure as vf  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "lxm-ysz-rexcess.json"
SRC_P = Path(sys.argv[1]) if len(sys.argv) > 2 else vf.fetch_arxiv("0809.3784")
SRC_A = Path(sys.argv[2]) if len(sys.argv) > 2 else vf.fetch_arxiv("0910.1234")
SHA_P = "d3e149ed63839e172348b14a97b7a9221549631534be33a001b83d177e5c66ea"
SHA_A = "b9a965ef37d1ecedeb5f6fdb6f3c1d6beff0d62f6b5f383c937c3e63ff4833b9"
P = (SRC_P / "0944.tex").read_text(errors="replace").split("\n")
A = (SRC_A / "prexcess_sub.tex").read_text(errors="replace").split("\n")
OM = 0.3
G, MSUN, MPC = 6.67430e-11, 1.98847e30, 3.0856775814913673e22
Ez = lambda z: math.sqrt(OM * (1 + z) ** 3 + 1 - OM)


def m500(r_mpc, z):
    h = 70e3 / MPC * Ez(z)
    return 500 * 3 * h ** 2 / (8 * math.pi * G) * 4 / 3 * math.pi * (r_mpc * MPC) ** 3 / MSUN


def label_idx(lines, lab):
    return next(k for k, l in enumerate(lines) if f"\\label{{{lab}}}" in l or f"\\label  \n" in l and False)


def val_err(cell):
    """'$ 1.88_{-0.01}^{+0.01}$' -> (1.88, 0.01, 0.01); '$ 3.06\\pm0.16$' -> (3.06, 0.16, 0.16); plain -> (v, 0, 0)"""
    m = re.search(r"(-?\d+\.?\d*)_\{-(\d+\.?\d*)\}\^\{\+(\d+\.?\d*)\}", cell)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    m = re.search(r"(-?\d+\.?\d*)\s*\\pm\s*(\d+\.?\d*)", cell)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(2))
    return float(re.search(r"-?\d+\.?\d*", cell).group(0)), 0.0, 0.0


# ---------------------------------------------------------------- Pratt tables
i1 = next(k for k, l in enumerate(P) if "{tab:tab1}" in l)
t1 = []
for l in P[i1:i1 + 80]:
    if l.startswith("RXC"):
        c = [x.strip() for x in l.replace("\\\\", "").replace("\\ldots", "").split("&")]
        t1.append(dict(name=c[0].replace("\\,", " "), z=float(c[1]), L1=val_err(c[3]), L2=val_err(c[5]), YX=val_err(c[7]), R=float(c[8]) / 1000.0))
assert len(t1) == 31
i2 = next(k for k, l in enumerate(P) if "{tab:tabappx}" in l)
t2 = []
for l in P[i2:i2 + 80]:
    if l.startswith("RXC"):
        c = [x.strip() for x in l.replace("\\\\", "").split("&")]
        t2.append(dict(name=c[0].replace("\\,", " "), z=float(c[1]), L1=val_err(c[3]), L2=val_err(c[6])))
assert len(t2) == 31 and all(abs(a["z"] - b["z"]) < 1e-9 for a, b in zip(t1, t2))
# spot checks against the printed tables
assert t1[0]["name"] == "RXC J0003.8+0203" and t1[0]["z"] == 0.0924 and t1[0]["L1"] == (1.88, 0.01, 0.01) and t1[0]["R"] == 0.8767 and t1[-1]["L2"] == (0.97, 0.01, 0.01)
assert t2[0]["L1"] == (1.02, 0.01, 0.01) and t2[-1]["L1"] == (1.34, 0.01, 0.01) and t2[10]["L2"] == (0.98, 0.01, 0.01)
# Arnaud table
ia = next(k for k, l in enumerate(A) if "\\label{tab:pnfw}" in l)
ta = []
for l in A[ia:ia + 80]:
    if l.startswith("RXC"):
        c = [x.strip() for x in l.replace("\\\\", "").split("&")]
        ta.append(dict(name=c[0], R=float(c[1].replace("$", "")), YX=val_err(c[2]), Y2500=val_err(c[3]), Y500=val_err(c[4])))
assert len(ta) == 31 and ta[0]["Y500"] == (0.99, 0.036, 0.036) and ta[1]["Y500"] == (3.06, 0.16, 0.16) and ta[0]["R"] == 0.879
for a, b in zip(ta, t1):                       # same 31 clusters in the same (RA) order; the two papers differ in the decimals of some names, so match on the 4-digit RA
    assert re.search(r"J(\d{4})", a["name"]).group(1) == re.search(r"J(\d{4})", b["name"]).group(1), (a["name"], b["name"])

# ---------------------------------------------------------------- M500 and its check
M_P = np.array([m500(c["R"], c["z"]) for c in t1])             # from Pratt R500 (kpc / 1000)
M_A = np.array([m500(a["R"], c["z"]) for a, c in zip(ta, t1)])  # from Arnaud R500 (Mpc), z from the Pratt table
dev = np.array([math.log10(m500(c["R"], c["z"]) / (10 ** 14.567 * (c["YX"][0] * 1e13 / 2e14) ** 0.561 / Ez(c["z"]) ** 0.4)) for c in t1])
assert np.max(np.abs(dev)) < 0.03 and abs(np.mean(dev)) < 0.015, (np.max(np.abs(dev)), np.mean(dev))     # M500(R500) agrees with the M500-Y_X relation (Arnaud+10 eq. mynstd) used to iterate R500
MY_CHECK = (float(np.mean(dev)), float(np.max(np.abs(dev))))
dev2 = np.array([math.log10(m / n) for m, n in zip(M_A, M_P)])
DEV2 = float(np.max(np.abs(dev2)))
assert DEV2 < 0.08          # the two papers use slightly different M-Y_X calibrations, so R500 differ (max reported)

zs = np.array([c["z"] for c in t1])
ZREP, ZMIN, ZMAX = float(np.median(zs)), float(zs.min()), float(zs.max())


def fit_ols(x, y):
    s, c = np.polyfit(x, y, 1)
    return float(s), float(c)


def fit_orth(x, y):
    X = np.vstack([x - x.mean(), y - y.mean()])
    U, _, _ = np.linalg.svd(X)
    s = U[1, 0] / U[0, 0]
    return float(s), float(y.mean() - s * x.mean())


xP = np.log10(M_P / 2e14)
SCALE_L = lambda z: Ez(z) ** (7 / 3)
FIT = {}
for key, vals in {"bol-L1": [c["L1"][0] for c in t1], "bol-L2": [c["L2"][0] for c in t1], "soft-L1": [c["L1"][0] for c in t2], "soft-L2": [c["L2"][0] for c in t2]}.items():
    y = np.array([math.log10(v / SCALE_L(c["z"])) for v, c in zip(vals, t1)])
    FIT[key] = (fit_ols(xP, y), fit_orth(xP, y))
# published values (Pratt+09 tables lxrel and lxrelsoft; BCES(Y|X) and BCES orthogonal: C [1e44 erg/s], alpha)
PUB = {"bol-L1": ((1.81, 1.81), (1.74, 1.96)), "bol-L2": ((1.09, 1.77), (1.08, 1.80)), "soft-L1": ((1.03, 1.53), (0.98, 1.71)), "soft-L2": ((0.63, 1.49), (0.62, 1.52))}
LINES = "\n".join(P)
for tag in ("$1.81\\pm0.13$ & $1.81\\pm0.10$", "$1.74\\pm0.13$ & $1.96\\pm 0.11$", "$1.09\\pm 0.05$ & $1.77\\pm0.05$", "$1.08\\pm0.04$ & $1.80\\pm 0.05$", "$1.03\\pm0.08$ & $1.53\\pm0.10$", "$0.63\\pm0.03$ & $1.49\\pm0.05$"):
    assert tag in LINES, tag
REFIT = {}
for key, ((cy, ay), (co, ao)) in PUB.items():
    (sy, cyfit), (so, cofit) = FIT[key]
    REFIT[key] = dict(ols=(sy, 10 ** cyfit), orth=(so, 10 ** cofit))
    assert abs(sy - ay) < 0.03 and abs(10 ** cyfit / cy - 1) < 0.03, (key, "Y|X", sy, 10 ** cyfit, ay, cy)
    assert abs(so - ao) < 0.08 and abs(10 ** cofit / co - 1) < 0.08, (key, "orth", so, 10 ** cofit, ao, co)

# Y-M: refit with the Arnaud table against the published Y_sph(R500)-M500 relation (eq. mysz500: 10^-4.739, 1.790)
xA = np.log10(M_A / 3e14)
yA = np.array([math.log10(a["Y500"][0] * 1e-5 / Ez(c["z"]) ** (2 / 3)) for a, c in zip(ta, t1)])
sA, cA = fit_orth(xA, yA)
assert abs(sA - 1.790) < 0.015 and abs(cA - (-4.739)) < 0.005, (sA, cA)
YREFIT = (sA, cA, fit_ols(xA, yA))
# arithmetic of the universal-profile normalisations quoted by the paper: log10(2.925e-5 I(1)), J(1), I(5)
assert abs(math.log10(2.925e-5 * 0.6145) - (-4.745)) < 0.0006 and abs(math.log10(2.925e-5 * 0.7398) - (-4.665)) < 0.0006 and abs(math.log10(2.925e-5 * 1.1037) - (-4.491)) < 0.0006
for s in ("log(A_{\\rm x})\\!=\\!-4.745", "log(B_{\\rm x})=-4.665", "log(A_{\\rm x})=-4.491", "10^{-4.739\\pm0.003}", "1.790\\pm0.015"):
    assert s in "\n".join(A), s

# ---------------------------------------------------------------- records
URL_P, URL_A = "https://arxiv.org/abs/0809.3784", "https://arxiv.org/abs/0910.1234"
CITE_P = "Pratt et al. 2009, A&A 498, 361 (arXiv:0809.3784)"
CITE_A = "Arnaud et al. 2010, A&A 517, A92 (arXiv:0910.1234)"
SEL_REX = ("REXCESS: 31 nearby clusters selected from REFLEX by X-ray luminosity only (\"selected by luminosity only, in such a way as to have close to homogeneous coverage of luminosity space\"), "
           f"{ZMIN:.4f} <= z <= {ZMAX:.4f}; 'Pratt+09: M_Y = mass from the M500-Y_X relation of Arnaud+07'")
EPOCH = {"zRepresentative": round(ZREP, 4), "zMin": ZMIN, "zMax": ZMAX, "mode": "observational-bin", "snapshot": None}
COSMO = {"H0": 70, "Om": 0.3}
XDEF = "log10 M500 (mass inside the radius at which the mean density is 500 times the critical density at the cluster redshift; computed from the tabulated R500 and z; R500 iterated from the M500-Y_X relation)"


def pts_record(*, rid, source, run, relation, cite, doi, url, sha, table, axes, y_values, defs, warning, population, citation_member):
    pts = []
    for (v, lo, hi), m in zip(y_values, M_P if relation == "lxm" else M_A):
        p = {"x": round(math.log10(m), 4), "y": round(math.log10(v), 4)}
        if lo > 0 or hi > 0:
            p["yLow"], p["yHigh"] = round(math.log10(v - lo), 4), round(math.log10(v + hi), 4)
        pts.append(p)
    pts.sort(key=lambda p: p["x"])
    return {"id": rid, "source": source, "run": run, "kind": "observation", "relation": relation, "epoch": dict(EPOCH), "axes": axes,
            "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "uncertainty", "connect": False, "points": pts}, "scatter": None,
            "selection": {"population": population, "warning": warning}, "definitions": defs,
            "provenance": {"tier": "published-table", "citation": cite, "doi": doi, "url": url, "retrieved": "2026-10-18", "figure": table, "sourceMember": citation_member,
                           "sourceArchiveSha256": sha, "extractionMethod": "values parsed from the LaTeX table(s); M500 computed from tabulated R500 and z with the paper's definition (footnote of Sect. Scaling in Pratt+09)"},
            "calibration": "validation", "rankable": True,
            "notes": f"One point per cluster (31). Transcription cross-checked: M500 from R500 agrees with the M500-Y_X relation used by the papers (mean {MY_CHECK[0]:+.4f}, max {MY_CHECK[1]:.4f} dex); the relation refit from these points reproduces the published fit (see fit records)."}


DEF_COMMON = {"haloMassDefinition": "M500crit", "massMethod": "M500-Y_X relation (Arnaud+07), calibrated on hydrostatic masses of relaxed clusters; computed from R500 iterated with it", "cosmology": COSMO,
              "sampleSelection": SEL_REX, "population": "all"}
recs = []
LB = {"bol-L1": ("bolometric [0.01-100] keV", "with core (R < R500)", "L1", "R < R500", t1, "L1"), "bol-L2": ("bolometric [0.01-100] keV", "core-excised ([0.15-1] R500)", "L2", "0.15-1 R500", t1, "L2"),
      "soft-L1": ("[0.1-2.4] keV (ROSAT band)", "with core (R < R500)", "L[0.1-2.4]_1", "R < R500", t2, "L1"), "soft-L2": ("[0.1-2.4] keV (ROSAT band)", "core-excised ([0.15-1] R500)", "L[0.1-2.4]_2", "0.15-1 R500", t2, "L2")}
for key, (band, core, lname, ap, tab, col) in LB.items():
    vals = [(c[col][0] * 1e44, c[col][1] * 1e44, c[col][2] * 1e44) for c in tab]
    tabname = "table:tab1 (Cluster properties; bolometric [0.01-100] keV)" if key.startswith("bol") else "table:tabappx (Cluster properties in the soft X-ray band suitable for surveys)"
    recs.append(pts_record(
        rid=f"pratt09.rexcess.lxm.{key}.points", source="Pratt et al. 2009 (REXCESS)", run=f"{key}: {band}, {core}", relation="lxm", cite=CITE_P, doi="10.1051/0004-6361/200810994", url=URL_P, sha=SHA_P, table=tabname,
        axes={"xDefinition": XDEF, "xUnit": "log10(Msun)", "yDefinition": f"log10 X-ray luminosity {lname} in the {band} band within {ap}; rest frame, not E(z)-scaled", "yUnit": "log10(erg s^-1)"},
        y_values=vals, defs={**DEF_COMMON, "xrayBand": band, "coreTreatment": "with core" if "with" in core else "core-excised", "luminosityAperture": f"{ap} (R500 = radius of density contrast 500)", "luminosityScaling": "none (physical luminosity)"},
        warning=f"Per-cluster {lname} [{band}, {ap}] of the 31 REXCESS clusters in units of 10^44 erg/s from the paper's table (all quantities computed for Omega_M=0.3, Omega_Lambda=0.7, h0=0.7); error bars are the table's statistical errors; "
                "the paper states the uncertainties are negligible compared with the intrinsic scatter. M500 is not tabulated and is computed from R500 and z. Luminosities are raw (no Malmquist-bias correction). "
                "In the table column definitions: L1 is interior to R500 (with core), L2 is in the [0.15-1] R500 aperture (core excised).",
        population="31 REXCESS clusters", citation_member="0944.tex"))
# Y_sph(R500) points (Arnaud+10 table; physical values in 1e-5 Mpc^2)
vals = [(a["Y500"][0] * 1e-5, a["Y500"][1] * 1e-5, a["Y500"][2] * 1e-5) for a in ta]
recs.append(pts_record(
    rid="arnaud10.rexcess.ysz.ysph500.points", source="Arnaud et al. 2010 (REXCESS)", run="Y_sph(R500), 31 REXCESS clusters", relation="ysz", cite=CITE_A, doi="10.1051/0004-6361/200913416", url=URL_A, sha=SHA_A,
    table="table:pnfw (Cluster physical parameters; column Y_sph(R500))",
    axes={"xDefinition": XDEF, "xUnit": "log10(Msun)", "yDefinition": "log10 spherically integrated Compton parameter Y_sph(R500) = (sigma_T/m_e c^2) int_0^R500 4 pi P(r) r^2 dr, physical (not E(z)-scaled)", "yUnit": "log10(Mpc^2)"},
    y_values=vals, defs={**DEF_COMMON, "szScaling": "none (physical Y_sph); the paper's relation uses h(z)^(-2/3) Y_sph", "szAperture": "spherical, R500", "szDefinition": "Y_sph (spherical), not Y_SZ D_A^2 (cylindrical)", "pressureProfile": "measured REXCESS pressure profiles (deprojected X-ray electron density times spectroscopic temperature)"},
    warning="Y_sph(R500) per cluster from the REXCESS pressure profiles (31 rows, including RXC J2157.4-0747 that the paper calls bimodal and excludes from the profile analysis) in units of 10^-5 Mpc^2; error bars are the table's 1-sigma errors. "
            "Y_sph is the SPHERICAL integral (proportional to the gas thermal energy), not the cylindrical Y_SZ D_A^2. R500 and M500 are from the M500-Y_X relation (hydrostatic-calibrated relaxed clusters), so M500 and Y are not independent of Y_X. M500 is computed from R500 and z.",
    population="31 REXCESS clusters", citation_member="prexcess_sub.tex"))

# parametric fits
LOGM0_L = math.log10(2e14)
LOGM0_Y = math.log10(3e14)
xlo, xhi = math.floor(min(np.log10(M_P)) * 100) / 100, math.ceil(max(np.log10(M_P)) * 100) / 100


def fit_record(rid, source, run, relation, cite, doi, url, sha, axes, equation, expression, params, defs, warning, note, tier="published-fit"):
    return {"id": rid, "source": source, "run": run, "kind": "observation", "relation": relation,
            "epoch": {"zRepresentative": round(ZREP, 4), "zNominal": round(ZREP, 4), "zMin": ZMIN, "zMax": ZMAX, "mode": "analytic-evolution", "snapshot": None},
            "axes": axes, "domain": {"xMin": xlo, "xMax": xhi},
            "representation": {"type": "parametric", "equation": equation, "expression": expression, "parameters": params, "ageCosmology": COSMO}, "scatter": None,
            "selection": {"population": "REXCESS clusters", "warning": warning}, "definitions": defs,
            "provenance": {"tier": tier, "citation": cite, "doi": doi, "url": url, "retrieved": "2026-10-18", "sourceArchiveSha256": sha},
            "calibration": "validation", "rankable": True, "notes": note}


for key, (band, core, lname, ap, tab, col) in LB.items():
    tabname = "lxrel (bolometric)" if key.startswith("bol") else "lxrelsoft ([0.1-2.4] keV)"
    for meth, (C, a) in zip(("BCES (Y|X)", "BCES orthogonal"), PUB[key]):
        if key == "soft-L2":
            pass
        tag = "bcesyx" if meth.startswith("BCES (") else "bcesorth"
        rf = REFIT[key]["ols" if tag == "bcesyx" else "orth"]
        recs.append(fit_record(
            rid=f"pratt09.rexcess.lxm.{key}.{tag}", source="Pratt et al. 2009 (REXCESS fit)", run=f"{key}: {band}, {core}, {meth}", relation="lxm", cite=CITE_P, doi="10.1051/0004-6361/200810994", url=URL_P, sha=SHA_P,
            axes={"xDefinition": XDEF, "xUnit": "log10(Msun)", "yDefinition": f"log10 X-ray luminosity {lname} ({band}, {ap}); the published h(z)^(-7/3) scaling is re-applied at the epoch, so this is the physical luminosity", "yUnit": "log10(erg s^-1)"},
            equation=f"h(z)^(-7/3) L = C (M500 / 2e14 Msun)^alpha, C = {C} x 10^44 erg/s, alpha = {a}  [{meth}; Pratt+09 table {tabname}]",
            expression="(7/6)*log10(0.3*(1+z)**3+0.7)+logC+alpha*(x-logM0)", params={"logC": round(math.log10(C * 1e44), 5), "alpha": a, "logM0": round(LOGM0_L, 5)},
            defs={**DEF_COMMON, "xrayBand": band, "coreTreatment": "with core" if "with" in core else "core-excised", "luminosityAperture": f"{ap}", "luminosityScaling": "h(z)^-7/3 = E(z)^-7/3 applied in the fit (E^2 = 0.3 (1+z)^3 + 0.7)", "fitMethod": meth,
                  "malmquistBiasCorrection": "none (raw relation of the REXCESS sample)", "massDefinition": "M500 from the M500-Y_X relation (M_Y)"},
            warning=f"Published power-law fit of the raw REXCESS {lname}-M_Y relation ({band}, {core}); fit method {meth}. Malmquist-bias-corrected rows of the same table are not stored. M is M_Y, the M500 derived from Y_X with the relation of Arnaud+07, so L-M is a Y_X-mass relation. "
                    "Intrinsic scatter is not given for L-M because M is derived from Y_X (table footnote a).",
            note=f"Verified: refitting the 31 table values (M500 computed from R500, z) with {'ordinary least squares in log-log' if tag == 'bcesyx' else 'orthogonal regression'} gives alpha = {rf[0]:.3f}, C = {rf[1]:.3f} x 10^44 erg/s against the paper's {a}, {C} (negligible measurement errors, so BCES reduces to these)."))
        if key == "soft-L2":
            recs[-1]["selection"]["warning"] += " The row is printed in the paper as 'L[0.1-2.4]_1-M_Y' but sits in the 0.15<R<R500 block of the survey-band table (a typo); it is read as L[0.1-2.4]_2 and the refit of the L_2 values reproduces it."

# Y-M fits (Arnaud+10)
YAX = {"xDefinition": XDEF, "xUnit": "log10(Msun)", "yUnit": "log10(Mpc^2)"}
recs.append(fit_record(
    rid="arnaud10.rexcess.ysz.ysph500.fit", source="Arnaud et al. 2010 (REXCESS fit)", run="Y_sph(R500)-M500, fit to the REXCESS data", relation="ysz", cite=CITE_A, doi="10.1051/0004-6361/200913416", url=URL_A, sha=SHA_A,
    axes={**YAX, "yDefinition": "log10 spherically integrated Compton parameter Y_sph(R500); the published h(z)^(-2/3) scaling is re-applied at the epoch, so this is the physical Y_sph"},
    equation="h(z)^(-2/3) Y_sph(R500) = 10^-4.739 [M500 / (3e14 h70^-1 Msun)]^1.790 h70^-5/2 Mpc^2  (Arnaud+10 eq. mysz500)",
    expression="(1/3)*log10(0.3*(1+z)**3+0.7)+logA+alpha*(x-logM0)", params={"logA": -4.739, "alpha": 1.79, "logM0": round(LOGM0_Y, 5)},
    defs={**DEF_COMMON, "szScaling": "h(z)^(-2/3) = E(z)^(-2/3) applied in the fit (E^2 = 0.3 (1+z)^3 + 0.7)", "szAperture": "spherical, R500", "szDefinition": "Y_sph (spherical)", "h70": "H0 = 70, so h70 = 1 and units are Msun and Mpc^2"},
    warning="Published power-law fit to the REXCESS Y_sph(R500) - M500 data. Y_sph is the spherical integral inside R500, not Y_SZ D_A^2. M500 comes from the M500-Y_X relation, so the relation 'does not contain more information than the Y_sph-Y_X relation' (paper). The paper's units carry h70 factors (h70 = 1 here).",
    note=f"Verified: refitting the 31 table values (M500 from R500 and z, Y_sph(R500) / E(z)^(2/3)) with orthogonal regression gives slope {YREFIT[0]:.3f} and log A = {YREFIT[1]:.3f} (OLS: {YREFIT[2][0]:.3f}, {YREFIT[2][1]:.3f}), against the paper's 1.790 +/- 0.015 and -4.739 +/- 0.003."))
for tag, logn, aper, quote in (("ycyl500", -4.665, "cylindrical, R500 aperture (Y_SZ D_A^2 within R500)", "log(B_{\\rm x})=-4.665"), ("ytot", -4.491, "total signal, cylindrical aperture 5 R500 (equivalently Y_sph(5 R500))", "log(A_{\\rm x})=-4.491")):
    recs.append(fit_record(
        rid=f"arnaud10.rexcess.ysz.{tag}.universal", source="Arnaud et al. 2010 (universal profile)", run=f"Y_SZ D_A^2-M500, universal GNFW pressure profile, {aper}", relation="ysz", cite=CITE_A, doi="10.1051/0004-6361/200913416", url=URL_A, sha=SHA_A,
        axes={**YAX, "yDefinition": f"log10 Y_SZ D_A^2, {aper}; the published h(z)^(-2/3) scaling is re-applied at the epoch, so this is the physical value"},
        equation=f"h(z)^(-2/3) Y_SZ D_A^2 = B (M500 / (3e14 h70^-1 Msun))^1.78 h70^-1 Mpc^2, log10 B = {logn} (2.925e-5 x {'J(1) = 0.7398' if tag == 'ycyl500' else 'I(5) = 1.1037'})  (Arnaud+10 eqs. mysz, Jx)",
        expression="(1/3)*log10(0.3*(1+z)**3+0.7)+logB+alpha*(x-logM0)", params={"logB": logn, "alpha": 1.78, "logM0": round(LOGM0_Y, 5)},
        defs={**DEF_COMMON, "szScaling": "h(z)^(-2/3) = E(z)^(-2/3) applied in the fit", "szAperture": aper, "szDefinition": "Y_SZ D_A^2 (cylindrical) derived from the universal pressure profile with the slope fixed at 1.78", "h70": "H0 = 70, so h70 = 1"},
        warning="Model relation built by the authors from the universal GNFW pressure profile (REXCESS data plus simulations at large radii) with the mass scaling slope fixed to 1.78 from the M500-Y_X relation; extent R_b = 5 R500 assumed for the cylindrical integral. "
                "The paper estimates an uncertainty of +/-0.06 on the slope and +/-0.024 dex on the normalisation. Not a direct measurement of Y_SZ.",
        note=f"Verified: the normalisation reproduces the quoted number log B = {logn} from 2.925e-5 x {'0.7398' if tag == 'ycyl500' else '1.1037'} to 4 digits (quoted constants of the paper: eq. y500, J(1), I(5))."))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=1) + "\n")
print(f"wrote {len(recs)} records; x domain {xlo}-{xhi}; z {ZMIN}-{ZMAX} (median {ZREP:.4f})")
print("M500(R500) vs M-YX relation: mean/max dex", MY_CHECK, "Pratt vs Arnaud R500-derived mass max dex", round(DEV2, 4))
print("L-M refits (ols slope, C | orth slope, C):", {k: (tuple(round(v, 3) for v in r['ols']), tuple(round(v, 3) for v in r['orth'])) for k, r in REFIT.items()})
print("Y-M refit orth slope, logA, OLS:", [round(v, 3) if not isinstance(v, tuple) else tuple(round(w, 3) for w in v) for v in YREFIT])
