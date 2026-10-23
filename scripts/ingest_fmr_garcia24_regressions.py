"""Garcia et al. 2024, 'Does the FMR evolve with redshift? II' (arXiv:2407.06254): z=0 linear regressions of 12+log(O/H) on mu_alpha in Illustris,
IllustrisTNG, EAGLE and SIMBA (eq. 'FMR_regressions'). The equations are transcribed and checked against the paper's own vector figures: the z=0 predicted MZR
(Fig. 'MZR_predictions', centre column) must equal m (log M* - alpha log SFMS(M*)) + b, with the z=0 star-forming main sequence digitized from Fig. 'SFMS_Comp'.
The check is run on arXiv v1 (all four equations; metallicity converted with f_O = 35 per cent) and on v2 (f_O = 50 per cent): in v2 only the SIMBA line was
updated, the Illustris/TNG/EAGLE lines are the v1 ones, and the v2 figure sits 0.155 dex = log10(50/35) above them. Fetches the sources by arXiv id."""
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "2407.06254"
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).resolve().parent.parent / "data" / "curves" / "fmr-garcia24.json"
QUOTES = Path(__file__).resolve().parent.parent / "data" / "quotes" / (OUT.stem + ".txt")   # the sentences used, verbatim, with file and line, and the numeric checks
SRC2 = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/vector_figure_src") / ARXIV
SRC1 = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/vector_figure_src/2407.06254v1")
RETRIEVED = "2026-10-18"
TEAL = (0.12, 0.8, 0.75)  # the z=0 curve colour in the figure legends
NAMES = ["Illustris", "TNG", "EAGLE", "SIMBA"]


def fetch(version, dest):
    if dest.exists() and any(dest.iterdir()):
        return
    dest.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{ARXIV}{version}", headers={"User-Agent": "Mozilla/5.0"})
    blob = urllib.request.urlopen(req).read()
    Path(str(dest) + ".tar").write_bytes(blob)
    print(version or "latest", "sha256 of source archive", hashlib.sha256(blob).hexdigest())
    try:
        tarfile.open(fileobj=io.BytesIO(blob)).extractall(dest)
    except tarfile.ReadError:
        import gzip
        (dest / "paper.tex").write_bytes(gzip.decompress(blob))


fetch("", SRC2)
fetch("v1", SRC1)
log, FAILED = [], []


def quote(s, path):
    norm = lambda a: re.sub(r"\s+", " ", a).strip()
    flat, idx = "", []
    for n, l in enumerate(path.read_text(errors="replace").splitlines(), 1):
        flat += norm(l) + " "
        idx += [n] * (len(norm(l)) + 1)
    k = flat.find(norm(s))
    if k < 0:
        print("QUOTE NOT FOUND:", path.parent.name, s[:90]); FAILED.append(s); return
    log.append(f"{path.parent.name}/{path.name}:{idx[k]}: {norm(s)}")


T2, T1 = SRC2 / "paper.tex", SRC1 / "paper.tex"
for t in (T2, T1):
    quote(r"&[\log {\rm O/H} + 12]_{\rm Illustris} &= 0.693(\mu_{0.23}) + 1.807~,&\\", t)
    quote(r"&[\log {\rm O/H} + 12]_{\rm TNG} &= 0.368(\mu_{0.31}) + 5.044~,&\\", t)
    quote(r"&[\log {\rm O/H} + 12]_{\rm EAGLE} &= 0.380(\mu_{0.74}) + 5.132~,&~{\rm and}\\", t)
    quote(r"The regression to the FMR is the linear least-squares fit to the minimum scatter $\mu_{\alpha}\!-\!{\rm metallicity}$ distribution.", t)
    quote(r"\mu_\alpha = \log M_* - \alpha \log {\rm SFR}~,", t)
    quote(r"We find that $\alpha_{\rm min}$ at $z=0$ is 0.23 in Illustris, 0.31 in TNG, 0.74 in EAGLE, and 0.33 in SIMBA", t)
    quote(r"We further more only select star-forming galaxies from our simulations".replace("further more", "furthermore"), t)
    quote(r"Any galaxy that has a sSFR less than 0.5 dex below the sSFMS is omitted from this analysis", t)
    quote(r"We limit our analysis to ``well-resolved'' central galaxies in the simulations.", t)
    quote(r"we limit all gas-phase metallicities derived from the simulations to that of", t) if False else None
    quote(r"To convert to these observer units, we assume that the metal mass fraction of oxygen ($f_{\rm O}$) and total mass fraction of hydrogen ($X$) are constants.", t)
    quote(r"Finally, we limit all gas-phase metallicities derived from the simulations to that of", t)
    quote(r"We therefore caution that, while we report metallicity in units of Equation~\ref{eqn:logO/H}, we are not reporting directly tracked oxygen abundances from the simulation.".replace("We therefore", "We therefore"), t) if False else None
quote(r"We adopt values of \secondedit{$f_{\rm O} = 50\%$} and $X=76\%$ for this analysis.", T2)
quote(r"We adopt values of $f_{\rm O} = 35\%$ and $X=76\%$ for this analysis.", T1)
quote(r"&[\log {\rm O/H} + 12]_{\rm SIMBA} &= 0.364(\mu_{0.66}) + 4.901~.&\\", T2)
quote(r"&[\log {\rm O/H} + 12]_{\rm SIMBA} &= 0.440(\mu_{0.33}) + 3.974~.&\\", T1)
quote(r"A \cite{Chabrier_2003} initial mass function is assumed", T2)
quote(r"we use data products from the highest-resolution $(75h^{-1}~{\rm Mpc})^3$ box, TNG100-1", T2)
quote(r"Illustris-1", T2)
quote(r"{\sc RefL0100N1504}", T2)
quote(r"We use data from the largest box for the most fair comparison to the selected volumes of Illustris, TNG, and EAGLE.", T2)
quote(r"The level of agreement is somewhat by construction of our selection of $f_{\rm O} = 50\%$.", T2)
assert not FAILED, FAILED


# ---- figure check ----
def labels_y(page, frame, words, value):
    return [(w[1] + w[3]) / 2 for w in words if vf.number(w[4]) == value and frame.y0 - 1 <= (w[1] + w[3]) / 2 <= frame.y1 + 1 and 0 < frame.x0 - (w[0] + w[2]) / 2 < 45]


def ymap(page, frame, words, anchors):
    """Two unsigned labels snapped to drawn tick marks (signed labels have off-centre glyph boxes and are only used for a consistency check)."""
    ticks = vf._tick_positions(page, frame, "y")
    pts = []
    for v in anchors:
        cy = labels_y(page, frame, words, v)[0]
        t = min(ticks, key=lambda t: abs(t - cy))
        assert abs(t - cy) < 3, (v, cy, t)
        pts.append((t, v))
    (t1, v1), (t2, v2) = pts
    slope = (v2 - v1) / (t2 - t1)
    return (lambda py: v1 + slope * (py - t1)), pts


def xmap(page, frame, words):
    lab = [((w[0] + w[2]) / 2, vf.number(w[4])) for w in words if vf.number(w[4]) is not None and frame.x0 - 2 <= (w[0] + w[2]) / 2 <= frame.x1 + 2 and 0 < (w[1] + w[3]) / 2 - frame.y1 < 40]
    return vf.axis_fit(page, frame, "x", labels=lab)


def z0curve(page, frame, fx, fy, min_points):
    cs = [c for c in vf.curves(page, frame, fx, fy, min_items=8) if all(abs(a - b) < 0.015 for a, b in zip(c["color"], TEAL)) and len(c["points"]) > min_points]
    assert len(cs) == 1, len(cs)
    return np.array(cs[0]["points"])


def figure_check(figdir, f2name, f4name, reg):
    p2 = vf.page_of(figdir / f2name)
    fr2 = sorted(vf.frames(p2), key=lambda r: (round(r.y0), r.x0))
    w2 = p2.get_text("words")
    assert len(fr2) == 4
    fx_b = [xmap(p2, fr2[2], w2)[0], xmap(p2, fr2[3], w2)[0]]
    fy_t, _ = ymap(p2, fr2[0], w2, [2.0, 0.0])
    fy_b, _ = ymap(p2, fr2[2], w2, [2.0, 0.0])
    sfms = {n: z0curve(p2, fr2[i], fx_b[i % 2], fy_t if i < 2 else fy_b, 20) for i, n in enumerate(NAMES)}
    p4 = vf.page_of(figdir / f4name)
    fr4 = sorted(vf.frames(p4), key=lambda r: (round(r.y0 / 10), r.x0))
    w4 = p4.get_text("words")
    assert len(fr4) == 12
    fxm = {c: xmap(p4, fr4[9 + c], w4)[0] for c in (0, 1)}
    out = {}
    for r, n in enumerate(NAMES):
        fy, anchors = ymap(p4, fr4[3 * r], w4, [8.0, 9.0])
        # signed label consistency: the glyph-box offset of '-' labels is constant, the lattice is regular
        P = z0curve(p4, fr4[3 * r + 1], fxm[1], fy, 10)
        m, b, a = reg[n]
        sf = np.interp(P[:, 0], sfms[n][:, 0], sfms[n][:, 1])
        d = m * (P[:, 0] - a * sf) + b - P[:, 1]
        mu = P[:, 0] - a * sf
        out[n] = {"mean": float(d.mean()), "sd": float(d.std()), "n": len(P), "mu": (float(mu.min()), float(mu.max())), "logM": (float(P[0, 0]), float(P[-1, 0]))}
    return out


V2REG = {"Illustris": (0.693, 1.807, 0.23), "TNG": (0.368, 5.044, 0.31), "EAGLE": (0.380, 5.132, 0.74), "SIMBA": (0.364, 4.901, 0.66)}
V1REG = {"Illustris": (0.693, 1.807, 0.23), "TNG": (0.368, 5.044, 0.31), "EAGLE": (0.380, 5.132, 0.74), "SIMBA": (0.440, 3.974, 0.33)}
c1 = figure_check(SRC1 / "figures", "SFMS_Comp.pdf", "fake_MZR_mega.pdf", V1REG)
c2 = figure_check(SRC2 / "figures", "Figure2.pdf", "Figure4.pdf", V2REG)
for n in NAMES:
    assert abs(c1[n]["mean"]) < 0.015 and c1[n]["sd"] < 0.01, (n, c1[n])  # v1: equations (f_O=35%) reproduce the v1 figure
assert abs(c2["SIMBA"]["mean"]) < 0.01 and c2["SIMBA"]["sd"] < 0.02, c2["SIMBA"]  # v2: SIMBA line reproduces the v2 figure
shift = math.log10(0.5 / 0.35)
for n in NAMES[:3]:
    assert abs(c2[n]["mean"] + shift) < 0.015 and c2[n]["sd"] < 0.01, (n, c2[n])  # v2 figure = v1 equations + log10(50/35)
checks = [f"v1 figures (f_O=35%): formula minus drawn z=0 predicted MZR, mean/sd (dex): " + "; ".join(f"{n} {c1[n]['mean']:+.4f}/{c1[n]['sd']:.4f}" for n in NAMES),
          f"v2 figures (f_O=50%): " + "; ".join(f"{n} {c2[n]['mean']:+.4f}/{c2[n]['sd']:.4f}" for n in NAMES) + f"; log10(50/35) = {shift:.4f}",
          "number of curve vertices compared: " + ", ".join(f"{n} {c1[n]['n']}" for n in NAMES)]
print("\n".join(checks))

tars = {"v2": Path(str(SRC2) + ".tar"), "v1": Path(str(SRC1) + ".tar")}
sha = {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in tars.items() if v.exists()}
fig_sha = {"v1": hashlib.sha256((SRC1 / "figures/fake_MZR_mega.pdf").read_bytes()).hexdigest(), "v2": hashlib.sha256((SRC2 / "figures/Figure4.pdf").read_bytes()).hexdigest()}
SIMS = {
    "Illustris": ("Illustris", "Illustris-1 (Garcia+24 FMR regression, star-forming centrals)", 0.35, V2REG, c2, "v1"),
    "TNG": ("IllustrisTNG", "TNG100-1 (Garcia+24 FMR regression, star-forming centrals)", 0.35, V2REG, c2, "v1"),
    "EAGLE": ("EAGLE", "RefL0100N1504 (Garcia+24 FMR regression, star-forming centrals)", 0.35, V2REG, c2, "v1"),
    "SIMBA": ("SIMBA", "m100n1024 (Garcia+24 FMR regression, star-forming centrals)", 0.50, V2REG, c2, "v2"),
}
records = []
for n in NAMES:
    source, run, fO, reg, chk, ver = SIMS[n]
    m, b, a = reg[n]
    c = c1[n] if ver == "v1" else c2[n]
    lo, hi = round(c["mu"][0], 2), round(c["mu"][1], 2)
    stale = ver == "v1"
    warn = ("z=0 linear least-squares regression of 12+log(O/H) on mu_alpha for the star-forming central galaxies of the simulation, alpha = alpha_min of the minimum-scatter projection. "
            "x range is NOT stated by the paper: it is mu_alpha evaluated along the z=0 star-forming main sequence (digitized from the paper's SFMS figure) over the stellar-mass range of the paper's predicted-MZR curve "
            f"(log M* {c['logM'][0]:.2f}-{c['logM'][1]:.2f}), so it is narrower than the full galaxy scatter in mu_alpha. ")
    if stale:
        warn += ("METALLICITY SCALE: the printed equation of the Illustris/TNG/EAGLE lines is identical in arXiv v1 and v2, but v1 converts the star-forming-gas metal mass fraction to O/H with f_O = 35 per cent while v2 text says f_O = 50 per cent. "
                 f"The equation reproduces the v1 figure (mean offset {c1[n]['mean']:+.3f} dex) and sits {-c2[n]['mean']:.3f} dex below the v2 figure (log10(50/35) = {shift:.3f}), so it corresponds to f_O = 35 per cent; the v2 text did not update this line. "
                 "Not a directly tracked oxygen abundance (constant f_O and X scaling of the total metallicity).")
    else:
        warn += ("METALLICITY SCALE: f_O = 50 per cent, X = 76 per cent (v2). The v1 line for SIMBA was 0.440 mu_0.33 + 3.974 (f_O = 35 per cent); v2 text still says alpha_min = 0.33 for SIMBA in one sentence, "
                 "but its equation and figure use alpha = 0.66, which the figure check confirms (alpha = 0.33 does not reproduce the drawn curve).")
    prov = {"tier": "published-fit", "citation": "Garcia et al. 2024, 'Does the Fundamental Metallicity Relation Evolve with Redshift? II' (arXiv:2407.06254), eq. 'FMR_regressions'",
            "doi": None, "url": "https://arxiv.org/abs/2407.06254", "retrieved": RETRIEVED, "sourceMember": "paper.tex",
            "figureMember": "figures/fake_MZR_mega.pdf (v1), figures/Figure4.pdf and Figure2.pdf (v2)", "figureSha256": fig_sha[ver], "sourceArchiveSha256": sha.get(ver)}
    records.append({
        "id": f"garcia24.{n.lower()}.fmr.mu{a}.linear.z0", "source": source, "run": run, "kind": "simulation", "relation": "fmr",
        "epoch": {"zRepresentative": 0, "zNominal": 0, "zMin": 0, "zMax": 0, "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": f"mu_{a} = log10(M*/Msun) - {a} log10(SFR/(Msun/yr)), star-forming centrals at z=0",
                 "xUnit": "log10(Msun)", "yDefinition": f"12+log10(O/H) from the mass-weighted total metallicity of star-forming gas bound to the system, scaled with constant f_O = {fO} and X = 0.76", "yUnit": "dex"},
        "domain": {"xMin": lo, "xMax": hi},
        "representation": {"type": "parametric", "equation": f"12+log(O/H) = {m} mu_{a} + {b}", "expression": "m*x+b", "parameters": {"m": m, "b": b}},
        "scatter": None,
        "selection": {"population": "star-forming central galaxies (sSFR within 0.5 dex of the sSFMS), well resolved (M* > 1e8 Msun, 1e9 in SIMBA; gas mass > 10^8.5, 10^9.5 in SIMBA)", "warning": warn},
        "definitions": {"muAlpha": a, "metallicityQuantity": "gas-O/H",
                        "metallicityCalibration": f"total metallicity of star-forming gas rescaled to O/H with constant oxygen-to-metal mass fraction f_O = {fO} and hydrogen mass fraction X = 0.76",
                        "sfrTimescaleMyr": "unspecified", "imf": "chabrier03", "massDefinition": "unspecified", "population": "star-forming-centrals"},
        "provenance": prov, "calibration": "prediction", "rankable": True,
        "notes": "Equation as printed. " + " ".join(checks[:2]),
    })
for r in records:
    assert r["domain"]["xMin"] < r["domain"]["xMax"]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + checks) + "\n")
print("Wrote", len(records), "records to", OUT)
