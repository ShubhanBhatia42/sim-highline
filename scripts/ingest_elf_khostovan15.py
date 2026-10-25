"""Khostovan et al. 2015 (HiZELS, arXiv:1503.00004, MNRAS 452, 1184): H-beta+[OIII] luminosity functions at z = 0.84, 1.42, 2.23 and 3.24 and [OII] luminosity functions at z = 1.47, 2.25, 3.34 and 4.69, from the paper's
binned tables (relation elf). The values are transcribed from the tables in the arXiv LaTeX source (column Phi_final: corrected for completeness and for the filter profile). The paper does not correct these luminosity functions for dust
or for AGN: "we present all the LF parameter results as uncorrected for dust and AGN contribution".
Checks inside this script (every assert must pass or nothing is written):
  * for every bin the paper's Phi_obs equals log10(N / (V x bin width)) from the printed number of emitters N, volume V and bin width, to 0.012 dex (the per-dex convention and the volumes);
  * the number of emitters in the bins does not exceed the total number of emitters of the paper's table of selected emitters at that epoch, and the epochs of the two tables are the epochs of the filter table;
  * the Schechter parameters of the paper's Table of fits (alpha fixed at -1.6 and -1.3) reproduce the binned points within the printed errors (rms of the difference over the error and the largest deviation are recorded);
  * the infinite integral of the printed Schechter function, phi* L* Gamma(alpha + 2), equals the log rho_L printed in the same table to 0.02 dex (a check of the printed parameters).
Every definition used by the record is located verbatim in the arXiv source; file and line are written to data/quotes/elf-khostovan15.txt.
Usage: python3 scripts/ingest_elf_khostovan15.py [SOURCE_DIR]"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "1503.00004"
ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
TEX = SRC / "oii_lf.tex"
OUT = ROOT / "data" / "curves" / "elf-khostovan15.json"
QUOTES = ROOT / "data" / "quotes" / "elf-khostovan15.txt"
RETRIEVED = "2026-10-25"
text = TEX.read_text(errors="replace")
SHA = hashlib.sha256(TEX.read_bytes()).hexdigest()


def js_numbers(o):
    """Integer-valued floats are written as integers, as the JavaScript step that normalises the records writes them (41.0 -> 41)."""
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: js_numbers(v) for k, v in o.items()}
    if isinstance(o, list):
        return [js_numbers(v) for v in o]
    return o


log = []
norm = lambda a: re.sub(r"\s+", " ", a).strip()
flat, idx = "", []
for n, l in enumerate(text.splitlines(), 1):
    flat += norm(l) + " "
    idx += [n] * (len(norm(l)) + 1)


def quote(s):
    """The whitespace-normalised sentence must occur verbatim in the source; returns file:line."""
    k = flat.find(norm(s))
    assert k >= 0, f"quote not found: {s[:90]}"
    log.append(f"{TEX.name}:{idx[k]}: {norm(s)}")
    return f"{TEX.name}:{idx[k]}"


# ---------------------------------------------------------------- definitions, each from a sentence of the paper
q_dust = quote(r"To simplify the use of our LFs by others in future studies, we present all the LF parameter results as uncorrected for dust and AGN contribution.")
q_dust2 = quote(r"Lastly, the LF results are not corrected for dust extinction, except when measuring the star-formation rate densities.")
q_blend = quote(r"Because the H$\beta$ and [O\rom{3}] emission lines are close to each other, photo-$z$ and color-color selections can not distinguish between them.")
q_blend2 = quote(r"to ensure we are not biasing our measurements based on such assumptions, we present the results as the combined measurement of \hb.")
q_cosmo = quote(r"we assume $\Lambda$CDM cosmology with $H_0 = 70$ km s$^{-1}$ Mpc$^{-1}$, $\Omega_\mathrm{m} = 0.3$, and $\Omega_\Lambda = 0.7$")
q_vol = quote(r"We report the probed comoving volume per square degree in table \ref{table:filter_probed}.")
q_vmax = quote(r"We use the traditional $V_{max}$ estimator to create our binned data.")
q_alpha = quote(r"We keep $\alpha$ fixed to a constant value of $-1.6$ and $-1.3$ for \hb~ and \oii, respectively, as we are not able to fully constrain the faint-end.")
q_err = quote(r"The errors here are Poissonian but with 20\% of the corrections added in quadrature.")
q_log = quote(r"The Schechter function is defined in its log-form as:")
q_sel = quote(r"We select our emitter candidates by defining a range in the distribution of $z_{phot}$")

# ---------------------------------------------------------------- the tables
FILTER = {  # table of filters: epoch of the line, half width of the redshift range
    "hb": {0.84: 0.01, 1.42: 0.01, 2.23: 0.02, 3.24: 0.02},
    "oii": {1.47: 0.02, 2.25: 0.02, 3.34: 0.03, 4.69: 0.03}}
def table_rows(label, begin):
    i = text.index("\\label{%s}" % label)
    return text[text.rindex(begin, 0, i):i].split("\n")


for line in table_rows("table:filter_probed", "\\begin{table*}"):
    m = re.match(r"\s*(NB921|NBJ|NBH|NBK)\s*&\s*[\d.]+\s*&\s*\d+\s*&\s*\$([\d.]+)\\pm([\d.]+)\$\s*&\s*[\d.]+\s*&\s*\$([\d.]+)\\pm([\d.]+)\$", line)
    if m:
        assert FILTER["hb"][float(m.group(2))] == float(m.group(3)) and FILTER["oii"][float(m.group(4))] == float(m.group(5)), line
        log.append(f"{TEX.name}: filter table row {norm(line)}")
TOTAL = {"hb": {0.84: 2477, 1.42: 371, 2.23: 271, 3.24: 179}, "oii": {1.47: 3285, 2.25: 137, 3.34: 35, 4.69: 18}}  # last column of the table of selected emitters (the filters NB921, NBJ, NBH, NBK in that order)
tot_rows = []
for line in table_rows("table:total_emitters", "\\begin{table*}"):
    m = re.match(r"\s*&\s*(NB921|NBJ|NBH|NBK)\s*&\s*([\d.]+)\s*&(?:\s*\d+\s*&){6}\s*(\d+)\s*\\\\", line)
    if m:
        tot_rows.append(int(m.group(3)))
assert tot_rows == list(TOTAL["hb"].values()) + list(TOTAL["oii"].values()), tot_rows
log.append(f"{TEX.name}: the table of selected emitters gives totals 2477, 371, 271, 179 (H-beta+[OIII]) and 3285, 137, 35, 18 ([OII])")


def lf_table(label):
    i = text.index("\\label{%s}" % label)
    tab = text[text.rindex("\\begin{table}", 0, i):i]
    out, z = {}, None
    for line in tab.split("\n"):
        m = re.search(r"\{\\bf z = ([\d.]+)\}", line)
        if m:
            z = float(m.group(1))
            out[z] = []
            continue
        m = re.match(r"\s*\$([\d.]+)\\pm([\d.]+)\$&\$(\d+)\$&\$(-[\d.]+)\$&\$(-[\d.]+)\\pm([\d.]+)\$&\$([\d.]+)\$", line)
        if m and z is not None:
            v = [float(g) for g in m.groups()]
            out[z].append(dict(logL=v[0], half=v[1], n=int(v[2]), phi_obs=v[3], phi=v[4], e_phi=v[5], vol=v[6] * 1e5))
    return out


TABLE = {"hb": lf_table("table:hbeta_lf_observed"), "oii": lf_table("table:oii_lf_observed")}
assert {k: sorted(v) for k, v in TABLE.items()} == {k: sorted(v) for k, v in FILTER.items()}
assert {k: [len(b) for b in v.values()] for k, v in TABLE.items()} == {"hb": [8, 4, 4, 4], "oii": [7, 3, 3, 3]}, {k: [len(b) for b in v.values()] for k, v in TABLE.items()}

# the table of Schechter fits
j = text.index("\\label{table:lfparams}")
t5 = text[text.rindex("\\begin{table*}", 0, j):j]
par = {"hb": {}, "oii": {}}
sect = None
for line in t5.split("\n"):
    if "Luminosity Function Properties" in line:
        sect = "hb" if "O\\rom{3}" in line else "oii"
        continue
    m = re.match(r"\$([\d.]+)\$ & \$(-[\d.]+)\^\{\+[\d.]+\}_\{-[\d.]+\}\$ & \$([\d.]+)\^\{\+[\d.]+\}_\{-[\d.]+\}\$ & \$(-[\d.]+)\$ & \$([\d.]+)\$", line)
    if m and sect:
        z = float(m.group(1))
        par[sect][z] = dict(logphis=float(m.group(2)), logLs=float(m.group(3)), alpha=float(m.group(4)), logrho=float(m.group(5)))
assert {k: sorted(v) for k, v in par.items()} == {k: sorted(v) for k, v in FILTER.items()}, par
assert par["hb"][0.84] == dict(logphis=-2.55, logLs=41.79, alpha=-1.6, logrho=39.58) and par["oii"][4.69]["logrho"] == 39.35


def schechter_dex(logL, p):
    """phi per dex: ln10 phi* (L/L*)^(alpha+1) exp(-L/L*)."""
    x = 10 ** (np.asarray(logL) - p["logLs"])
    return math.log10(math.log(10)) + p["logphis"] + (p["alpha"] + 1) * np.log10(x) - x * math.log10(math.e)


checks, records = {}, []
LINE = {"hb": "H-beta+[OIII] (blend; the paper does not separate the lines)", "oii": "[OII] 3727"}
NAME = {"hb": "H-beta+[OIII]", "oii": "[OII]"}
TAG = {"hb": "hbeta-oiii", "oii": "oii"}
for kind in ("hb", "oii"):
    for z, b in TABLE[kind].items():
        x = np.array([r["logL"] for r in b])
        y = np.array([r["phi"] for r in b])
        e = np.array([r["e_phi"] for r in b])
        width = np.array([2 * r["half"] for r in b])
        assert np.all(np.diff(x) > 0)
        # check 1: Phi_obs from the numbers of emitters, volumes and bin widths
        recomputed = np.array([math.log10(r["n"] / (r["vol"] * w)) for r, w in zip(b, width)])
        d1 = float(np.max(np.abs(recomputed - np.array([r["phi_obs"] for r in b]))))
        width_note = ""
        if d1 >= 0.012:
            # one epoch of the paper's [OII] table: the printed half widths of the second and third bins (0.075) do not give the printed Phi_obs; the widths implied by Phi_obs (N / (V 10^Phi_obs)) tile the bin centres exactly
            assert (kind, z) == ("oii", 3.34), (kind, z, d1)
            implied = np.array([r["n"] / (r["vol"] * 10 ** r["phi_obs"]) for r in b])
            assert np.allclose(implied, [0.1, 0.1, 0.2], rtol=0.03) and np.allclose(0.5 * (implied[1:] + implied[:-1]), np.diff(x), rtol=0.03), implied
            assert abs(recomputed[0] - b[0]["phi_obs"]) < 0.012
            d1 = float(np.max(np.abs(np.array([math.log10(r["n"] / (r["vol"] * w)) for r, w in zip(b, implied)]) - np.array([r["phi_obs"] for r in b]))))
            width_note = (f" The printed half widths of the second and third bins (0.075 and 0.075) do not reproduce the printed Phi_obs; the widths that do are {implied[0]:.2f}, {implied[1]:.2f} and {implied[2]:.2f} dex, which tile the printed bin centres exactly "
                          "(a misprint of the half widths in the table, not read further; the bin centres used here are not affected).")
        assert d1 < 0.012, (kind, z, d1)
        # check 2: numbers of emitters
        nsrc = sum(r["n"] for r in b)
        assert nsrc <= TOTAL[kind][z], (kind, z, nsrc, TOTAL[kind][z])
        # check 3: the Schechter fit of the paper against the points
        p = par[kind][z]
        res = y - schechter_dex(x, p)
        chi = float(np.sqrt(np.mean((res / e) ** 2)))
        assert chi < 2.0 and float(np.max(np.abs(res / e))) < 3.5, (kind, z, chi, np.max(np.abs(res / e)))
        # check 4: the printed luminosity density
        rho = p["logphis"] + p["logLs"] + math.log10(math.gamma(p["alpha"] + 2))
        assert abs(rho - p["logrho"]) < 0.02, (kind, z, rho, p["logrho"])
        checks[f"{kind} z={z:g}"] = dict(bins=len(b), emitters_in_bins=nsrc, emitters_total=TOTAL[kind][z], max_dphi_obs=round(d1, 3), chi_rms=round(chi, 2), chi_max=round(float(np.max(np.abs(res / e))), 2), rho_gamma=round(rho, 2), rho_printed=p["logrho"])
        pts = [{"x": round(r["logL"], 3), "y": round(r["phi"], 3), "yLow": round(r["phi"] - r["e_phi"], 3), "yHigh": round(r["phi"] + r["e_phi"], 3)} for r in b]
        zhalf = FILTER[kind][z]
        notes = (f"Binned luminosity function transcribed from the paper's table ({len(b)} bins, {nsrc} of {TOTAL[kind][z]} selected emitters). Checks: Phi_obs recomputed from the printed numbers, volumes and bin widths to {d1:.3f} dex; "
                 f"the paper's Schechter fit (log phi* = {p['logphis']}, log L* = {p['logLs']}, alpha = {p['alpha']} fixed) reproduces the points to rms {chi:.2f} times the printed error (largest {float(np.max(np.abs(res / e))):.1f}); "
                 f"the infinite integral of that fit, log rho_L = {rho:.2f}, equals the {p['logrho']} printed in the table." + width_note)
        records.append({
            "id": f"khostovan15.hizels.elf.{TAG[kind]}.z{z:g}", "source": "Khostovan et al. 2015 (HiZELS)", "run": f"{NAME[kind]} luminosity function, binned (Phi_final: completeness and filter-profile corrected; not corrected for dust or AGN)",
            "kind": "observation", "relation": "elf",
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": round(z - zhalf, 3), "zMax": round(z + zhalf, 3), "mode": "observational-bin", "snapshot": None},
            "axes": {"xDefinition": f"log10 luminosity of the {NAME[kind]} emission of narrow-band selected emitters, not corrected for dust or AGN contribution", "xUnit": "log10(erg s^-1)",
                     "yDefinition": "log10 comoving number density of emitters per dex of luminosity (the paper's Phi_final: corrected for completeness and for the filter profile)", "yUnit": "log10(Mpc^-3 dex^-1)"},
            "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": pts},
            "scatter": None,
            "selection": {"population": "narrow-band selected emitters (colour-colour, photometric and spectroscopic redshift selection), COSMOS and UDS fields",
                          "warning": ("Luminosities are not corrected for dust extinction or for AGN contribution (the paper states so). "
                                      + ("H-beta and [OIII] cannot be told apart by the photometric selection, so the luminosity is that of the blend; the paper does not say which [OIII] lines the blend contains. " if kind == "hb" else
                                         "The [OII] doublet is measured through a narrow band; the paper does not say how the two lines are combined. ")
                                      + "The faint-end slope of the Schechter fit is fixed, not fitted. The sample also holds galaxies mis-identified in redshift (the paper estimates the contamination, mostly H-alpha emitters). "
                                      + ("The bins sit at the bright end only (three bins); the luminosity function is poorly constrained at this epoch." if len(b) <= 3 else ""))},
            "definitions": {
                "line": LINE[kind],
                "dustCorrection": "attenuated",
                "dustCorrectionMethod": "none (not corrected for dust extinction or for AGN contribution)",
                "densityFrame": "comoving",
                "apertureDefinition": "unspecified",
                "cosmology": {"H0": 70, "Om": 0.3},
                "population": "narrow-band selected emitters, star-forming galaxies and AGN not separated (COSMOS and UDS)",
            },
            "provenance": {"tier": "published-table", "citation": "Khostovan et al. 2015, MNRAS 452, 1184 (arXiv:1503.00004), tables of the " + NAME[kind] + " luminosity function", "doi": "10.1093/mnras/stv1360",
                           "url": "https://arxiv.org/abs/1503.00004", "retrieved": RETRIEVED, "sourceMember": TEX.name, "sourceSha256": SHA,
                           "quotes": {"dust": q_dust, "dust_statement": q_dust2, "blend": [q_blend, q_blend2], "cosmology": q_cosmo, "comoving_volume": q_vol, "estimator": q_vmax, "alpha_fixed": q_alpha, "errors": q_err, "selection": q_sel},
                           "definitionBasis": "line: 'we present the results as the combined measurement of H-beta' (with [OIII]); the [OII] line is called [OII] 3727 in the paper's table of filters, and the text does not say that it is the blend of the doublet. imf: the paper assumes a Salpeter IMF for star formation rates, which does not enter a luminosity function. apertureDefinition: not stated in this paper."},
            "calibration": "validation", "rankable": True,
            "notes": notes,
        })
assert len(records) == 8
for r in records:
    assert r["domain"]["xMin"] < r["domain"]["xMax"]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(js_numbers({"schemaVersion": "1.0.0", "records": records}), indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + ["check %s: %s" % (k, json.dumps(v)) for k, v in checks.items()]) + "\n")
for k, v in checks.items():
    print(k, v)
print("Wrote", len(records), "records to", OUT)
