"""Curti et al. 2020 (arXiv:1910.00597, MNRAS 491, 944): projections of the FMR on mu_alpha = log M* - alpha log SFR (Appendix A, Table of
'best fit parameters for the 2D projections of the FMR on the Z-mu_alpha plane'), functional form of their MZR with mu_alpha in place of M*.
The main FMR of the paper (eq. 'FMR', Z(M*, SFR) with SFR-dependent turnover mass) is a function of SFR, not of mu, and is NOT stored here.
Each transcribed expression is compared with the best-fit curve drawn in the paper's vector figures (calibrated on the labelled ticks). Fetches the source by arXiv id."""
import hashlib
import io
import json
import math
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402  (repository helper; falls back to the repository copy when run from the staging area)

ARXIV = "1910.00597"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "fmr-curti20.json"
QUOTES = Path(__file__).resolve().parent.parent / "data" / "quotes" / (OUT.stem + ".txt")   # the sentences used, verbatim, with file and line, and the numeric checks
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/vector_figure_src") / ARXIV
RETRIEVED = "2026-10-18"
TEX = SRC / "fmr_new_paper.tex"


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
log, FAILED = [], []


def quote(s, path=TEX):
    norm = lambda a: re.sub(r"\s+", " ", a).strip()
    flat, idx = "", []
    for n, l in enumerate(path.read_text(errors="replace").splitlines(), 1):
        flat += norm(l) + " "
        idx += [n] * (len(norm(l)) + 1)
    k = flat.find(norm(s))
    if k < 0:
        print("QUOTE NOT FOUND:", s[:100]); FAILED.append(s); return
    log.append(f"{path.name}:{idx[k]}: {norm(s)}")


quote(r"\text{12 + log(O/H)} = \text{Z}_{0}  - \gamma/\beta * \text{log}\bigg(1 + \bigg(\frac{\text{M}}{\text{M}_{0}} \bigg)^{-\beta} \bigg)\ .")
quote(r"Following \cite{Mannucci:2010aa}, we search for the 2D-projection of the FMR that reduce the metallicity scatter around the relation Z- $\mu_{\alpha}$, where $\mu_{\alpha} = \text{log}(M_{\star}) - \alpha\ \text{log}(\text{SFR})$.")
quote(r"We fit our M-SFR bins (we here consider total-SFR only) against log(O/H) according to the same functional form used for the MZR (i.e. Eq.~\ref{eq:mzr}), where the x-variable is now $\mu_{\alpha}$")
quote(r"\text{Global Sample} &  0.55 $\pm$ 0.01 & 8.780     $\pm$ 0.004 & 10.14    $\pm$ 0.03 & 0.30      $\pm$ 0.01 & 2.4  $\pm$ 0.4 \\")
quote(r"\text{sSFR}$< 10^{-9.5}$ Gyr$^{-1}$  & 0.22 $\pm$ 0.02 & 8.796     $\pm$ 0.005 & 10.1    $\pm$ 0.1 & 0.25      $\pm$ 0.03 & 1.1      $\pm$ 0.2 \\")
quote(r"\text{sSFR}$> 10^{-9.5}$ Gyr$^{-1}$  & 0.65 $\pm$ 0.01 & 8.74     $\pm$ 0.04 & 9.9    $\pm$ 0.1 & 0.32   $\pm$ 0.01 & 5.0   $\pm$ 3.0 \\")
quote(r"we can divide our total sample into two subset of galaxies, the ``high sSFR'' sample (log(sSFR)$>-9.5$) and the ``low sSFR'' sample (log(sSFR)$<-9.5$) respectively")
quote(r"The Z-SFR dependence is weaker ($\alpha = 0.22$)")
quote(r"The Z-SFR dependence is tighter ($\alpha = 0.65$)")
quote(r"We obtain a best-fit $\upalpha$ value of $0.55$")
quote(r"\caption{Best fit parameters for the 2D projections of the FMR on the Z-$\mu_{\alpha}$ plane, for different SFR regimes. }")
quote(r"We applied a redshift selection of $\text{z}>0.027$ to ensure the presence of the [\ion{O}{ii}]$\lambda3727$ emission line")
quote(r"We required galaxies to be classified as star forming, according to their position on the {[\ion{N}{ii}]-BPT diagram and following the classification scheme by \cite{Kauffmann:2003aa}.")
quote(r"The stellar masses for our sample are provided by the MPA/JHU catalog and have been estimated from fits to the photometry")
quote(r"Star formation rates used in this work are derived from the extinction corrected H$\upalpha$ luminosity inside the fibre, adopting the calibration proposed by \cite{Kennicutt:2012aa}.")
quote(r"We then apply the aperture corrections provided by the MPA/JHU catalog")
quote(r"to compute the total SFR for our galaxies.")
quote(r"Both stellar masses and SFRs estimates are re-scaled to a common \cite{Chabrier:2003aa} IMF.")
quote(r"assuming the calibrations presented in \cite{Curti:2017aa} which are consistently defined on the T$_{\text{e}}$-based abundance scale over the entire metallicity range spanned by SDSS galaxies.")
quote(r"the total analysed sample is reduced to $153,452$ galaxies.")
assert not FAILED, FAILED

# transcribed table rows: (id, run, alpha, Z0, mu0, gamma, beta, population, figure, errors)
ROWS = [
    ("curti20.sdss.fmr.mu0.55.global", "global sample, alpha=0.55", 0.55, 8.780, 10.14, 0.30, 2.4, "all star-forming SDSS galaxies", "fmr_proj_final_MCMC.pdf", (0.004, 0.03, 0.01, 0.4), 0.005),
    ("curti20.sdss.fmr.mu0.22.low-ssfr", "sSFR < 10^-9.5 yr^-1, alpha=0.22", 0.22, 8.796, 10.1, 0.25, 1.1, "star-forming SDSS galaxies with log sSFR < -9.5 (yr^-1)", "fmr_proj_lowfinal_MCMC.pdf", (0.005, 0.1, 0.03, 0.2), 0.02),
    ("curti20.sdss.fmr.mu0.65.high-ssfr", "sSFR > 10^-9.5 yr^-1, alpha=0.65", 0.65, 8.74, 9.9, 0.32, 5.0, "star-forming SDSS galaxies with log sSFR > -9.5 (yr^-1)", "fmr_proj_highfinal_MCMC.pdf", (0.04, 0.1, 0.01, 3.0), 0.02),
]
tar = Path(str(SRC) + ".tar")
records, checks = [], []
for rid, run, alpha, Z0, mu0, gam, beta, pop, figname, errs, tol in ROWS:
    f = lambda x: Z0 - gam / beta * math.log10(1 + 10 ** (-beta * (x - mu0)))
    # drawn best-fit curve: the black 2.5 pt stroke of 49 segments in the main panel; axes calibrated on the numeric tick labels of the figure
    pdf = SRC / "figures" / figname
    page = vf.page_of(pdf)
    frame = max(vf.frames(page), key=lambda r: r.width * r.height)
    fx, xt = vf.axis_fit(page, frame, "x")
    fy, yt = vf.axis_fit(page, frame, "y")
    assert len(xt) >= 5 and len(yt) >= 5
    # the label of the x axis carries the alpha used in this panel
    assert any(w[4] == f"{alpha:.2f}" and w[1] > 440 for w in page.get_text("words")), ("alpha label", alpha)
    strokes = [d for d in page.get_drawings() if d["type"] == "s" and d["color"] and max(d["color"]) < 0.1 and abs((d.get("width") or 0) - 2.5) < 0.01 and len(d["items"]) >= 40]
    assert len(strokes) == 1, len(strokes)
    d = strokes[0]
    pts = [d["items"][0][1]] + [it[-1] for it in d["items"]]
    curve = [(fx(p.x), fy(p.y)) for p in pts]
    diff = [f(x) - y for x, y in curve]
    mx = max(abs(v) for v in diff)
    assert mx < tol, (rid, mx)
    xlo, xhi = round(curve[0][0], 2), round(curve[-1][0], 2)
    assert xlo < xhi
    checks.append(f"{rid}: drawn best-fit curve ({len(curve)} vertices, x {xlo}..{xhi}) minus transcribed expression: max |diff| = {mx:.4f} dex (rms {math.sqrt(sum(v * v for v in diff) / len(diff)):.4f}); ends: drawn {curve[0][1]:.3f},{curve[-1][1]:.3f} vs expression {f(curve[0][0]):.3f},{f(curve[-1][0]):.3f}")
    prov = {"tier": "published-fit", "citation": "Curti et al. 2020, MNRAS 491, 944 (arXiv:1910.00597), Appendix A and its table of 2D projections of the FMR",
            "doi": "10.1093/mnras/stz2910", "url": "https://arxiv.org/abs/1910.00597", "retrieved": RETRIEVED, "sourceMember": "fmr_new_paper.tex",
            "figureMember": f"figures/{figname}", "figureSha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}
    if tar.exists():
        prov["sourceArchiveSha256"] = hashlib.sha256(tar.read_bytes()).hexdigest()
    records.append({
        "id": rid, "source": "Curti et al. 2020", "run": run, "kind": "observation", "relation": "fmr",
        "epoch": {"zRepresentative": 0.027, "zMin": 0.027, "zMax": 0.027, "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": f"mu_{alpha} = log10(M*/Msun) - {alpha} log10(SFR/(Msun/yr)); MPA-JHU total stellar mass, total (aperture-corrected) Halpha SFR",
                 "xUnit": "log10(Msun)", "yDefinition": "12+log10(O/H), gas-phase, Te-anchored strong-line calibrations (Curti+17), median of M*-SFR bins", "yUnit": "dex"},
        "domain": {"xMin": xlo, "xMax": xhi},
        "representation": {"type": "parametric",
                           "equation": f"12+log(O/H) = Z0 - (gamma/beta) log10(1 + (10^mu / 10^mu0)^-beta), mu = mu_{alpha}; Z0={Z0}, mu0={mu0}, gamma={gam}, beta={beta}",
                           "expression": "Z0-(gamma/beta)*Math.log10(1+Math.pow(10,-beta*(x-mu0)))",
                           "parameters": {"Z0": Z0, "mu0": mu0, "gamma": gam, "beta": beta, "Z0Error": errs[0], "mu0Error": errs[1], "gammaError": errs[2], "betaError": errs[3]}},
        "scatter": None,
        "selection": {"population": pop + " (SDSS DR7 MPA-JHU, BPT star-forming, z>0.027)",
                      "warning": "Fit to median metallicities in M*-SFR bins using the MZR functional form with mu_alpha in place of M*. The paper's main FMR is Z(M*, SFR) and is not stored. x range = extent of the best-fit curve drawn in the paper's figure (not stated in the text). The redshift upper limit of the sample is not stated in this paper, so the epoch block carries only the stated lower limit z>0.027. The paper's table labels the sSFR split in Gyr^-1 while its text and caption use yr^-1 (log sSFR = -9.5): the text and caption were followed."},
        "definitions": {"muAlpha": alpha, "metallicityQuantity": "gas-O/H", "metallicityCalibration": "Te-anchored-strong-line (Curti+17)",
                        "sfrTimescaleMyr": "unspecified", "sfrIndicator": "Halpha extinction-corrected in the fibre (Kennicutt & Evans 2012 calibration), MPA-JHU aperture corrections to total SFR",
                        "imf": "chabrier03", "massDefinition": "sed-total", "population": "star-forming"},
        "provenance": prov, "calibration": "validation", "rankable": True,
        "notes": "Parameters as published (Appendix A table). " + checks[-1],
    })
print("\n".join(checks))
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + checks) + "\n")
print("Wrote", len(records), "records to", OUT)
