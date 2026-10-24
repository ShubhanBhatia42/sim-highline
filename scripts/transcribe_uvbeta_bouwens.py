"""UV-continuum slope beta against absolute UV magnitude, observations: the biweight-mean beta in bins of M_UV tabulated by Bouwens et al. 2012 (ApJ 754, 83; arXiv:1109.0994, Table 'uvslope', z ~ 4 to 7)
and by Bouwens et al. 2014 (ApJ 793, 115; arXiv:1306.2950, Table 'medianbeta', z ~ 4 to 8). Values are parsed from the LaTeX tables in the arXiv source and asserted against the printed numbers below.
beta is the slope of f_lambda ~ lambda^beta fitted to the broad-band fluxes of the filters that sit redward of Lyman-alpha, so the observed light (dust attenuated) is what is measured.
Usage: python3 scripts/transcribe_uvbeta_bouwens.py   (writes data/curves/uvbeta-bouwens12-14.json)"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "uvbeta-bouwens12-14.json"
AX = {"xDefinition": "absolute UV magnitude M_UV (rest-frame UV, AB; the geometric mean of the luminosities in the bands used to derive beta for Bouwens+12, the rest-frame UV luminosity for Bouwens+14)", "xUnit": "mag (AB)",
      "yDefinition": "UV-continuum slope beta, f_lambda ~ lambda^beta (biweight mean of the individual galaxies in the M_UV bin)", "yUnit": "dimensionless"}
COSMO = {"H0": 70.0, "Om": 0.3}
records = []


def num(t):
    t = t.replace("$-$", "-").replace("$", "").replace("\\phantom{-}", "")
    return float(t)


def parse_blocks(tex, start_marker, end_marker, header_re, ncol):
    """rows 'M & beta+-rand+-syst & ...' under each redshift header; returns {z_label: [(M, beta, rand, syst, rest columns)]}"""
    t = tex[tex.index(start_marker):]
    t = t[t.index("\\startdata") + 10:t.index(end_marker)]
    out, cur = {}, None
    for line in t.split("\\\\"):
        line = line.replace("\n", " ").strip()
        h = re.search(header_re, line)
        if h:
            cur = h.group(1)
            out[cur] = []
            continue
        c = [x.strip() for x in line.split("&")]
        if cur and len(c) >= 2 and re.match(r"^\$-\$\d+\.\d+$", c[0]):
            m = re.match(r"^(\$-\$\d+\.\d+)\$\\pm\$(\d+\.\d+)\$\\pm\$(\d+\.\d+)", c[1])
            assert m, (cur, c[:2])
            out[cur].append((num(c[0]), num(m.group(1)), float(m.group(2)), float(m.group(3)), c[2:]))
    return out


def make(rid, source, z, zlabel, rows, window, doi, cite, arxiv, member, sha, figure, extra_note, aperture):
    pts = [{"x": M, "y": b, "yLow": round(b - e, 3), "yHigh": round(b + e, 3)} for M, b, e, s in rows]
    assert all(a["x"] < c["x"] for a, c in zip(pts, pts[1:])) or all(a["x"] > c["x"] for a, c in zip(pts, pts[1:]))
    pts.sort(key=lambda p: p["x"])
    syst = sorted({s for _, _, _, s in rows})
    assert len(syst) == 1, syst
    return {"id": rid, "source": source, "run": source, "kind": "observation", "relation": "uvbeta",
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "observational-bin", "snapshot": None},
            "axes": AX, "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "uncertainty", "connect": False, "points": pts}, "scatter": None,
            "selection": {"population": f"Lyman-break galaxies at {zlabel} (HST ACS+WFC3/IR, HUDF/XDF, ERS, CANDELS)",
                          "warning": f"Biweight-mean beta of the galaxies in each M_UV bin, from the table of the paper; the plotted band is the random error (1 sigma) and the paper adds a systematic error of {syst[0]:.2f} not drawn. {extra_note}"},
            "definitions": {"betaWindow": window, "dustTreatment": "attenuated", "dustModel": "observed light: dust attenuation is whatever the galaxies have", "betaMethod": "power-law fit f_lambda ~ lambda^beta to broad-band fluxes",
                            "xVariable": "M_UV", "cosmology": COSMO, "population": "Lyman-break dropout samples", "aperture": aperture},
            "provenance": {"tier": "published-table", "citation": cite, "doi": doi, "url": f"https://arxiv.org/abs/{arxiv}", "retrieved": "2026-10-23", "figure": figure, "checksumSha256": sha, "sourceMember": member,
                           "extractionMethod": "transcribed from the arXiv LaTeX source of the paper's table and parsed by script; values asserted against the printed numbers in the script"},
            "calibration": "target", "rankable": True, "notes": "Observational constraint; the paper's own definitions are in the definitions block."}


# ------------------------------------------------------------------ Bouwens et al. 2014
ARX = "1306.2950"
src = vf.fetch_arxiv(ARX) / "ms.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
for q in ("we fit the observed $J_{125}$-band and\n$H_{160}$-band fluxes to a power law $f_{\\lambda} \\propto\n\\lambda^{\\beta}$ to determine $\\beta$",
          "using the same power-law fits ($f_{\\lambda} \\propto\n\\lambda^{\\beta}$) used for our $z\\sim7$ samples",
          "$\\Omega_0 = 0.3$, $\\Omega_{\\Lambda} = 0.7$, $H_0 =\n70\\,\\textrm{km/s/Mpc}$",
          "The biweight mean is our preferred method for quoting",
          "All the photometry used for the $\\beta$ determinations are\nPSF-matched to the $H_{160}$ band",
          "Our primary method for deriving $UV$-continuum slopes for $z\\sim8$\ngalaxies is based on a power-law fit to the $JH_{140}$ and $H_{160}$\nband fluxes",
          "though we note that\nthey are quite uncertain and do not provide a useful constraint",
          "the error we derive on the biweight\nmean/median from bootstrap resampling is clearly too low"):
    assert " ".join(q.split()) in " ".join(tex.split()), ("quoted sentence missing", q)
B14 = parse_blocks(tex, "The biweight mean, median, and inverse-variance-weighted mean", "\\enddata", r"\\textbf\{z\$\\,\\sim\\,\$(\d+\.?\d*)", 5)
assert list(B14) == ["4", "5", "6", "7", "8", "8.5"] and [len(B14[k]) for k in B14] == [13, 11, 10, 4, 2, 1], {k: len(v) for k, v in B14.items()}
# the printed numbers (read from the typeset table): first and last bin of z~4, z~5, z~6 and the z~7 and z~8 rows
assert B14["4"][0][:4] == (-21.75, -1.54, 0.07, 0.06) and B14["4"][-1][:4] == (-15.75, -2.15, 0.12, 0.06)
assert B14["5"][0][:4] == (-21.75, -1.36, 0.48, 0.06) and B14["5"][-1][:4] == (-16.5, -2.16, 0.17, 0.06)
assert B14["6"][0][:4] == (-21.75, -1.55, 0.17, 0.08) and B14["6"][-1][:4] == (-17.0, -2.24, 0.2, 0.08)
assert B14["7"][0][:4] == (-21.25, -1.75, 0.18, 0.13) and B14["7"][-1][:4] == (-17.35, -2.42, 0.28, 0.13) and B14["8"][1][:4] == (-18.65, -1.41, 0.6, 0.27)
# consistency with the paper's own fitted line (table 'slopes': beta = -1.85 at M_UV = -19.5 for z ~ 3.8): the two z~4 bins either side of -19.5 average to it within 0.02
b4 = {M: b for M, b, e, s, _ in B14["4"]}
assert abs((b4[-19.75] + b4[-19.25]) / 2 - (-1.85)) < 0.02 and "$B_{435}$ & 3.8 & $-1.85\\pm0.01\\pm0.06$ & $-0.11\\pm0.01$" in tex
WIN14 = {"4": "power-law fit to PSF-matched broad-band fluxes: i775 I814 z850 Y105 J125 (the deepest fields: i775 I814 z850 J125)",
         "5": "power-law fit to PSF-matched broad-band fluxes: z850 Y105 J125 H160 (the deepest fields: z850 Y105 H160)",
         "6": "power-law fit to PSF-matched broad-band fluxes: Y105 J125 H160 (the deepest fields: Y105 H160)",
         "7": "power-law fit to broad-band fluxes: J125 and H160 (J125 JH140 H160 over the HUDF)",
         "8": "power-law fit to the JH140 and H160 band fluxes (the paper's primary method at z ~ 8)"}
ZMEAN14 = {"4": 3.8, "5": 5.0, "6": 5.9, "7": 7.0, "8": 8.0}   # mean redshifts of the samples, printed in the paper's table 'slopes'
assert "$z_{850}$ & 7.0 &" in tex and "$Y_{105}$ & 8.0 &" in tex and "$V_{606}$ & 5.0 &" in tex and "$i_{775}$ & 5.9 &" in tex
for z in ("4", "5", "6", "7", "8"):
    note = {"4": "z ~ 4 here is the mean redshift 3.8 of the dropout sample.", "8": "Two bins only (2 and 4 galaxies); the paper says the z ~ 8 results are 'quite uncertain and do not provide a useful constraint' and that the error of the first bin (+-0.01) is clearly too low because the two galaxies have the same beta. The single z ~ 8.5 bin (M_UV = -18.5, beta = -2.06) is not stored as a curve.",
            "7": "The bins are 1.3 mag wide.", "5": "z ~ 5.", "6": "z ~ 6."}[z]
    records.append(make(f"bouwens14.uvbeta.z{z}", "Bouwens et al. 2014", ZMEAN14[z], f"z ~ {z}", [(M, b, e, s) for M, b, e, s, _ in B14[z]], WIN14[z], "10.1088/0004-637X/793/2/115",
                        f"Bouwens et al. 2014, ApJ 793, 115 (arXiv:{ARX}), table of the biweight mean, median and inverse-variance-weighted mean beta as a function of M_UV", ARX, "ms.tex", sha, "Table: biweight mean beta versus M_UV (z ~ 4 to 8)", note,
                        "photometry PSF-matched to the H160 band (the paper: 'All the photometry used for the beta determinations are PSF-matched to the H160 band')"))

# ------------------------------------------------------------------ Bouwens et al. 2012
ARX = "1109.0994"
src = vf.fetch_arxiv(ARX) / "nbeta.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
assert "$\\Omega_0 = 0.3$, $\\Omega_{\\Lambda} = 0.7$, $H_0 =" in tex and "PSF-matched to the WFC3/IR $H_{160}$-band, using typical Kron-style" in tex.replace("\n", " ").replace("  ", " ")
B12 = parse_blocks(tex, "The biweight mean $UV$-continuum slope $\\beta$ and $1\\sigma$", "\\enddata", r"^\\multicolumn\{3\}\{c\}\{\$z\\sim(\d+)\$\}", 3)
assert list(B12) == ["4", "5", "6", "7"] and [len(B12[k]) for k in B12] == [6, 5, 5, 4], {k: len(v) for k, v in B12.items()}
assert B12["4"][0][:4] == (-21.5, -1.74, 0.04, 0.1) and B12["4"][-1][:4] == (-16.5, -2.2, 0.07, 0.1)
assert B12["5"][0][:4] == (-21.5, -1.63, 0.08, 0.1) and B12["5"][-1][:4] == (-17.5, -2.35, 0.11, 0.1)
assert B12["6"][0][:4] == (-21.5, -1.78, 0.11, 0.14) and B12["6"][-1][:4] == (-17.5, -2.54, 0.17, 0.14)
assert B12["7"][0][:4] == (-21.25, -1.89, 0.1, 0.28) and B12["7"][-1][:4] == (-18.25, -2.68, 0.19, 0.28)
# consistency with the paper's own fit (table 'bestfit': beta = -2.00 at M_UV = -19.5, slope -0.11 for z ~ 3.8): the table's z ~ 4 value at -19.5 is -2.01
assert dict((M, b) for M, b, e, s, _ in B12["4"])[-19.5] == -2.01 and "$B_{435}$ & 3.8 & $-$2.00$\\pm$0.02$\\pm$0.10 & $-$0.11$\\pm$0.01" in tex
assert "$z_{850}$ & 7.0 &" in tex and "$V_{606}$ & 5.0 &" in tex and "$i_{775}$ & 5.9 &" in tex
for q in ("$i_{775}z_{850}Y_{105}J_{125}$ & 2041\\AA", "$z_{850}Y_{105}J_{125}H_{160}$ & 1997\\AA", "$Y_{105}J_{125}H_{160}$ & 1846\\AA", "$J_{125}H_{160}$ & 1731\\AA"):
    assert q in tex, q
WIN12 = {"4": "power-law fit to broad-band fluxes: i775 z850 Y105 J125 (mean rest-frame wavelength 2041 A)", "5": "power-law fit to broad-band fluxes: z850 Y105 J125 H160 (mean rest-frame wavelength 1997 A)",
         "6": "power-law fit to broad-band fluxes: Y105 J125 H160 (mean rest-frame wavelength 1846 A)", "7": "power-law fit to broad-band fluxes: J125 H160 (mean rest-frame wavelength 1731 A)"}
for z, zm in (("4", 3.8), ("5", 5.0), ("6", 5.9), ("7", 7.0)):
    records.append(make(f"bouwens12.uvbeta.z{z}", "Bouwens et al. 2012", zm, f"z ~ {z}", [(M, b, e, s) for M, b, e, s, _ in B12[z]], WIN12[z], "10.1088/0004-637X/754/2/83",
                        f"Bouwens et al. 2012, ApJ 754, 83 (arXiv:{ARX}), table of the biweight mean UV-continuum slope as a function of UV luminosity", ARX, "nbeta.tex", sha, "Table: biweight mean beta and scatter versus M_UV",
                        "Corrected by the authors for selection effects and measurement errors; the 2014 paper of the same group revises these values.",
                        "photometry PSF-matched to the WFC3/IR H160 band, using typical Kron-style apertures (the paper's table note)"))

for rec in records:
    assert rec["representation"]["points"] and all(a["x"] < b["x"] for a, b in zip(rec["representation"]["points"], rec["representation"]["points"][1:])), rec["id"]
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} observational UV slope records")
