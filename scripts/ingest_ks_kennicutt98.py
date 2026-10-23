"""Kennicutt 1998 (arXiv:astro-ph/9712213, ApJ 498, 541): global Schmidt law, Sigma_SFR = 2.5e-4 Sigma_gas^1.4 (eq. 4).
Transcribes the published fit, checks it against the paper's own Tables 1 and 2 (text extracted from the PostScript tables with ghostscript:
a bivariate (OLS bisector) fit of the tabulated points must reproduce the quoted slope within its stated error), and writes the record.
Fetches the source by arXiv id."""
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

ARXIV = "astro-ph/9712213"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "ks-kennicutt98.json"
QUOTES = Path(__file__).resolve().parent.parent / "data" / "quotes" / (OUT.stem + ".txt")   # the sentences used, verbatim, with file and line, and the numeric checks
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/vector_figure_src") / ARXIV.replace("/", "_")
RETRIEVED = "2026-10-18"
TEX = SRC / "text.tex"


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
log = []
FAILED = []


def quote(s, path=TEX):
    """Assert the whitespace-normalised quote occurs verbatim in the file; record file:line of its first character."""
    norm = lambda a: re.sub(r"\s+", " ", a).strip()
    flat, idx = "", []
    for n, l in enumerate(path.read_text(errors="replace").splitlines(), 1):
        flat += norm(l) + " "
        idx += [n] * (len(norm(l)) + 1)
    k = flat.find(norm(s))
    if k < 0:
        print("QUOTE NOT FOUND:", s[:100]); FAILED.append(s); return
    log.append(f"{path.name}:{idx[k]}: {norm(s)}")


# ---- the fit and the definitions it rests on ----
quote(r"{\Sigma_{SFR}} = {(2.5 \pm 0.7) \times 10^{-4}}~{{ ({{\Sigma_{gas}} \over {1~M_{\odot}~{\rm pc}^{-2}}})}^{1.4 \pm 0.15}}~ {{\rm M_{\odot}~yr^{-1}~kpc^{-2}}}")
quote(r"The disk-averaged SFRs and gas densities for the combined sample are well represented by a Schmidt law with index $N = 1.4 \pm 0.15$.")
quote(r"Figure 2 shows the relationship between the disk-averaged SFR and total gas density (atomic and molecular hydrogen) for the 61 normal spirals in our sample.")
quote(r"Consequently we have ignored the HI component and approximate the molecular mass as the total gas mass in the starburst region.")
quote(r"conversion factor:  $N(H_2) = 2.8 \times 10^{20}~I_{{\rm CO}}$~cm$^{-2}$~ (K~km~s$^{-1}$).")
quote(r"The lines are offset by a factor of 1.37 to include helium and heavy elements in the total gas mass.")
quote(r"The IMF used in this conversion is a Salpeter function ($dN(m)/dm = -2.35$) over $m = 0.1 - 100$ \msun.")
quote(r"The \halpha\ luminosities used in equation (2) were corrected for internal extinction by 1.1 mag (factor 2.8)")
quote(r"SFR~({\rm M_\odot~yr^{-1}}) = {{L(H\alpha)} \over {1.26 \times 10^{41} ~{\rm ergs~s^{-1}}}}")
quote(r"{ {SFR} \over {1~{\rm M_{\odot}~yr^{-1}}} } = { {L_{FIR}} \over {2.2 \times 10^{43}~ {\rm ergs~s^{-1}} } }")
quote(r"Adopting the mean luminosity for 10--100 Myr continuous bursts, solar abundances, the Salpeter IMF described earlier")
quote(r"Finally, the mean SFR surface density (units \msun~yr$^{-1}$~kpc$^{-2}$) was derived for each galaxy, by dividing the total SFR from equation (2) by the deprojected area within the corrected RC2 radius.")
quote(r"The SFRs and densities are averaged within the radii of the central molecular disks and starbursts, which have typical dimensions of order 1 kpc.")
quote(r"The mean molecular surface densities were then derived, averaged within the radius of the central molecular disk as determined from the CO maps.")
quote(r"This yields a best fitting index $N = 1.40 \pm 0.05$ (bivariate regression) or $N = 1.35 \pm 0.03$ (errors in SFRs only).")
quote(r"with a best fitting least squares slope $N = 1.40 \pm 0.13$ (bivariate regression)")

assert not FAILED, FAILED
# ---- parse Tables 1 and 2 (PostScript -> text via ghostscript); minus signs are lost in the extraction and are reconstructed as described ----
def table_text(name):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "t.txt"
        subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=txtwrite", f"-sOutputFile={out}", str(SRC / name)], check=True, capture_output=True)
        return out.read_text(errors="replace").replace("\r", "")


X, Y, kind = [], [], []
for l in table_text("table1.ps").split("\n"):
    m = re.match(r"\s*(\d{3,4})\s+(\d+\.\d+)\s+(.*)", re.sub(r"\s{2,}", "  ", l))
    if not m:
        continue
    v = [float(t) for t in re.findall(r"-?\d+\.\d+", m.group(3))]
    for i in range(len(v) - 3):
        # columns: log Sigma_HI, log Sigma_H2, log Sigma_gas, log Sigma_SFR (negative for every normal disk); the sign of a column lost in extraction is fixed by
        # requiring log Sigma_gas = log(10^HI + 10^H2) to 0.011 dex (the table's rounding)
        if any(abs(math.log10(10 ** (s1 * v[i]) + 10 ** (s2 * v[i + 1])) - v[i + 2]) < 0.011 for s1 in (1, -1) for s2 in (1, -1)):
            X.append(v[i + 2]); Y.append(-v[i + 3]); kind.append(0)
            break
n_disk = len(X)
x2 = []
for l in table_text("table2.ps").split("\n"):
    l = re.sub(r"\s{2,}", "  ", l.strip())
    m = re.match(r"^(?:NGC|IC|Arp|Mrk|UGC|VII|ZW|IR|Ma\S+)\s?[\w\+\-\.]*\s+(?:\d+(?:\.\d)?\s+)?(\d\.\d\d)\s+(\x00)?(\d\.\d\d)", l)
    if m and float(m.group(1)) > 2:
        x2.append(float(m.group(1)))
        X.append(float(m.group(1))); Y.append(-float(m.group(3)) if m.group(2) else float(m.group(3))); kind.append(1)
X, Y, kind = np.array(X), np.array(Y), np.array(kind)
assert n_disk >= 55 and kind.sum() >= 28, (n_disk, kind.sum())


def bisector(x, y):
    xm, ym = x.mean(), y.mean()
    sxx, syy, sxy = ((x - xm) ** 2).sum(), ((y - ym) ** 2).sum(), ((x - xm) * (y - ym)).sum()
    b1, b2 = sxy / sxx, syy / sxy
    b = (b1 * b2 - 1 + math.sqrt((1 + b1 ** 2) * (1 + b2 ** 2))) / (b1 + b2)
    return float(b), float(ym - b * xm)


N_ALL, A_ALL = bisector(X, Y)
N_SB, A_SB = bisector(X[kind == 1], Y[kind == 1])
SLOPE, INTERCEPT = 1.4, math.log10(2.5e-4)
resid = Y - (INTERCEPT + SLOPE * X)
assert abs(N_ALL - 1.40) <= 0.05, N_ALL  # quoted 1.40 +- 0.05 (bivariate regression, composite)
assert abs(N_SB - 1.40) <= 0.13, N_SB  # quoted 1.40 +- 0.13 (bivariate regression, starbursts)
assert abs(A_ALL - INTERCEPT) < 0.05 and abs(resid.mean()) < 0.05, (A_ALL, resid.mean())
xmin, xmax = round(float(X.min()), 2), round(float(X.max()), 2)
checks = [
    f"Tables 1-2 parsed: {n_disk} normal disks (log Sigma_gas, log Sigma_SFR) + {int(kind.sum())} starbursts (log Sigma_H2, log Sigma_SFR) ({len(X)} points)",
    f"OLS bisector, all points: slope {N_ALL:.3f}, intercept {A_ALL:.3f} (paper: N=1.40+-0.05; eq. 4 intercept log10(2.5e-4)={INTERCEPT:.3f}); starbursts only: slope {N_SB:.3f} (paper 1.40+-0.13)",
    f"eq. 4 minus tabulated log Sigma_SFR: mean {resid.mean():+.3f} dex, rms {resid.std():.3f} dex (disks {resid[kind == 0].mean():+.3f}, starbursts {resid[kind == 1].mean():+.3f})",
    f"x span of the tabulated points: log Sigma_gas = {xmin}..{xmax}",
]
print("\n".join(checks))

sha = hashlib.sha256(Path(str(SRC) + ".tar").read_bytes()).hexdigest() if Path(str(SRC) + ".tar").exists() else None
prov = {
    "tier": "published-fit", "citation": "Kennicutt 1998, ApJ 498, 541 (arXiv:astro-ph/9712213), eq. 4",
    "doi": "10.1086/305588", "url": "https://arxiv.org/abs/astro-ph/9712213", "retrieved": RETRIEVED, "sourceMember": "text.tex",
}
if sha:
    prov["sourceArchiveSha256"] = sha
rec = {
    "id": "kennicutt98.galaxies.ks.global-total-gas.eq4", "source": "Kennicutt 1998", "run": "global Schmidt law, normal disks + circumnuclear starbursts",
    "kind": "observation", "relation": "ks",
    "epoch": {"zRepresentative": 0, "zMin": 0, "zMax": 0, "mode": "observational-bin", "snapshot": None},
    "axes": {
        "xDefinition": "log10 disk-averaged gas surface density: HI+H2 for 61 normal spirals (mean within the RC2 radius), H2 only for 36 circumnuclear starbursts (mean within the central molecular disk, ~1 kpc); hydrogen only, constant N(H2)=2.8e20 Ico",
        "xUnit": "log10(Msun pc^-2)",
        "yDefinition": "log10 disk-averaged SFR surface density (Halpha for the normal disks, FIR for the starbursts; Salpeter IMF 0.1-100 Msun)",
        "yUnit": "log10(Msun yr^-1 kpc^-2)",
    },
    "domain": {"xMin": xmin, "xMax": xmax},
    "representation": {"type": "parametric", "equation": "Sigma_SFR = 2.5e-4 (Sigma_gas / 1 Msun pc^-2)^1.4 Msun yr^-1 kpc^-2, i.e. log Sigma_SFR = log10(2.5e-4) + 1.4 log Sigma_gas",
                       "expression": "Math.log10(2.5e-4)+1.4*x", "parameters": {"A": 2.5e-4, "AError": 0.7e-4, "N": 1.4, "NError": 0.15}},
    "scatter": {"value": 0.3, "unit": "dex", "meaning": "0.3 dex is the random error in SFRs and gas densities assumed by the paper for its formal fit errors; the dispersion of the composite sample about eq. 4 computed from Tables 1-2 is %.2f dex rms" % resid.std()},
    "selection": {"population": "61 normal spiral galaxies plus 36 infrared-selected circumnuclear starbursts (galaxy-integrated / disk-averaged points)",
                  "warning": "Total-gas Schmidt law of the combined sample: the gas is HI+H2 for the normal disks but H2 alone for the starbursts (HI ignored), the CO-to-H2 factor is constant, and the SFR indicator differs between the two samples (Halpha vs FIR). x range is the span of the points tabulated in the paper's Tables 1 and 2, computed by the ingest script from the PostScript tables (the paper states no validity range for eq. 4). Not a resolved (sub-kpc) relation; do not compare with patch-scale simulation KS laws without the areaScale caveat."},
    "definitions": {
        "gasDefinition": "HI+H2 (normal disks); H2 only (starbursts)",
        "areaScale": "galaxy-integrated: disk-averaged within the RC2 radius (normal disks), central molecular disk of ~1 kpc (starbursts)",
        "sfrIndicator": "Halpha extinction-corrected by 1.1 mag, L(Ha)/1.26e41 erg/s (normal disks); L_FIR/2.2e43 erg/s (starbursts)",
        "sfrTimescaleMyr": "heterogeneous",
        "imf": "salpeter55",
        "coConversion": "N(H2) = 2.8e20 Ico cm^-2 (K km/s)^-1, constant",
        "heliumIncluded": "no (hydrogen only; the paper offsets its efficiency lines by 1.37 'to include helium and heavy elements')",
        "population": "all",
    },
    "provenance": prov, "calibration": "validation", "rankable": True,
    "notes": "Equation (4) as published. " + " ".join(checks),
}
assert rec["domain"]["xMin"] < rec["domain"]["xMax"]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + checks) + "\n")
print("Wrote 1 record to", OUT)
