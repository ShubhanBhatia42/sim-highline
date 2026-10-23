"""Mannucci et al. 2010 (arXiv:1005.0006): fundamental metallicity relation projected on mu_0.32 = log M* - 0.32 log SFR.
Transcribes the published 4th-order polynomial (SDSS medians) and the redshift-independent linear/plateau relation, checks them against the
numbers the paper quotes and against its Table 1, and writes the records. Fetches the source by arXiv id."""
import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np

ARXIV = "1005.0006"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "fmr-mannucci10.json"
QUOTES = Path(__file__).resolve().parent.parent / "data" / "quotes" / (OUT.stem + ".txt")   # the sentences used, verbatim, with file and line, and the numeric checks
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/vector_figure_src") / ARXIV
RETRIEVED = "2026-10-18"
TEX = SRC / "fmr4.tex"
TAB = SRC / "sfrmedtab.tex"


def fetch(arxiv_id, dest):
    if dest.exists() and any(dest.iterdir()):
        return
    dest.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{arxiv_id}", headers={"User-Agent": "Mozilla/5.0"})
    blob = urllib.request.urlopen(req).read()
    Path(str(dest) + ".tar").write_bytes(blob)
    print("sha256 of source archive", hashlib.sha256(blob).hexdigest())
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(dest)


fetch(ARXIV, SRC)
text = TEX.read_text(errors="replace")
lines = text.splitlines()
log = []


def quote(s, path=TEX):
    """Assert the whitespace-normalised quote occurs verbatim in the file, record file:line (first line)."""
    t = path.read_text(errors="replace")
    norm = lambda a: re.sub(r"\s+", " ", a).strip()
    flat, idx = "", []
    for n, l in enumerate(t.splitlines(), 1):
        flat += norm(l) + " "
        idx += [n] * (len(norm(l)) + 1)
    k = flat.find(norm(s))
    assert k >= 0, ("quote not found", s)
    log.append(f"{path.name}:{idx[k]}: {norm(s)}")
    return idx[k]


# ---- the published relations (quoted verbatim) ----
quote(r"\mu_\alpha =\rm{log}(M_*)-\alpha~\rm{log(SFR)}")
quote(r"12+log(O/H) =  8.90  + 0.39x -0.20x^2 - 0.077x^3 +0.064x^4")
quote(r"where $x=\mu_{0.32}-10$.")
quote(r"12+log(O/H)=&8.90+0.47x  & ~\rm{if}~~ \mu_{0.32}<10.2 \\ &9.07        & ~\rm{if}~~ \mu_{0.32}>10.5 \\")
quote(r"metallicity of star-forming galaxies of any mass, any SFR and at any redshift up to z=2.5 follow the following relation:")
quote(r"The median of the resulting distribution cab be fitted by:")
# ---- sample / definitions (quoted) ----
quote(r"We selected emission-line galaxies with redshift between 0.07 and 0.30")
quote(r"with a correction factor of 1.06 to scale the masses down from a \cite{Kroupa01} to a \cite{Chabrier03} initial mass function (IMF).")
quote(r"SFRs inside the spectroscopic aperture were measured from the \ha\ emission line flux corrected for dust extinction as estimated from the Balmer decrement.")
quote(r"The conversion factor between \ha\ luminosity and SFR in \cite{Kennicutt98} was used, corrected to a \cite{Chabrier03} IMF.")
quote(r"Oxygen gas-phase abundances were measured from the emission line ratios as described in \cite{Nagao06} and \cite{Maiolino08}.")
quote(r"galaxy metallicity is then defined as the average of these two values.")
quote(r"Total stellar masses \mstar\  from \cite{Kauffmann03a} were used")
quote(r"The final galaxy sample contains 141825 galaxies.")
quote(r"The same quantity also cancels out any redshift evolution up to z$\sim$2.5")
quote(r"where $\alpha$ is a free parameter.")
quote(r"reduces to $\sim$0.05~dex")
quote(r"with $\alpha$=0.32,")
quote(r"The value of $\alpha$ that minimizes the scatter of median metallicities of SDSS galaxies around the relation")

# ---- evaluate / verify ----
X = lambda m: m - 10.0
poly = lambda mu: 8.90 + 0.39 * X(mu) - 0.20 * X(mu) ** 2 - 0.077 * X(mu) ** 3 + 0.064 * X(mu) ** 4
lin = lambda mu: 8.90 + 0.47 * X(mu)
# parse Table 1: header of M* bin centres, then triplets (median 12+log(O/H), error, N) per log SFR row
rows = [l for l in TAB.read_text().splitlines()]
hdr = [float(v) for v in re.findall(r"\d+\.\d+", rows[0])]
assert hdr[0] == 9.10 and hdr[-1] == 11.35 and len(hdr) == 16
cells = []
i = 2
while i < len(rows):
    if not rows[i].strip().startswith(("$-$", "$+$")):
        i += 1
        continue
    sfr = float(rows[i].split("&")[0].replace("$-$", "-").replace("$+$", "").strip())
    zs = [c.strip() for c in rows[i].split("&")[1:]]
    ns = [c.strip().replace("\\vspace{2pt}\\\\", "").replace("\\\\", "").strip() for c in rows[i + 2].split("&")[1:]]
    for k, (z, n) in enumerate(zip(zs, ns)):
        z = z.replace("\\\\", "").strip()
        if z:
            cells.append((hdr[k], sfr, float(z), int(n)))
    i += 3
assert len(cells) > 150, len(cells)
mu = np.array([m - 0.32 * s for m, s, z, n in cells])
Z = np.array([z for m, s, z, n in cells])
N = np.array([n for m, s, z, n in cells])
lo, hi = round(float(mu.min()), 2), round(float(mu.max()), 2)
# Table 1 cell (log M*=10.00, log SFR=-0.40): spot value for the log
res = np.array([poly(m) for m in mu]) - Z
rms = float(np.sqrt(np.average(res ** 2, weights=N)))
# Check 1 (quoted numbers): both branches give 8.90 at mu=10 and the polynomial approaches the quoted 9.07 plateau at mu>10.5
assert abs(poly(10.0) - 8.90) < 1e-12 and abs(lin(10.0) - 8.90) < 1e-12
plateau = [round(float(poly(m)), 2) for m in np.arange(10.7, 11.45, 0.1)]
assert round(poly(10.8), 2) == 9.07, poly(10.8)  # reproduces the quoted 9.07 to 3 significant digits
assert all(abs(p - 9.07) <= 0.02 for p in plateau), plateau  # the quartic keeps rising slowly (9.09 at 11.4); the paper's own plateau is the constant 9.07
# Check 2 (Table 1): count-weighted rms residual of the polynomial against the 16x16 median cells
assert rms < 0.03, rms
low_cells = (mu < 10.2) & (N > 200)
slope_low = float(np.polyfit(mu[low_cells], Z[low_cells], 1)[0])
sel_lo, sel_hi = mu < 10.2, mu > 10.5
rms_lin = float(np.sqrt(np.average((np.array([lin(m) for m in mu[sel_lo]]) - Z[sel_lo]) ** 2, weights=N[sel_lo])))
mean_hi = float(np.average(Z[sel_hi], weights=N[sel_hi]))
assert abs(mean_hi - 9.07) < 0.015, mean_hi  # N-weighted mean of the Table 1 cells with mu_0.32>10.5 agrees with the quoted plateau to 0.012 dex (not to 3 significant digits)
assert rms_lin < 0.06, rms_lin
check_lines = [
    f"poly(10)={poly(10.0):.3f} (quoted constant term 8.90); poly(10.8)={poly(10.8):.4f} -> {round(poly(10.8),2)} vs quoted plateau 9.07; poly over 10.7-11.4 in 0.1 steps = {plateau}",
    f"Table 1: {len(cells)} median cells, mu_0.32 span {lo}..{hi}, N-weighted rms of polynomial minus cell median = {rms:.4f} dex",
    f"Table 1 cells with mu<10.2 and N>200: least-squares slope dZ/dmu = {slope_low:.3f} (the paper's linear branch, 0.47, was fitted to the SDSS plus high-z samples, so the SDSS-only slope is not expected to equal it); N-weighted rms of 8.90+0.47x minus the Table 1 cell medians with mu<10.2 = {rms_lin:.3f} dex",
    f"Table 1 cells with mu>10.5 ({int(sel_hi.sum())} cells): N-weighted mean median-metallicity = {mean_hi:.4f} vs quoted 9.07 (agreement to 0.015 dex only; the plateau value is a rounded fit parameter)",
]
print("\n".join(check_lines))

sha = hashlib.sha256(Path(str(SRC) + ".tar").read_bytes()).hexdigest() if Path(str(SRC) + ".tar").exists() else None

common_def = {
    "muAlpha": 0.32,
    "metallicityQuantity": "gas-O/H",
    "metallicityCalibration": "Nagao+06 / Maiolino+08 strong-line calibrations (average of N2 and R23 metallicities)",
    "sfrTimescaleMyr": "unspecified",
    "sfrIndicator": "Halpha (3 arcsec fibre, Balmer-decrement dust correction, Kennicutt 1998 conversion)",
    "imf": "chabrier03",
    "massDefinition": "sed-total",
    "population": "star-forming",
}
axes = {
    "xDefinition": "mu_0.32 = log10(M*/Msun) - 0.32 log10(SFR/(Msun/yr)); total stellar mass (Kauffmann+03, scaled 1.06 from Kroupa to Chabrier), SFR from fibre Halpha",
    "xUnit": "log10(Msun)",
    "yDefinition": "12+log10(O/H), gas-phase oxygen abundance (Nagao+06, Maiolino+08 strong-line calibration)",
    "yUnit": "dex",
}
prov = {
    "tier": "published-fit",
    "citation": "Mannucci et al. 2010, MNRAS 408, 2115 (arXiv:1005.0006)",
    "doi": "10.1111/j.1365-2966.2010.17291.x",
    "url": "https://arxiv.org/abs/1005.0006",
    "retrieved": RETRIEVED,
    "sourceMember": "fmr4.tex",
}
if sha:
    prov["sourceArchiveSha256"] = sha


def rec(rid, run, expr, equation, domain, epoch, selection, notes, extra_def=None, scatter=None):
    return {
        "id": rid, "source": "Mannucci et al. 2010", "run": run, "kind": "observation", "relation": "fmr",
        "epoch": epoch, "axes": axes, "domain": {"xMin": domain[0], "xMax": domain[1]},
        "representation": {"type": "parametric", "equation": equation, "expression": expr, "parameters": {}},
        "scatter": scatter, "selection": selection, "definitions": {**common_def, **(extra_def or {})},
        "provenance": prov, "calibration": "validation", "rankable": True, "notes": notes,
    }


epoch_sdss = {"zRepresentative": 0.185, "zMin": 0.07, "zMax": 0.30, "mode": "observational-bin", "snapshot": None}
epoch_all = {"zRepresentative": 0.07, "zMin": 0.07, "zMax": 2.5, "mode": "analytic-evolution", "snapshot": None}
records = [
    rec("mannucci10.sdss.fmr.mu0.32.poly4", "SDSS median polynomial",
        "8.90+0.39*(x-10)-0.20*Math.pow(x-10,2)-0.077*Math.pow(x-10,3)+0.064*Math.pow(x-10,4)",
        "12+log(O/H) = 8.90 + 0.39x - 0.20x^2 - 0.077x^3 + 0.064x^4, x = mu_0.32 - 10",
        (lo, hi), epoch_sdss,
        {"population": "SDSS DR7 emission-line galaxies, AGN removed (BPT), H-alpha S/N>25, 0.07<z<0.30; fit to the median metallicity in mu_0.32",
         "warning": f"Fit to the medians of SDSS galaxies in mu_0.32. x range is the span of mu_0.32 over the cells of the paper's Table 1 (computed from bin centres, not stated by the paper). zRepresentative 0.185 is the midpoint of the 0.07-0.30 selection window, not a measured median. The paper's 3 arcsec fibre SFRs are not aperture corrected."},
        "Polynomial as published (eq. 'cfr2', first). " + check_lines[0] + ". " + check_lines[1] + ".",
        scatter={"value": 0.05, "unit": "dex", "meaning": "residual dispersion of individual SDSS galaxies around the 3D FMR in the central part, as stated for the FMR (not for this projection)"}),
    rec("mannucci10.sdss-highz.fmr.mu0.32.linear-lowmu", "linear branch mu<10.2",
        "8.90+0.47*(x-10)",
        "12+log(O/H) = 8.90 + 0.47x, x = mu_0.32 - 10, valid for mu_0.32 < 10.2",
        (lo, 10.2), epoch_all,
        {"population": "star-forming galaxies of any mass and SFR, SDSS plus the z=0.5-2.5 literature samples compiled in the paper",
         "warning": "Published as the relation followed 'at any redshift up to z=2.5'; the paper gives no relation for 10.2<mu_0.32<10.5. Evolution is stored as analytic-evolution with zRepresentative = zMin because the expression has no redshift dependence."},
        "Linear branch as published. " + check_lines[2],
        extra_def={"population": "star-forming"}),
    rec("mannucci10.sdss-highz.fmr.mu0.32.plateau", "plateau branch mu>10.5",
        "9.07",
        "12+log(O/H) = 9.07, valid for mu_0.32 > 10.5",
        (10.5, hi), epoch_all,
        {"population": "star-forming galaxies of any mass and SFR, SDSS plus the z=0.5-2.5 literature samples compiled in the paper",
         "warning": "Constant branch of the same published relation; see the linear-lowmu record. Upper x limit is the span of mu_0.32 over the cells of the paper's Table 1."},
        "Plateau as published. " + check_lines[3] + "; the SDSS polynomial evaluates to " + str(round(float(poly(10.8)), 2)) + " at mu_0.32=10.8."),
]
for r in records:
    assert r["epoch"]["zMin"] <= r["epoch"]["zRepresentative"] <= r["epoch"]["zMax"]
    assert r["domain"]["xMin"] < r["domain"]["xMax"]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + check_lines) + "\n")
print("Wrote", len(records), "records to", OUT)
