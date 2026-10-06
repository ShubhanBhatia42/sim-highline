import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "uvlf-sfrd-obs.json"
UVBAND = "rest-frame UV (~1500-1600 A), AB"
SCH = "log10(0.4*Math.LN10*phi*Math.pow(10,-0.4*(x-Ms)*(alpha+1))*Math.exp(-Math.pow(10,-0.4*(x-Ms))))"
SCH_EQ = "Phi(M) = 0.4 ln10 phi* 10^(-0.4 (M-M*)(alpha+1)) exp(-10^(-0.4 (M-M*))) per mag"
AX_UV = {"xDefinition": "absolute UV magnitude M_UV (rest-frame UV, AB)", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"}
AX_SFRD = {"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic star-formation rate density", "yUnit": "log10(Msun yr^-1 cMpc^-3)"}
records = []


def clean(t):
    t = re.sub(r"\\phantom\{[^}]*\}", "", t)
    return t.replace("$", "").replace("\\!", "").strip()


def base(rid, source, relation, z, axes, rep, tier, cite, doi, arxiv, member, sha, definitions, population, warning, zrange=None, rankable=True, notes=""):
    zmin, zmax = zrange or (z, z)
    xs = [p["x"] for p in rep["points"]] if rep["type"] == "points" else None
    dom = {"xMin": xs[0], "xMax": xs[-1]} if xs else None
    return {"id": rid, "source": source, "run": source, "kind": "observation", "relation": relation,
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": zmin, "zMax": zmax, "mode": "observational-bin", "snapshot": None},
            "axes": axes, "domain": dom, "representation": rep, "scatter": None, "selection": {"population": population, "warning": warning}, "definitions": definitions,
            "provenance": {"tier": tier, "citation": cite, "doi": doi, "url": f"https://arxiv.org/abs/{arxiv}", "retrieved": vf.RETRIEVED, "figure": member[1], "checksumSha256": sha, "sourceMember": member[0],
                           "extractionMethod": "transcribed from the arXiv LaTeX source of the paper's table and parsed by script; values spot-checked against quoted numbers in the script"},
            "calibration": "target", "rankable": rankable, "notes": notes or "Observational constraint; the paper's own definitions are in the definitions block."}


def pts_record(rows):
    return {"type": "points", "intervalKind": "uncertainty", "connect": False, "points": rows}


def sch_record(phi, ms, alpha, xmin, xmax):
    return {"type": "parametric", "equation": SCH_EQ, "expression": SCH, "parameters": {"phi": phi, "Ms": ms, "alpha": alpha}}, {"xMin": xmin, "xMax": xmax}


# ---- Bouwens et al. 2021 (AJ 162, 47) ----
ARX = "2102.07775"
src = vf.fetch_arxiv(ARX) / "ms.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
DEF_B = {"uvBand": UVBAND, "uvBandNote": "M_1600,AB", "dustCorrection": "none (observed LF)", "cosmology": {"H0": 70.0, "Om": 0.3}, "densityFrame": "comoving", "population": "dropout-selected galaxies (HST legacy fields)"}
CITE_B = "Bouwens et al. 2021, AJ 162, 47 (arXiv:2102.07775)"
DOI_B = "10.3847/1538-3881/abf83e"
sch_tab = tex[tex.index("Determinations of the Schechter Parameters"):]
sch_tab = sch_tab[sch_tab.index("\\startdata") + 10:sch_tab.index("\\enddata")]
SCHP = {}
for line in sch_tab.split("\\\\"):
    c = [clean(x) for x in line.split("&")]
    if len(c) == 5 and re.match(r"^\d+\.\d+$", c[1]):
        z = float(c[1])
        ms = float(re.match(r"(-?\d+\.\d+)", c[2].replace("−", "-")).group(1))
        phi = float(re.match(r"(\d*\.?\d+)", c[3]).group(1)) * 1e-3
        al = float(re.match(r"(-?\d+\.\d+)", c[4]).group(1))
        SCHP[z] = (ms, phi, al)
assert set(SCHP) == {2.1, 2.9, 3.8, 4.9, 5.9, 6.8, 7.9, 8.9, 10.2}, SCHP
assert SCHP[5.9] == (-20.93, 0.51e-3, -1.93) and SCHP[6.8][0] == -21.15 and SCHP[2.1][2] == -1.52, "Schechter table spot check"
ZMAP = {2: 2.1, 3: 2.9, 4: 3.8, 5: 4.9, 6: 5.9, 7: 6.8, 8: 7.9, 9: 8.9, 10: 10.2}
sw = tex[tex.index("Stepwise Determination of the rest-frame"):]
sw = sw[sw.index("\\startdata") + 10:sw.index("\\enddata")]
groups = [None, None, None]
bins = {}
for line in sw.split("\\\\"):
    cells = [x.strip() for x in line.split("&")]
    ptr = 0
    pend = []
    for cell in cells:
        if "\\multicolumn" in cell:
            g = ptr // 2
            m = re.search(r"z\\sim\s*(\d+)\$?\s*galaxies", cell)
            groups[g] = int(m.group(1)) if m else None
            ptr += 2
            continue
        pend.append((ptr, cell))
        ptr += 1
    for k in range(0, len(pend) - 1):
        (p0, a), (p1, b) = pend[k], pend[k + 1]
        if p0 % 2 == 0 and p1 == p0 + 1 and a.strip() and b.strip():
            g = p0 // 2
            if groups[g] is None:
                continue
            M = float(clean(a).replace("−", "-").replace(" ", ""))
            bt = clean(b)
            if bt.startswith("<"):
                continue
            m = re.match(r"(\d+\.\d+)\\pm(\d+\.\d+)", bt.replace(" ", ""))
            if not m:
                continue
            bins.setdefault(groups[g], []).append((M, float(m.group(1)), float(m.group(2))))
assert sorted(bins) == [2, 3, 4, 5, 6, 7, 8, 9, 10], sorted(bins)
assert bins[6][0] == (-22.52, 2e-6, 2e-6) and len(bins[4]) == 12 and len(bins[2]) == 11 and bins[9][-1][0] == -17.92, "stepwise table spot check"
for zn, rows in sorted(bins.items()):
    zc = ZMAP[zn]
    rows = sorted(rows)
    pts = []
    for M, phi, err in rows:
        pt = {"x": round(M, 2), "y": round(math.log10(phi), 4)}
        if phi - err > 0:
            pt["yLow"] = round(math.log10(phi - err), 4)
        pt["yHigh"] = round(math.log10(phi + err), 4)
        pts.append(pt)
    ms, phi, al = SCHP[zc]
    for p in pts:
        sch = math.log10(0.4 * math.log(10) * phi * 10 ** (-0.4 * (p["x"] - ms) * (al + 1)) * math.exp(-10 ** (-0.4 * (p["x"] - ms))))
        if p["yHigh"] - p["y"] < 0.2:
            assert abs(sch - p["y"]) < 0.4, ("stepwise point disagrees with the paper's own Schechter fit", zn, p, sch)
    rid = f"bouwens21.uvlf.z{zc:g}.stepwise"
    records.append(base(rid, "Bouwens et al. 2021", "uvlf", zc, AX_UV, pts_record(pts), "published-table", CITE_B + ", stepwise LF table", DOI_B, ARX, ("ms.tex", "Table: stepwise determination of the rest-frame UV LF"), sha, DEF_B,
                        f"dropout-selected galaxies at z~{zn}" + (" (Oesch et al. 2018 sample)" if zn == 10 else ""), f"Stepwise (SWML) UV luminosity function at z~{zn} from the HUDF, HFF parallel fields and blank fields; errors are the quoted 1-sigma symmetric errors, converted to log10 (a lower bound is omitted where the error exceeds the value); upper limits are not included.", zrange=(zc, zc)))
for zc, (ms, phi, al) in sorted(SCHP.items()):
    zn = [k for k, v in ZMAP.items() if v == zc][0]
    xs = [r[0] for r in bins[zn]]
    rep, dom = sch_record(phi, ms, al, min(xs), max(xs))
    r = base(f"bouwens21.uvlf.z{zc:g}.schechter", "Bouwens et al. 2021 (Schechter fit)", "uvlf", zc, AX_UV, rep, "published-fit", CITE_B + ", Schechter parameters table", DOI_B, ARX, ("ms.tex", "Table: Schechter parameters of the rest-frame UV LFs"), sha, DEF_B,
             f"dropout-selected galaxies at z~{zn}", f"Schechter fit to the UV LF at <z>={zc} over the magnitude range of the stepwise points (M*={ms}, phi*={phi:.2e}, alpha={al}).", zrange=(zc, zc))
    r["domain"] = dom
    records.append(r)

# ---- Harikane et al. 2023 (ApJS 265, 5) ----
ARX = "2208.01612"
src = vf.fetch_arxiv(ARX) / "ms_jwst_v3.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
DEF_H = {"uvBand": UVBAND, "uvBandNote": "M_UV, JWST dropout galaxies", "dustCorrection": "none (observed LF)", "cosmology": {"H0": 67.66, "Om": 0.3111}, "densityFrame": "comoving", "population": "dropout-selected galaxies (early JWST data)"}
CITE_H = "Harikane et al. 2023, ApJS 265, 5 (arXiv:2208.01612)"
DOI_H = "10.3847/1538-4365/acaaa9"
lf = tex[tex.index("Obtained Luminosity Function at Each Redshift"):]
lf = lf[lf.index("\\startdata") + 10:lf.index("\\enddata")]
HZ = {"F115W-Drop": 9, "F150W-Drop": 12, "F200W-Drop": 16}
cur = None
hb = {}
for line in lf.split("\\\\"):
    line = line.replace("\\hline", "").strip()
    m = re.search(r"(F\d+W-Drop)", line)
    if m:
        cur = HZ[m.group(1)]
        hb[cur] = []
        continue
    c = [x.strip() for x in line.split("&")]
    if len(c) == 2 and cur:
        M = float(clean(c[0]).replace("−", "-"))
        t = clean(c[1]).replace(" ", "")
        if t.startswith("<"):
            hb[cur].append((M, None))
            continue
        m = re.match(r"\((\d+\.?\d*)\^\{\+(\d+\.?\d*)\}_\{-(\d+\.?\d*)\}\)\\times10\^\{(-?\d+)\}", t)
        assert m, t
        e = 10.0 ** int(m.group(4))
        hb[cur].append((M, (float(m.group(1)) * e, float(m.group(2)) * e, float(m.group(3)) * e)))
assert [len(hb[z]) for z in (9, 12, 16)] == [6, 6, 2] and abs(hb[9][4][1][0] - 2.24e-4) < 1e-12 and abs(hb[12][3][1][0] - 1.31e-5) < 1e-12, "Harikane table spot check"
fit = tex[tex.index("Fit Parameters for Luminosity Functions"):]
fit = fit[:fit.index("\\enddata")]
SCHH = {9: (-21.24, -4.83), 12: (-20.47, -5.06), 16: (-20.80, -5.84)}
assert "-21.24^{+0.45}_{-0.59}" in clean(fit).replace(" ", "") and "-4.83^{+0.37}_{-0.49}" in clean(fit).replace(" ", "") and "-20.47^{+1.94}_{-0.15}" in clean(fit).replace(" ", ""), "Schechter fit table spot check"
for z, rows in hb.items():
    pts = []
    for M, v in sorted(rows):
        if v is None:
            continue
        phi, up, lo = v
        pt = {"x": round(M, 2), "y": round(math.log10(phi), 4), "yHigh": round(math.log10(phi + up), 4)}
        if phi - lo > 0:
            pt["yLow"] = round(math.log10(phi - lo), 4)
        pts.append(pt)
    nlim = sum(1 for _, v in rows if v is None)
    records.append(base(f"harikane23.uvlf.z{z}.binned", "Harikane et al. 2023", "uvlf", float(z), AX_UV, pts_record(pts), "published-table", CITE_H + ", binned UV LF table", DOI_H, ARX, ("ms_jwst_v3.tex", "Table: obtained luminosity function at each redshift"), sha, DEF_H,
                        f"F{ {9: '115', 12: '150', 16: '200'}[z] }W-dropout candidates at z~{z}", f"Binned UV luminosity function at z~{z} from early JWST NIRCam data; asymmetric 1-sigma errors converted to log10; {nlim} upper limit{'s' if nlim != 1 else ''} not included.", zrange=(float(z), float(z))))
    ms, lp = SCHH[z]
    rep, dom = sch_record(10 ** lp, ms, -2.35, -23.0 if z != 16 else -23.6, -18.0 if z != 16 else -20.6)
    r = base(f"harikane23.uvlf.z{z}.schechter", "Harikane et al. 2023 (Schechter fit)", "uvlf", float(z), AX_UV, rep, "published-fit", CITE_H + ", fit parameters table", DOI_H, ARX, ("ms_jwst_v3.tex", "Table: fit parameters for luminosity functions"), sha, DEF_H,
             f"F{ {9: '115', 12: '150', 16: '200'}[z] }W-dropout candidates at z~{z}", f"Schechter fit (alpha fixed at -2.35) over the magnitude range of the binned data; M*={ms}" + (" (fixed)" if z == 16 else "") + f", log phi*={lp}.", zrange=(float(z), float(z)))
    r["domain"] = dom
    records.append(r)
tab = tex[tex.index("Obtained Cosmic UV Luminosity Density and SFR Density"):]
tab = tab[tab.index("\\startdata") + 10:tab.index("\\enddata")]
rows = {}
for line in tab.split("\\\\"):
    tri = r"\$(-?\d+\.\d+)_\{-(\d+\.\d+)\}\^\{\+(\d+\.\d+)\}\$"
    m = re.match(r"\s*\$z\\sim(\d+)\$\s*&\s*" + tri + r"\s*&\s*" + tri + r"\s*&\s*" + tri, line.replace("\n", " "))
    if m:
        g = [float(x) for x in m.groups()[1:]]
        rows[int(m.group(1))] = {"uv": tuple(g[3:6]), "dc": tuple(g[6:9])}
assert set(rows) == {9, 12, 16} and rows[9]["dc"] == (-2.61, 0.16, 0.18) and rows[12]["uv"] == (-3.33, 0.26, 0.26), "SFRD table spot check"
DEF_S = {"imf": "salpeter55", "sfrIndicator": "UV luminosity, K_UV = 1.15e-28 Msun yr^-1 / (erg s^-1 Hz^-1) (Madau & Dickinson 2014)", "sfrIntegrationLimit": "double power-law LF integrated to M_UV = -17", "densityFrame": "comoving", "cosmology": {"H0": 67.66, "Om": 0.3111}, "population": "all galaxies brighter than M_UV = -17"}
for key, dc, label in (("dc", True, "dust-corrected"), ("uv", False, "uncorrected for dust")):
    pts = [{"x": float(z), "y": rows[z][key][0], "yLow": round(rows[z][key][0] - rows[z][key][1], 3), "yHigh": round(rows[z][key][0] + rows[z][key][2], 3)} for z in (9, 12, 16)]
    d = dict(DEF_S, dustCorrection="dust-corrected (beta_UV relations)" if dc else "none (UV only)")
    records.append(base(f"harikane23.sfrd.{'dustcorr' if dc else 'uvonly'}", "Harikane et al. 2023" + ("" if dc else " (UV only)"), "sfrd", 12.0, AX_SFRD, pts_record(pts), "published-table", CITE_H + ", SFR density table", DOI_H, ARX, ("ms_jwst_v3.tex", "Table: cosmic UV luminosity density and SFR density"), sha, d,
                        "all galaxies brighter than M_UV = -17", f"Cosmic SFR density at z~9, 12 and 16 ({label}) from integrating the double power-law UV LF to M_UV = -17; asymmetric 1-sigma errors converted to dex.", zrange=(9.0, 16.0)))
    records[-1]["epoch"]["mode"] = "observational-bin"

# ---- Donnan et al. 2024 (MNRAS 533, 3222) ----
ARX = "2403.03171"
src = vf.fetch_arxiv(ARX) / "primer_LF.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
tb = tex[tex.index("\\label{tab:LF_points}"):]
tb = tb[tb.index("\\hline") + 6:tb.index("\\end{tabular}")]
db = {}
for line in tb.split("\\\\"):
    line = line.replace("\\hline", "").strip()
    c = [x.strip() for x in line.split("&")]
    if len(c) == 3 and re.match(r"^\d+(\.\d+)?$", c[0]):
        z = float(c[0])
        M = float(clean(c[1]).replace("−", "-"))
        m = re.match(r"(\d+)\^\{\+(\d+)\}_\{-(\d+)\}", clean(c[2]).replace(" ", ""))
        assert m, c
        db.setdefault(z, []).append((M, float(m.group(1)) * 1e-6, float(m.group(2)) * 1e-6, float(m.group(3)) * 1e-6))
assert sorted(db) == [9.0, 10.0, 11.0, 12.5, 14.5] and [len(db[z]) for z in sorted(db)] == [7, 7, 7, 7, 1] and abs(db[9.0][4][1] - 486e-6) < 1e-12 and abs(db[12.5][6][1] - 217e-6) < 1e-12, "Donnan table spot check"
DEF_D = {"uvBand": UVBAND, "uvBandNote": "M_UV, JWST PRIMER/JADES/NGDEEP", "dustCorrection": "none (observed LF)", "cosmology": "unspecified", "densityFrame": "comoving", "population": "galaxies at 8.5<z<15.5 from JWST/NIRCam imaging"}
DEF_D.pop("cosmology")
for z, rows in sorted(db.items()):
    pts = []
    for M, phi, up, lo in sorted(rows):
        pt = {"x": round(M, 2), "y": round(math.log10(phi), 4), "yHigh": round(math.log10(phi + up), 4)}
        if phi - lo > 0:
            pt["yLow"] = round(math.log10(phi - lo), 4)
        pts.append(pt)
    records.append(base(f"donnan24.uvlf.z{z:g}.binned", "Donnan et al. 2024", "uvlf", z, AX_UV, pts_record(pts), "published-table", "Donnan et al. 2024, MNRAS 533, 3222 (arXiv:2403.03171), binned UV LF table", "10.1093/mnras/stae2037", ARX, ("primer_LF.tex", "Table: computed UV LF data points"), sha, DEF_D,
                        f"photometric-redshift selected galaxies at z={z:g}", f"Binned UV luminosity function at z={z:g} from combined JWST PRIMER, JADES and NGDEEP imaging; asymmetric 1-sigma errors converted to log10.", zrange=(z, z)))

# ---- Madau & Dickinson 2014 (ARA&A 52, 415) ----
ARX = "1403.0007"
src = vf.fetch_arxiv(ARX) / "paper.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
assert r"0.015\,{(1+z)^{2.7}\over 1+[(1+z)/2.9]^{5.6}}" in tex, "MD14 equation 15 not found as quoted"
expr = "log10(0.015*Math.pow(1+x,2.7)/(1+Math.pow((1+x)/2.9,5.6)))"
rep = {"type": "parametric", "equation": "psi(z) = 0.015 (1+z)^2.7 / (1 + ((1+z)/2.9)^5.6) Msun yr^-1 Mpc^-3 (their Eq. 15)", "expression": expr, "parameters": {}}
r = base("madau14.sfrd.fit", "Madau & Dickinson 2014", "sfrd", 2.0, AX_SFRD, rep, "published-fit", "Madau & Dickinson 2014, ARA&A 52, 415 (arXiv:1403.0007), Eq. 15", "10.1146/annurev-astro-081811-125615", ARX, ("paper.tex", "Equation 15"), sha,
         {"imf": "salpeter55", "sfrIndicator": "UV and IR compilation", "sfrIntegrationLimit": "UV integrated to 0.03 L*(z=3); IR to the survey limits", "dustCorrection": "dust-corrected", "densityFrame": "comoving", "cosmology": {"H0": 70.0, "Om": 0.3}, "population": "all galaxies"},
         "all galaxies", "Best-fitting function to the compiled cosmic star-formation history; a Salpeter IMF (0.1-100 Msun) is the reference throughout the review, so divide by about 1.6 for a Chabrier-like IMF before comparing with simulations that adopt one.", zrange=(0.0, 8.0))
r["domain"] = {"xMin": 0.0, "xMax": 8.0}
records.append(r)
for rec in records:
    if rec["representation"]["type"] == "points":
        assert all(a["x"] < b["x"] for a, b in zip(rec["representation"]["points"], rec["representation"]["points"][1:])), rec["id"]
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} observational UV LF and SFR density records")
