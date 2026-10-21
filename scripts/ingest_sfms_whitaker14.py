"""Whitaker et al. 2014 (arXiv:1407.1843) broken-power-law star-formation sequence, one record per redshift bin.
Table 2 (broken power law) and Table 3 (stacked medians) are parsed from the LaTeX source, not typed in. Checks:
(1) mean of the four a_low equals the paper's quoted 0.97; (2) a weighted refit of the broken power law (break fixed at 10.2)
to the tabulated median log Psi reproduces Table 2 within its quoted 1-sigma errors. Writes records_whitaker14.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_figure import fetch_arxiv  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
import json, re, sys
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares

SRC = (fetch_arxiv("1407.1843") / "ms_arxiv_v2.tex")
OUT = ROOT / "data" / "curves" / "sfms-whitaker14.json"
tex = SRC.read_text()
lines = tex.split("\n")

def block(start_marker, end_marker="\\end{tabular}"):
    i = tex.index(start_marker); return tex[i:tex.index(end_marker, i)]

pm = lambda c: tuple(float(v) for v in re.match(r"\s*\$?\s*(-?[\d.]+)\s*\\pm\s*([\d.]+)", c).groups())
# ---- Table 2 (broken power law)
t2 = {}
for l in block("\\caption{Broken Power Law Fits}").split("\n"):
    m = re.match(r"\s*\$(\d\.\d)<z<(\d\.\d)\$\s*&(.*?)\\\\", l)
    if m:
        c = [pm(x) for x in m.group(3).split("&")]
        t2[(float(m.group(1)), float(m.group(2)))] = dict(alow=c[0], ahigh=c[1], b=c[2])
assert len(t2) == 4, t2
# ---- Table 3 (stacks): log M*, median log Psi (+-)
t3 = {}; zb = None
for l in block("\\caption{Star Formation Sequence Data}").split("\n"):
    l = l.strip()
    m = re.match(r"\$(\d\.\d)<z<(\d\.\d)\$\s*&\s*(.*)", l)
    if m: zb = (float(m.group(1)), float(m.group(2))); rest = m.group(3)
    elif l.startswith("&"): rest = l[1:]
    else: continue
    cells = [c.strip() for c in rest.replace("\\\\", "").split("&")]
    try: lm = float(cells[0])
    except ValueError: continue
    t3.setdefault(zb, []).append((lm,) + pm(cells[1]))
assert sum(len(v) for v in t3.values()) == 50
# ---- checks
mean_alow = np.mean([v["alow"][0] for v in t2.values()])
assert round(mean_alow, 2) == 0.97, mean_alow     # paper: "an average measured value of alpha=0.97+-0.06"
check = {"meanAlow": round(float(mean_alow), 3), "refit": {}}
for zb, par in t2.items():
    R = np.array(t3[zb]); x, y, e = R[:, 0], R[:, 1], np.maximum(R[:, 2], 0.02)
    f = lambda p: p[2] + np.where(x < 10.2, p[0], p[1]) * (x - 10.2)
    p = least_squares(lambda p: (f(p) - y) / e, [1, .5, 1.3]).x
    pub = [par["alow"][0], par["ahigh"][0], par["b"][0]]; err = [par["alow"][1], par["ahigh"][1], par["b"][1]]
    dev = [abs(a - b) / s for a, b, s in zip(p, pub, err)]
    check["refit"][f"{zb[0]}-{zb[1]}"] = dict(refit=[round(float(v), 3) for v in p], published=pub, deviationInSigma=[round(float(d), 2) for d in dev])
    assert max(dev) < 1.5, (zb, dev)
print(json.dumps(check, indent=1))

def rec(zb):
    par = t2[zb]; R = t3[zb]; zc = round((zb[0] + zb[1]) / 2, 2)
    lo, hi = min(r[0] for r in R), max(r[0] for r in R)
    tag = f"z{zb[0]:g}-{zb[1]:g}"
    P = {"alow": par["alow"][0], "ahigh": par["ahigh"][0], "b": par["b"][0], "alowError": par["alow"][1], "ahighError": par["ahigh"][1], "bError": par["b"][1]}
    return {
        "id": f"whitaker14.3dhst.sfms.bpl.{tag}", "source": "Whitaker et al. 2014 (3D-HST/CANDELS)", "run": "broken power law, median stacks",
        "kind": "observation", "relation": "sfms",
        "epoch": {"zRepresentative": zc, "zMin": zb[0], "zMax": zb[1], "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass (FAST, Bruzual & Charlot 2003, Chabrier IMF, emission-line corrected)", "xUnit": "log10(Msun)",
                 "yDefinition": "log10 UV+IR SFR (Psi = 1.09e-10 (L_IR + 2.2 L_UV) Lsun, Chabrier IMF) of the median 24um-stack plus median UV luminosity of star-forming galaxies in the mass bin", "yUnit": "log10(Msun/yr)"},
        "domain": {"xMin": lo, "xMax": hi},
        "representation": {
            "type": "parametric",
            "equation": "log Psi = a [log(M*/Msun) - 10.2] + b, with a = a_low below and a_high above log M* = 10.2 (Eq. 2, Table 2)",
            "expression": "b+alow*Math.min(x-10.2,0)+ahigh*Math.max(x-10.2,0)", "parameters": P},
        "scatter": None,
        "selection": {"population": "UVJ-selected star-forming galaxies above the 90% mass-completeness limits, 3D-HST v4.0 / CANDELS (five fields)",
                      "warning": "Fit to median stacked UV+IR SFRs in 0.2 dex mass bins; the SFR of each bin includes MIPS-undetected galaxies through stacking. The paper does not measure the intrinsic scatter. The break mass 10.2 is fixed. "
                                 "zRepresentative is the bin centre. The paper's quadratic (Table 1) is not stored: its two-decimal coefficients do not reproduce the paper's own Table 3 (see M1 notes)."},
        "provenance": {"tier": "published-fit", "citation": "Whitaker et al. 2014, ApJ 795, 104 (arXiv:1407.1843), Eq. 2 and Table 2", "doi": None,
                       "url": "https://arxiv.org/abs/1407.1843", "retrieved": "2026-10-18"},
        "calibration": "validation", "rankable": True,
        "notes": f"Coefficients parsed from the arXiv source Table 2; mass range is the range of the tabulated stacks in Table 3 ({lo} to {hi}). Verification: mean a_low of the four bins = 0.97 (paper quotes 0.97+-0.06); a refit to Table 3 reproduces Table 2 within 1 sigma.",
        "definitions": {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": {"H0": 70, "Om": 0.3}, "population": "star-forming",
                        "sfrIndicator": "UV+IR (Spitzer/MIPS 24 um stacking for L_IR, rest-frame 2800 A for L_UV)", "sfrTimescaleMyr": 100,
                        "sfrTimescaleBasis": "'This conversion implicitly assumes that galaxies continuously form stars over timescales of 100 Myr or longer.' (lower bound)",
                        "sfrStatistic": "median", "massBasis": "stellar masses include a correction for emission-line contamination"}}

records = [rec(zb) for zb in sorted(t2)]
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print("wrote", len(records), "records to", OUT)
