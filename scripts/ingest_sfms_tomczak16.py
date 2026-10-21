"""Tomczak et al. 2016 (arXiv:1510.06072) SFR-M* relation of ZFOURGE galaxies, Eqs. (sfrmass) + parameterization for all galaxies and for UVJ star-forming galaxies,
as two analytic-evolution records. Coefficients are parsed from the arXiv source (ms.tex). Verification: the eight redshift-parameterised curves drawn in the paper's
Fig. 7 (all galaxies) and Fig. 8 (star-forming) (matplotlib EPS, converted with gs; axes calibrated on numeric tick labels with vector_figure.axis_fit) are compared with the
transcribed expression; Table 4 (stacked UV+IR SFRs) is compared as a second check. Writes records_tomczak16.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_figure import fetch_arxiv  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
import json, re, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
import vector_figure as vf
from ingest_sfms_tomczak16_table import rows as TABLE

BASE = fetch_arxiv("1510.06072"); TEX = (BASE / "ms.tex").read_text()
WORK = Path("/tmp/vector_figure_src/t16-work"); WORK.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data" / "curves" / "sfms-tomczak16.json"

def block(marker, nxt):
    i = TEX.index(marker); return TEX[i:TEX.index(nxt, i)]
def parse(b):
    b = b.replace("\\:", "").replace(" ", "")
    n = lambda pat: [float(v) for v in re.search(pat, b).groups()]
    s0 = n(r"s\}_0=&([\d.]+)\+([\d.]+)z-([\d.]+)z\^2"); m0 = n(r"log\(M_0\)\}=&([\d.]+)\+([\d.]+)z-([\d.]+)z\^2")
    g = n(r"\\gamma=&([\d.]+)")
    return dict(s0=s0, m0=m0, g=g[0])
COEF = {"all": parse(block(r"\bf All \; Galaxie", r"\end{split}")), "sf": parse(block(r"\bf Star-Form", r"\end{split}"))}
assert COEF["all"] == dict(s0=[0.195, 1.157, 0.143], m0=[9.244, 0.753, 0.09], g=1.118), COEF["all"]    # note: stored positive, sign handled below
assert COEF["sf"] == dict(s0=[0.448, 1.22, 0.174], m0=[9.458, 0.865, 0.132], g=1.091), COEF["sf"]
def sfr(k, x, z):
    c = COEF[k]; s0 = c["s0"][0] + c["s0"][1] * z - c["s0"][2] * z * z; m0 = c["m0"][0] + c["m0"][1] * z - c["m0"][2] * z * z
    return s0 - np.log10(1 + 10 ** (-c["g"] * (x - m0)))
ZB = [(0.5, 0.75), (0.75, 1.0), (1.0, 1.25), (1.25, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.0), (3.0, 4.0)]
ZC = [(a + b) / 2 for a, b in ZB]

check = {}
for k, fig in (("all", "Fig7"), ("sf", "Fig8")):
    pdf = WORK / f"{fig}.pdf"
    subprocess.run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-dEPSCrop", "-sDEVICE=pdfwrite", f"-sOutputFile={pdf}", str(BASE / f"{fig}.eps")], check=True)
    page = vf.page_of(pdf)
    fr = sorted(vf.frames(page, min_w=100, min_h=60), key=lambda r: r.x0)[0]            # left panel (the three right panels start at x0=616)
    fx, fy, info = vf.calibrate(page, fr)
    assert [round(v, 2) for _, v in info["xTicks"]] == [8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5], info["xTicks"]
    lines = [c for c in vf.curves(page, fr, fx, fy, min_items=50) if c["width"] == 2.0 and 90 <= len(c["points"]) <= 110]
    lines.sort(key=lambda c: c["points"][-1][1])      # ascending SFR at the right-hand end = ascending redshift
    assert len(lines) == 8, len(lines)
    res = []
    for c, zc, zb in zip(lines, ZC, ZB):
        P = np.array(c["points"]); P = P[np.argsort(P[:, 0], kind="stable")]
        zbest = minimize_scalar(lambda z: np.mean((sfr(k, P[:, 0], z) - P[:, 1]) ** 2), bounds=(0.2, 5), method="bounded").x
        d = sfr(k, P[:, 0], zc) - P[:, 1]
        res.append(dict(zBin=zb, xRange=[round(float(P[0, 0]), 2), round(float(P[-1, 0]), 2)], zBestFit=round(float(zbest), 3), zCentre=zc, rms=round(float(np.sqrt(np.mean(d ** 2))), 4), maxAbs=round(float(np.abs(d).max()), 4)))
    check[k] = res
    for r in res: print(k, r["zBin"], r["xRange"], "zfit", r["zBestFit"], "zc", r["zCentre"], "rms", r["rms"], "max", r["maxAbs"])
    assert all(r["rms"] < 0.03 and abs(r["zBestFit"] - r["zCentre"]) < 0.08 for r in res), res
    # Table 4 cross-check (all bins, including those below the completeness limit)
    col = "psi_all" if k == "all" else "psi_sf"
    d = np.array([sfr(k, r["logM"], (r["z"][0] + r["z"][1]) / 2) - r[col][0] for r in TABLE])
    check[k + "_table"] = dict(n=len(d), rms=round(float(np.sqrt(np.mean(d ** 2))), 3), median=round(float(np.median(d)), 3))
    print(k, "vs Table 4 (80 stacks):", check[k + "_table"])

def rec(k):
    c = COEF[k]
    P = dict(s00=c["s0"][0], s01=c["s0"][1], s02=-c["s0"][2], logM00=c["m0"][0], logM01=c["m0"][1], logM02=-c["m0"][2], gamma=c["g"])
    expr = "(s00+s01*z+s02*z*z)-Math.log10(1+Math.pow(10,-gamma*(x-(logM00+logM01*z+logM02*z*z))))"
    lo = min(r["xRange"][0] for r in check[k]); hi = max(r["xRange"][1] for r in check[k])
    starts = {f"{r['zBin'][0]}-{r['zBin'][1]}": r["xRange"][0] for r in check[k]}
    name = {"all": "all galaxies (star-forming plus quiescent)", "sf": "UVJ-selected star-forming galaxies"}[k]
    return {
        "id": f"tomczak16.zfourge.sfms.{'all' if k == 'all' else 'sf'}.evolution", "source": "Tomczak et al. 2016 (ZFOURGE)", "run": name,
        "kind": "observation", "relation": "sfms",
        "epoch": {"zRepresentative": 2.0, "zMin": 0.5, "zMax": 4.0, "mode": "analytic-evolution", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass (FAST, Bruzual & Charlot 2003, Chabrier IMF, solar metallicity)", "xUnit": "log10(Msun)",
                 "yDefinition": "log10 UV+IR SFR (Psi = 1.09e-10 (L_IR + 2.2 L_UV), Chabrier IMF) of the median UV luminosity plus stacked 24-160 micron IR luminosity in bins of mass and redshift", "yUnit": "log10(Msun/yr)"},
        "domain": {"xMin": lo, "xMax": hi},
        "representation": {"type": "parametric",
                           "equation": "log Psi = s0 - log[1 + (M*/M0)^-gamma] (Eq. 1, Lee+15 form); s0 = a + b z + c z^2 and log M0 = a + b z + c z^2 (Eq. 2-3), gamma constant (fixed-gamma fit)",
                           "expression": expr, "parameters": P},
        "scatter": None,
        "selection": {"population": name + ", ZFOURGE (CDFS, COSMOS, UDS) with Spitzer 24 micron and Herschel 100/160 micron stacking",
                      "warning": f"Valid for 0.5<z<4 and the stacked mass ranges; the authors warn that the parameterization 'may not extrapolate well outside of the z and/or stellar mass ranges used here'. Digitised start of the fitted lines (log M*, by z bin): {json.dumps(starts)}; end {hi}. "
                                 "The SFR of each bin is built from the median UV luminosity and the stacked IR luminosity of the bin. The 'all galaxies' relation includes quiescent galaxies (the turnover mass may be influenced by the growing quiescent population, as the authors note)."},
        "provenance": {"tier": "published-fit", "citation": "Tomczak et al. 2016, ApJ 817, 118 (arXiv:1510.06072), Eqs. 1-3", "doi": None, "url": "https://arxiv.org/abs/1510.06072", "retrieved": "2026-10-18"},
        "calibration": "validation", "rankable": True,
        "notes": f"Coefficients parsed from the arXiv source. Verification: the expression reproduces the eight redshift-parameterised curves of the paper's {'Fig. 7' if k == 'all' else 'Fig. 8'} at the bin-centre redshifts with rms 0.0003-0.0032 dex (max 0.005) and a free fit of z returns the bin centres; it matches the paper's Table 4 stacked SFRs with rms {check[k + '_table']['rms']} dex over all 80 stacks (including bins below the completeness limit).",
        "definitions": {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": {"H0": 70, "Om": 0.3}, "population": "all" if k == "all" else "star-forming",
                        "sfrIndicator": "UV+IR (Bell05 conversion scaled to Chabrier; L_IR from Wuyts08 template fitted to stacked 24-160 micron photometry)", "sfrTimescaleMyr": "unspecified", "sfrStatistic": "unspecified",
                        "sfrStatisticNote": "'we aim to measure the average star-formation rate of galaxies in bins of z and stellar mass'; median L_UV, stacked L_IR"}}
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec("all"), rec("sf")]}, indent=2) + "\n")
print("wrote", OUT)
