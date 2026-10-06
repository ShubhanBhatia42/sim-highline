import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1704.00954"
DOI = "10.1093/mnras/stx841"
src = vf.fetch_arxiv(ARXIV) / "p.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
CITE = f"Wilkins et al. 2017, MNRAS 469, 2517 (arXiv:{ARXIV})"
RUN = "BlueTides (400 cMpc/h)"


def table(label):
    m = re.search(r"\\begin\{table\*?\}(?:(?!\\end\{table).)*?\\label\{" + re.escape(label) + r"\}.*?\\end\{table\*?\}", tex, re.S)
    return m.group(0)


def num(t):
    t = t.replace("$", "").strip()
    return None if t in ("-", "") else float(t)


def by_bin_rows(label, zs):
    """rows are mass or magnitude bins ('lo - hi'), columns are redshifts; returns {block: {z: [(centre, value)]}}"""
    out, block = {}, "all"
    for line in table(label).split("\\\\"):
        if "multicolumn{7}" in line and "bf" in line:
            block = re.search(r"\{\\bf ([^}]*)\}", line).group(1)
            continue
        c = [x.strip() for x in line.replace("\\hline", "").split("&")]
        m = re.match(r"\$\s*(-?[\d.]+)\s*\$\s*-\s*\$\s*(-?[\d.]+)\s*\$", c[0]) if c else None
        if m and len(c) == len(zs) + 1:
            centre = (float(m.group(1)) + float(m.group(2))) / 2
            for z, v in zip(zs, c[1:]):
                if num(v) is not None:
                    out.setdefault(block, {}).setdefault(z, []).append((round(centre, 3), num(v)))
    return out


def by_z_rows(label, nbins):
    """rows are redshifts, columns are bins 'lo-hi' of the header; returns {block: {z: [(centre, value)]}}"""
    t = table(label)
    hdr = re.search(r"\$z\$\s*&(.*?)\\\\", t, re.S).group(1)
    centres = [(float(a) + float(b)) / 2 for a, b in re.findall(r"\$\s*(-?[\d.]+)\s*\$\s*-\s*\$\s*(-?[\d.]+)\s*\$", hdr)]
    assert len(centres) == nbins, (label, centres)
    out, block = {}, "all"
    for line in t.split("\\\\"):
        if "multicolumn" in line and "bf" in line and "&" in line:
            block = re.search(r"\{\\bf ([^}]*)\}", line).group(1)
            continue
        c = [x.strip() for x in line.replace("\\hline", "").split("&")]
        if len(c) == nbins + 1 and re.fullmatch(r"-?[\d.]+", c[0]):
            z = float(c[0])
            for ce, v in zip(centres, c[1:]):
                if num(v) is not None:
                    out.setdefault(block, {}).setdefault(z, []).append((round(ce, 3), num(v)))
    return out


ZS6 = [13.0, 12.0, 11.0, 10.0, 9.0, 8.0]
gsmf = by_bin_rows("tab:GSMF", ZS6)["all"]
uvlf = by_bin_rows("tab:UVLF", ZS6)
phys = by_z_rows("tab:physical", 9)
dm_t = table("tab:DM_stellar")
dmc = [(float(a) + float(b)) / 2 for a, b in re.findall(r"\$(-?[\d.]+)\$-\$(-?[\d.]+)\$", dm_t.split("stellar-to-dark")[0])]
dm = {}
for line in dm_t.split("stellar-to-dark matter mass ratio")[1].split("\\\\"):
    c = [x.strip() for x in line.replace("\\hline", "").split("&")]
    if len(c) == 8 and re.fullmatch(r"-?[\d.]+", c[0]):
        dm[float(c[0])] = [(round(ce, 3), num(v)) for ce, v in zip(dmc, c[1:]) if num(v) is not None]
smbh = list(by_z_rows("tab:SMBH", 9).values())[0]
sch = {}
for line in table("tab:parameters_redshift").split("\\\\"):
    c = [x.strip() for x in line.replace("\\hline", "").split("&")]
    if len(c) == 4 and re.fullmatch(r"\d+", c[0]):
        sch[float(c[0])] = tuple(float(x) for x in c[1:])
ssfr = [v for k, v in phys.items() if "specific" in k][0]
zsfg = [v for k, v in phys.items() if "star forming gas" in k][0]
assert gsmf[8.0][0] == (8.1, -2.76) and gsmf[13.0][-1] == (8.5, -6.4) and len(gsmf[8.0]) == 12
assert uvlf["intrinsic far-UV luminosity function"][8.0][-1] == (-17.25, -2.44) and uvlf["observed (dust-corrected) far-UV luminosity function"][13.0][0] == (-20.25, -6.59)
assert ssfr[10.0][0] == (8.125, -7.91) and zsfg[9.0][0] == (8.125, -3.02) and dm[8.0][0] == (10.625, -2.52) and dm[13.0] == [(10.625, -2.75), (10.875, -2.56)]
assert [p for p in smbh[10.0]][-1] == (9.625, 6.69) and sch[8.0] == (-20.93, -3.92, -2.04) and sorted(gsmf) == sorted(ZS6)
SCH = "log10(0.4*Math.LN10*phi*Math.pow(10,-0.4*(x-Ms)*(alpha+1))*Math.exp(-Math.pow(10,-0.4*(x-Ms))))"
records = []


def rec(rid, relation, z, axes, rep, pop, warning, defs, tier="published-table", member="p.tex", rankable=True, dom=None, run=RUN):
    pts = rep.get("points")
    return {"id": rid, "source": "BlueTides", "run": run, "kind": "simulation", "relation": relation,
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
            "axes": axes, "domain": dom or {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]}, "representation": rep, "scatter": None,
            "selection": {"population": pop, "warning": warning}, "definitions": defs,
            "provenance": {"tier": tier, "citation": CITE + f", {member}", "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": vf.RETRIEVED, "checksumSha256": sha,
                           "sourceMember": "p.tex tables (arXiv source, transcribed)", "extractionMethod": "transcribed from the arXiv LaTeX tables and parsed by script; bin centres are the midpoints of the tabulated bins; spot-checked against quoted values in the script"},
            "calibration": "prediction", "rankable": rankable, "notes": "Bin values as tabulated by the authors; x is the bin midpoint."}


def pts_rep(rows, kind="scatter"):
    return {"type": "points", "intervalKind": "unspecified", "connect": True, "points": [{"x": x, "y": y} for x, y in rows]}


D0 = {"imf": "unspecified", "population": "all galaxies"}
for z, rows in sorted(gsmf.items()):
    records.append(rec(f"wilkins17.bluetides.gsmf.z{z:g}", "gsmf", z, {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function per dex", "yUnit": "log10(cMpc^-3 dex^-1)"},
                       pts_rep(rows), "all galaxies", f"Stellar mass function of BlueTides at z={z:g} in 0.2 dex bins (tabulated values; the paper does not state the mass aperture or cosmology near the table).", dict(D0, massDefinition="unspecified", densityFrame="comoving"), member="Table GSMF"))
for z, rows in sorted(ssfr.items()):
    records.append(rec(f"wilkins17.bluetides.ssfr.z{z:g}", "ssfr", z, {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 median specific star formation rate", "yUnit": "log10(yr^-1)"},
                       pts_rep(rows), "all galaxies, median per 0.25 dex mass bin", f"Median sSFR of BlueTides galaxies at z={z:g} in 0.25 dex stellar mass bins (tabulated).", dict(D0, massDefinition="unspecified", sfrStatistic="median"), member="Table physical (median sSFR)"))
for z, rows in sorted(zsfg.items()):
    records.append(rec(f"wilkins17.bluetides.mzrraw.z{z:g}", "mzr", z, {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 median star-forming gas metallicity Z_SFG (metal mass fraction)", "yUnit": "log10(mass fraction)"},
                       pts_rep(rows), "all galaxies, median per 0.25 dex mass bin", f"Median star-forming gas metal mass fraction of BlueTides galaxies at z={z:g} (tabulated; log10 of the absolute mass fraction, not Z/Zsun).",
                       {"metallicityQuantity": "gas-metal-mass-fraction", "metallicityCalibration": "intrinsic-simulation (star-forming gas, median)", "imf": "unspecified", "population": "all galaxies"}, member="Table physical (star forming gas metallicity)"))
for z, rows in sorted(dm.items()):
    records.append(rec(f"wilkins17.bluetides.shmr.z{z:g}", "shmr", z, {"xDefinition": "log10 dark matter mass M_DM of the host", "xUnit": "log10(Msun)", "yDefinition": "log10 stellar-to-dark-matter mass ratio M*/M_DM", "yUnit": "dex"},
                       pts_rep(rows), "all galaxies", f"Stellar-to-dark-matter mass ratio of BlueTides at z={z:g} in 0.25 dex bins (tabulated); the ratio is to the dark matter mass M_DM of the host, not an explicit M200.", dict(D0, massDefinition="unspecified", haloMassDefinition="dark-matter-mass-of-host"), member="Table DM_stellar"))
for z, rows in sorted(smbh.items()):
    if len(rows) >= 2:
        records.append(rec(f"wilkins17.bluetides.bh.median.z{z:g}", "bh", z, {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 median super-massive black hole mass", "yUnit": "log10(Msun)"},
                           pts_rep(rows), "galaxies hosting a black hole, median per 0.25 dex mass bin", f"Median central SMBH mass of BlueTides galaxies at z={z:g} (tabulated; bins with too few hosts are empty).", dict(D0, massDefinition="unspecified", population="bh-hosts", bhMassMethod="unspecified"), member="Table SMBH", run=RUN + ", medians (Wilkins+17)"))
for key, tag, dust in (("intrinsic far-UV luminosity function", "intrinsic", "none (intrinsic)"), ("observed (dust-corrected) far-UV luminosity function", "observed", "dust attenuated (the paper's 'observed'; the table heading says dust-corrected, the figure caption and text say attenuated)")):
    for z, rows in sorted(uvlf[key].items()):
        records.append(rec(f"wilkins17.bluetides.uvlf.{tag}.z{z:g}", "uvlf", z, {"xDefinition": f"absolute far-UV (150 nm) magnitude, {tag}", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"},
                           pts_rep(sorted(rows)), "all galaxies", f"{tag.capitalize()} rest-frame far-UV (150 nm) luminosity function of BlueTides at z={z:g} in 0.5 mag bins (tabulated).",
                           dict(D0, uvBand="rest-frame far-UV 150 nm, AB", dustCorrection=dust, densityFrame="comoving"), member=f"Table UVLF ({tag})", run=RUN + (", intrinsic" if tag == "intrinsic" else ", dust attenuated")))
for z, (ms, lp, al) in sorted(sch.items()):
    xs = [x for x, _ in uvlf["observed (dust-corrected) far-UV luminosity function"][z]]
    records.append(rec(f"wilkins17.bluetides.uvlf.schechter.z{z:g}", "uvlf", z, {"xDefinition": "absolute far-UV (150 nm) magnitude, attenuated", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude (Schechter fit)", "yUnit": "log10(cMpc^-3 mag^-1)"},
                       {"type": "parametric", "equation": "Phi(M) = 0.4 ln10 phi* 10^(-0.4 (M-M*)(alpha+1)) exp(-10^(-0.4 (M-M*))) per mag", "expression": SCH, "parameters": {"phi": 10 ** lp, "Ms": ms, "alpha": al}},
                       "all galaxies", f"Schechter fit of Wilkins et al. 2017 to the observed (attenuated) UV luminosity function at z={z:g} (M*={ms}, log phi*={lp}, alpha={al}); the domain is the span of the tabulated bins because the paper does not state the fitted range.",
                       dict(D0, uvBand="rest-frame far-UV 150 nm, AB", dustCorrection="dust attenuated", densityFrame="comoving"), tier="published-fit", member="Table parameters_redshift", rankable=False, dom={"xMin": min(xs), "xMax": max(xs)}, run=RUN + ", dust attenuated, Schechter fit"))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "wilkins17-bluetides.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} BlueTides records from Wilkins+17")
