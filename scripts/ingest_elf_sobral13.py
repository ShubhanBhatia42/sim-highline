"""Sobral et al. 2013 (HiZELS, arXiv:1202.3436, MNRAS 428, 1128): H-alpha luminosity functions at z = 0.40, 0.84, 1.47 and 2.23, from the paper's Table 4 (relation elf).

The values are transcribed from the table in the arXiv LaTeX source. The luminosities are corrected for [NII] contamination and for dust (a constant A(Halpha) = 1 mag), as the table caption says.
Checks inside this script (every assert must pass or nothing is written):
  * the number of sources in the table bins does not exceed the number of Halpha emitters of the paper's Table 3 at that redshift, and the totals of Table 3 reproduce the counts quoted in the text;
  * the best-fitting Schechter functions of the paper's Table 5 (alpha, L*, phi*) reproduce the tabulated points within the printed errors (rms of the difference over the error below 1.2, no bin beyond 3 sigma);
  * the Schechter function integrated above L = 10^41.6 erg/s reproduces the log rho_L(41.6) printed in Table 5 at z = 0.84, 1.47 and 2.23 to 0.05 dex (a check of the per-dex convention); at z = 0.4 it does not (0.37 dex lower), which is
    recorded and not used; points and fit give the same luminosity density over the bins at all four redshifts.
Every definition used by the record is located verbatim in the arXiv source; file and line are written to data/quotes/elf-sobral13.txt.
"""
import hashlib
import io
import json
import math
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np

ARXIV = "1202.3436"
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "curves" / "elf-sobral13.json"
QUOTES = ROOT / "data" / "quotes" / (OUT.stem + ".txt")
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/elf_sources") / ARXIV
RETRIEVED = "2026-10-23"
TEX = SRC / "FAINT_END_C_VARIANCE.tex"


def fetch(arxiv_id, dest):
    if dest.exists() and any(dest.iterdir()):
        return
    dest.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{arxiv_id}", headers={"User-Agent": "Mozilla/5.0"})
    blob = urllib.request.urlopen(req).read()
    Path(str(dest) + ".tar").write_bytes(blob)
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(dest)


def js_numbers(o):
    """Integer-valued floats are written as integers, as the JavaScript step that normalises the records writes them (41.0 -> 41)."""
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: js_numbers(v) for k, v in o.items()}
    if isinstance(o, list):
        return [js_numbers(v) for v in o]
    return o


fetch(ARXIV, SRC)
ARCHIVE_SHA = hashlib.sha256(Path(str(SRC) + ".tar").read_bytes()).hexdigest() if Path(str(SRC) + ".tar").exists() else None
text = TEX.read_text(errors="replace")
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
q_line = quote(r"L$_{\rm \bf H\alpha}$ has been corrected for both [N{\sc ii}] contamination and for dust extinction (using A$_{\rm H\alpha}=1$\,mag).")
q_nii = quote(r"A correction for the [N{\sc ii}] line contamination is therefore done, following the relation given in S12.")
q_dust = quote(r"a simple 1 mag of extinction is applied for the four redshifts and for all observed luminosities.")
q_cosmo = quote(r"An H$_0=70$\,km\,s$^{-1}$\,Mpc$^{-1}$, $\Omega_M=0.3$ and $\Omega_{\Lambda}=0.7$ cosmology is used.")
q_ap = quote(r"The $3''$ apertures are used to select and measure H$\alpha$ line fluxes: at $z=0.4$ the 3$''$ apertures measure the same physical area as 2$''$ apertures at $z=0.8,1.47,2.23$")
q_ap2 = quote(r"Photometry was measured in apertures of $2''$ diameter which at $z=0.8-2.2$ recover H$\alpha$ fluxes over $\approx16$\,kpc.")
q_com = quote(r"the H$\alpha$ survey probes a (co-moving) volume of $3.3\times10^5$\,Mpc$^3$\,deg$^{-2}$.")
q_ew = quote(r"corresponding to a $z=2.23$ rest-frame EW limit of 25\,\AA \ for H$\alpha$+[N{\sc ii}]; this is the same rest-frame equivalent width used at all redshifts.")
q_log = quote(r"In the $\log$ form, the Schechter function is given by:")
q_err = quote(r"Errors are Poissonian, but they include a further 20\% of the total completeness corrections added in quadrature.")
q_agn = quote(r"At the very bright end ($L>4L^*$), and particularly at $z>1$, there seems to be a deviation from a Schechter function.")
q_agn2 = quote(r"which become dominant at the highest luminosities")

# ---------------------------------------------------------------- Table 4 (binned luminosity functions)
i = text.index("\\label{LF_NUMBERS}")
tab = text[text.rindex("\\begin{table}", 0, i):i]
Z_KEYS = {"0.40": 0.40, "0.84": 0.84, "1.47": 1.47, "2.23": 2.23}
bins, z = {}, None
for line in tab.split("\n"):
    line = line.split("%")[0] if line.lstrip().startswith("%") else line
    m = re.search(r"z=([\d.]+)\$?\s*&", line)
    if m and "bf" in line:
        z = Z_KEYS[m.group(1)]
        bins[z] = []
        continue
    m = re.match(r"\s*\$([\d.]+)\\pm([\d.]+)\$\s*&\s*\$(\d+)\$\s*&\s*\$(-[\d.]+)\\pm([\d.]+)\$\s*&\s*\$(-[\d.]+)\\pm([\d.]+)\$\s*&\s*([\d.]+)", line)
    if m and z is not None:
        lo = [float(g) for g in m.groups()]
        bins[z].append(dict(logL=lo[0], half=lo[1], n=int(lo[2]), phi_obs=lo[3], e_obs=lo[4], phi=lo[5], e_phi=lo[6], vol=lo[7]))
assert sorted(bins) == [0.4, 0.84, 1.47, 2.23], bins.keys()
COUNTS = {0.4: 18, 0.84: 9, 1.47: 13, 2.23: 15}
assert {k: len(v) for k, v in bins.items()} == COUNTS, {k: len(v) for k, v in bins.items()}  # rows of the printed table (the commented-out row at z=2.23 is not read)

# ---------------------------------------------------------------- Table 3 (emitters; UKIRT NB_K plus the HAWK-I H2 survey at z = 2.23) and Table 5 (Schechter fits, rho_L)
T3 = {  # Halpha-selected emitters, COSMOS + UDS, by filter (rows of the printed table): NB921, NBJ, NBH, NBK
    0.4: (521, 1221), 0.84: (425, 212), 1.47: (327, 188), 2.23: (588, 184, 31, 14)}  # z = 2.23 also has the two HAWK-I (H2 filter) rows
for pair, row in ((r"NB921 & C & 155542 & 148702 & 2819 & 247  & -- & 521", 0.4), (r"NB921 & U & 236718 & 198256 & 6957 & 775  & -- & 1221", 0.4),
                  (r"NB$_{\rm J}$ & C & 32345 & 31661 & 700 & 40 & 46 & 425", 0.84), (r"NB$_{\rm J}$ & U & 21233 & 19916 & 551 & 49  & 30 & 212", 0.84),
                  (r"NB$_{\rm H}$ & C & 65912 & 64453 & 723 & 60  & 63 & 327", 1.47), (r"NB$_{\rm H}$ & U & 26084 & 23503 & 418 & 23  & 5 & 188", 1.47),
                  (r"NB$_{\rm K}$ & C & 99395 & 98085 & 1359 & 78 & 56 & 588", 2.23), (r"NB$_{\rm K}$ & U & 28276 & 26062 & 399 & 28 & 10 & 184", 2.23),
                  (r"H$_2$ & C & 1054 & 940 & 52 & 3 & 2 & 31", 2.23), (r"H$_2$ & U & 1193 & 1059 &  33 & 7 & 1 & 14", 2.23)):
    assert norm(pair) in flat, pair
TEXT_TOTALS = {0.4: 1742, 0.84: 637}
q_t = {0.4: quote(r"A total of 1742 H$\alpha$ emitters at $z=0.4$ are selected."), 0.84: quote(r"A total of 637 H$\alpha$ emitters at $z=0.84$ are selected.")}
for zz, tot in TEXT_TOTALS.items():
    assert sum(T3[zz]) == tot, (zz, T3[zz], tot)  # Table 3 reproduces the totals quoted in the text
# Table 5: L*, phi*, alpha (alpha fixed at -1.6 for L* and phi*; the alpha column is the 3-parameter fit), log rho_L above 10^41.6
j = text.index("\\label{lfs__}")
t5 = text[text.rindex("\\begin{table*}", 0, j):j]
rows5 = {}
for zz in (0.40, 0.84, 1.47, 2.23):
    m = re.search(r"z=%s\\pm[\d.]+\$\s*&\s*\$([\d.]+)\^\{\+[\d.]+\}_\{-[\d.]+\}\$\s*&\s*\$(-[\d.]+)\^\{\+[\d.]+\}_\{-[\d.]+\}\$\s*&\s*\$(-[\d.]+)\^\{\+[\d.]+\}_\{-[\d.]+\}\$\s*&\s*\$([\d.]+)\^" % ("%.2f" % zz), t5)
    assert m, zz
    rows5[zz] = dict(logLs=float(m.group(1)), logphis=float(m.group(2)), alpha=float(m.group(3)), logrho416=float(m.group(4)))
assert rows5[0.4] == dict(logLs=41.95, logphis=-3.12, alpha=-1.75, logrho416=38.99)
assert rows5[2.23] == dict(logLs=42.87, logphis=-2.78, alpha=-1.59, logrho416=40.26)


def schechter_dex(logL, p, alpha):
    """phi per dex: ln10 phi* (L/L*)^(alpha+1) exp(-L/L*) (the 'log form' of the paper's equation)."""
    x = 10 ** (np.asarray(logL) - p["logLs"])
    return np.log10(math.log(10)) + p["logphis"] + (alpha + 1) * np.log10(x) - x * math.log10(math.e)


checks = {}
records = []
quote(r"NB921 & 0.9196 &132 & 0.401$\pm$0.010 &  5.13 \\")
quote(r"NB$_{\rm J}$ & 1.211 & 150 & 0.845$\pm$0.015 & 14.65 \\")
quote(r"NB$_{\rm H}$ &1.617 & 211 & 1.466$\pm$0.016 & 33.96 \\")
quote(r"NB$_{\rm K}$ & 2.121 & 210  & 2.231$\pm$0.016 & 38.31 \\")
Z_RANGE = {0.4: (0.391, 0.411), 0.84: (0.830, 0.860), 1.47: (1.450, 1.482), 2.23: (2.215, 2.247)}  # Table 1: z(Halpha) +- the printed half width of the filter FWHM
for zz in (0.4, 0.84, 1.47, 2.23):
    b = bins[zz]
    x = np.array([r["logL"] for r in b])
    y = np.array([r["phi"] for r in b])
    e = np.array([r["e_phi"] for r in b])
    assert np.all(np.diff(x) > 0)
    nsrc = sum(r["n"] for r in b)
    assert nsrc <= sum(T3[zz]), (zz, nsrc, T3[zz])
    # check 2: Schechter fit of Table 5 against the points (alpha of the 3-parameter fit; the paper fixes alpha = -1.6 for L* and phi*)
    p = rows5[zz]
    model = schechter_dex(x, p, p["alpha"])
    res = y - model
    chi = float(np.sqrt(np.mean((res / e) ** 2)))
    rms = float(np.sqrt(np.mean(res ** 2)))
    assert chi < 1.2 and float(np.max(np.abs(res / e))) < 3, (zz, chi, float(np.max(np.abs(res / e))))  # within the printed errors, bin by bin
    # check 3: luminosity density. (a) the Schechter fit integrated above 10^41.6 erg/s must give the log rho_L(41.6) of Table 5 (a check of the Schechter form and units used to compare the points);
    # (b) the points and the fit, summed over the same bins (bin width = 2 x the printed half width), give the same luminosity density
    grid = np.linspace(41.6, 46.0, 4401)
    rho_full = float(np.log10(np.trapezoid(10 ** (schechter_dex(grid, p, p["alpha"]) + grid), grid)))
    if zz == 0.4:  # the printed parameters of this epoch do not reproduce the printed log rho_L(41.6): 0.37 dex lower. Not used as a check here, and said in the record.
        assert abs((rho_full - p["logrho416"]) + 0.37) < 0.05, (zz, rho_full, p["logrho416"])
    else:
        assert abs(rho_full - p["logrho416"]) < 0.05, (zz, rho_full, p["logrho416"])
    width = np.array([2 * r["half"] for r in b])
    rho_pts = float(np.log10(np.sum(10 ** (y + x) * width)))
    rho_fit = float(np.log10(np.sum(10 ** (model + x) * width)))
    assert abs(rho_pts - rho_fit) < 0.15, (zz, rho_pts, rho_fit)
    rho = rho_pts
    checks[zz] = dict(sources=nsrc, emitters=sum(T3[zz]), rms_fit=round(rms, 3), mean_fit=round(float(np.mean(res)), 3), chi_rms=round(chi, 2), rho_points_on_bins=round(rho_pts, 2), rho_fit_on_bins=round(rho_fit, 2), rho_fit_above_41p6=round(rho_full, 2), rho_printed=p["logrho416"])
    pts = [{"x": round(r["logL"], 3), "y": round(r["phi"], 3), "yLow": round(r["phi"] - r["e_phi"], 3), "yHigh": round(r["phi"] + r["e_phi"], 3)} for r in b]
    zlo, zhi = Z_RANGE[zz]
    ap = "fixed 2 arcsec diameter aperture (about 16 kpc); 3 arcsec at z = 0.4 to cover the same physical area" if zz != 0.4 else "fixed 3 arcsec diameter aperture at z = 0.4 (about 16 kpc, the same physical area as 2 arcsec at higher redshift)"
    rho_note = (f"the same fit integrated above 10^41.6 erg/s gives log rho_L = {rho_full:.2f} against {p['logrho416']} printed in Table 5" if zz != 0.4 else
                f"at this epoch the printed Schechter parameters integrate to log rho_L(41.6) = {rho_full:.2f}, 0.37 dex below the {p['logrho416']} printed in Table 5, so that check is not used here (the paper does not say why; the points themselves agree with the printed fit)")
    notes_check = (f"Table 4 transcribed ({len(b)} bins, {nsrc} sources of {sum(T3[zz])} Halpha emitters in Table 3). Checks: the Table 5 Schechter fit (log L*={p['logLs']}, log phi*={p['logphis']}, alpha={p['alpha']}) "
                   f"reproduces the points to rms {chi:.2f} times the printed error (rms {rms:.2f} dex); {rho_note}; the points and the fit give the same luminosity density over the bins (log rho {rho_pts:.2f} and {rho_fit:.2f}).")
    records.append({
        "id": f"sobral13.hizels.elf.halpha.z{zz:g}", "source": "Sobral et al. 2013 (HiZELS)", "run": "H-alpha luminosity function, binned (Table 4, corrected phi)",
        "kind": "observation", "relation": "elf",
        "epoch": {"zRepresentative": zz, "zNominal": zz, "zMin": zlo, "zMax": zhi, "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "log10 H-alpha line luminosity, corrected for [NII] contamination and for dust extinction (A(Halpha) = 1 mag)", "xUnit": "log10(erg s^-1)",
                 "yDefinition": "log10 comoving number density of H-alpha emitters per dex of luminosity (the paper's phi corr: corrected for incompleteness and for the filter profile)", "yUnit": "log10(Mpc^-3 dex^-1)"},
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": pts},
        "scatter": None,
        "selection": {"population": "narrow-band selected H-alpha emitters (rest-frame EW(Halpha+[NII]) > 25 A), COSMOS and UDS fields",
                      "warning": "Luminosities carry a constant A(Halpha) = 1 mag for every galaxy and a statistical [NII] correction (median [NII]/(Halpha+[NII]) about 0.25), not a measurement per galaxy; the paper notes the bright end deviates from a Schechter function where AGN dominate, and the points are not AGN-corrected. Errors are Poisson plus 20 per cent of the completeness correction."},
        "definitions": {
            "line": "H-alpha (without [NII])",
            "dustCorrection": "intrinsic",
            "dustCorrectionMethod": "constant A(Halpha) = 1 mag applied to every galaxy",
            "densityFrame": "comoving",
            "apertureDefinition": ap,
            "cosmology": {"H0": 70, "Om": 0.3},
            "population": "narrow-band selected H-alpha emitters, EW(Halpha+[NII]) > 25 A rest frame (star-forming galaxies and AGN)",
        },
        "provenance": {"tier": "published-table", "citation": "Sobral et al. 2013, MNRAS 428, 1128 (arXiv:1202.3436), Table 4", "doi": "10.1093/mnras/sts096",
                       "url": "https://arxiv.org/abs/1202.3436", "retrieved": RETRIEVED, "sourceMember": TEX.name, "sourceArchiveSha256": ARCHIVE_SHA,
                       "quotes": {"line_and_dust": q_line, "nii": q_nii, "dust_constant": q_dust, "cosmology": q_cosmo, "aperture": [q_ap, q_ap2], "comoving": q_com, "selection": q_ew, "errors": q_err},
                       "definitionBasis": "densityFrame is stated as '(co-moving)' for the NB_H volume (z = 1.47) in the volume section; the other epochs' volumes are computed in the same paragraph in the same way (read, not stated)"},
        "calibration": "validation", "rankable": True,
        "notes": notes_check,
    })
assert len(records) == 4
for r in records:
    assert r["domain"]["xMin"] < r["domain"]["xMax"]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(js_numbers({"schemaVersion": "1.0.0", "records": records}), indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + ["check z=%g: %s" % (k, json.dumps(v)) for k, v in checks.items()]) + "\n")
for k, v in checks.items():
    print(k, v)
print("Wrote", len(records), "records to", OUT)
