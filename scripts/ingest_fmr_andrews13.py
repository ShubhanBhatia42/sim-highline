"""Andrews & Martini 2013 (arXiv:1211.3418, ApJ 765, 140): direct-method (Te) fundamental metallicity relation of SDSS stacks, mu_0.66 = log M* - 0.66 log SFR.
Two records: (1) the 117 M*-SFR stacks with a direct-method 12+log(O/H) (machine-readable tables datafile2/datafile3 of the paper source), with x = mu_0.66
computed from the stack-bin centres and validated against the 116 marker centres of the vector Fig. 12; (2) the black linear fit drawn in Fig. 12
(the paper quotes only its slope, 0.43), read from the vector path. Fetches the source by arXiv id."""
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
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "1211.3418"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "fmr-andrews13.json"
QUOTES = Path(__file__).resolve().parent.parent / "data" / "quotes" / (OUT.stem + ".txt")   # the sentences used, verbatim, with file and line, and the numeric checks
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/vector_figure_src") / ARXIV
RETRIEVED = "2026-10-18"
TEX = SRC / "ms.tex"
ALPHA = 0.66


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


quote(r"\mu_\alpha \equiv \mathrm{log}(M_\star) - \alpha \mathrm{log(SFR)},")
quote(r"The scatter in metallicity at fixed $\mu_\alpha$ is minimized for $\alpha$~=~0.66")
quote(r"The coefficient (0.66) on log(SFR) in the abscissa minimizes the scatter in the FMR")
quote(r"The black line shows a linear fit to the data, with a slope of 0.43.")
quote(r"The scatter in the direct method FMR ($\sigma$~=~0.13~dex;")
quote(r"We employed the direct method to measure the metallicities of $\sim$200,000 star-forming galaxies from the SDSS that were stacked in bins of")
quote(r"We adopt the total stellar mass \citep{kauffmann2003a} and the total SFR \citep{brinchmann2004, salim2007} values from the MPA-JHU catalog, as opposed to these quantities calculated only for the light within the fiber.")
quote(r"galaxies binned in 0.1 dex in \mstar\ from log(\mstar/\msun)~=~7.0~to~11.0 {\it and} 0.5 dex in SFR from log(SFR/[\msun~ yr$^{-1}$])~=~$-$2.0~to~2.0")
quote(r"0.027~<~$z$~<~0.25 to ensure that the \oii\ line and the \oiia\ lines fall within the wavelength range of the SDSS spectrograph")
quote(r"We discard galaxies classified as AGN because AGN emission line ratios may produce spurious metallicity measurements.")
quote(r"we form a ``composite'' metallicity calibration")
quote(r"the solar oxygen abundance of 12~+~log(O/H)~=~8.86 from \citet{delahaye2006}")
quote(r"The metallicities of the stacks are presented in Table \ref{table:metallicity}.")
quote(r"for the stacks with log(SFR)~>~$-$1.0 (the same SFR range as the stacks with direct method metallicities)")
assert not FAILED, FAILED


# ---- tables (machine-readable, from the source archive) ----
def table(name):
    L = (SRC / name).read_text().split("\n")
    idx = [i for i, l in enumerate(L) if l.startswith("-----")]
    return [l for l in L[idx[-1] + 1:] if l.strip()]


key = lambda l: tuple(l[a:b].strip() for a, b in ((0, 4), (5, 9), (10, 14), (15, 19)))
t2 = {key(l): (int(l[20:25]), float(l[26:32]), float(l[33:39])) for l in table("datafile2.txt") if key(l)[2]}  # N, median log M*, median log SFR
t3 = {key(l): (float(l[70:74]), float(l[75:79]) if l[75:79].strip() else None, int(l[20:25])) for l in table("datafile3.txt") if key(l)[2] and l[70:74].strip()}
stacks = []
for k, (z, ez, n3) in t3.items():
    n, mmed, smed = t2[k]
    assert n == n3
    mlo, mup, slo, sup = map(float, k)
    stacks.append({"mu": (mlo + mup) / 2 - ALPHA * (slo + sup) / 2, "mu_median": mmed - ALPHA * smed, "z": z, "ez": ez, "n": n, "key": k})
assert len(stacks) == 117, len(stacks)

# ---- vector Fig. 12 ----
with tempfile.TemporaryDirectory() as d:
    pdf = Path(d) / "fig12.pdf"
    subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", "-dEPSCrop", f"-sOutputFile={pdf}", str(SRC / "fig12.eps")], check=True, capture_output=True)
    page = vf.page_of(pdf)
    frame = max(vf.frames(page), key=lambda r: r.width * r.height)
    fx, xt = vf.axis_fit(page, frame, "x")
    fy, yt = vf.axis_fit(page, frame, "y")
    assert len(xt) >= 5 and len(yt) >= 8
    assert any("0.66" in w[4] for w in page.get_text("words")), "x-axis label must carry alpha=0.66"
    markers = []
    for dr in page.get_drawings():
        r = dr["rect"]
        if dr["fill"] is not None and abs(r.width - 7.14) < 0.05 and abs(r.height - 7.14) < 0.05 and frame.contains(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)):
            markers.append((fx((r.x0 + r.x1) / 2), fy((r.y0 + r.y1) / 2)))
    line = [dr for dr in page.get_drawings() if dr["type"] == "s" and dr["color"] == (0.0, 0.0, 0.0) and abs((dr.get("width") or 0) - 3.0) < 0.01 and len(dr["items"]) > 20]
    assert len(line) == 1
    pts = [line[0]["items"][0][1]] + [it[-1] for it in line[0]["items"]]
    P = [(fx(p.x), fy(p.y)) for p in pts]
assert len(markers) == 116, len(markers)
S = np.array([(s["mu"], s["z"]) for s in stacks])
dist = [float(np.hypot(S[:, 0] - x, S[:, 1] - y).min()) for x, y in markers]
S_med = np.array([(s["mu_median"], s["z"]) for s in stacks])
dist_med = [float(np.hypot(S_med[:, 0] - x, S_med[:, 1] - y).min()) for x, y in markers]
assert max(dist) < 0.01, max(dist)  # all 116 plotted markers sit on the table stacks with x from the bin centres
unmatched = [s for s in stacks if min(math.hypot(s["mu"] - x, s["z"] - y) for x, y in markers) > 0.02]
assert len(unmatched) == 1, len(unmatched)  # one table stack is not drawn (outside the plotted window or hidden)
# fitted line drawn in the figure
slope_fig = (P[-1][1] - P[0][1]) / (P[-1][0] - P[0][0])
assert all(abs((y - P[0][1]) - slope_fig * (x - P[0][0])) < 0.01 for x, y in P)  # straight
assert abs(slope_fig - 0.43) < 0.01, slope_fig  # the paper's quoted slope
icpt9 = P[0][1] + slope_fig * (9.0 - P[0][0])
# the paper's quoted scatter, sigma = 0.13 dex, around the direct-method FMR, and the alpha that minimizes it
mu = np.array([s["mu"] for s in stacks]); z = np.array([s["z"] for s in stacks])
resid = z - (icpt9 + slope_fig * (mu - 9.0))
sigma = float(resid.std())
assert abs(sigma - 0.13) < 0.02, sigma


def scatter_alpha(a):
    xs = np.array([float(s["key"][0]) / 2 + float(s["key"][1]) / 2 - a * (float(s["key"][2]) + float(s["key"][3])) / 2 for s in stacks])
    c = np.polyfit(xs, z, 1)
    return float((z - np.polyval(c, xs)).std())


alphas = np.arange(0.0, 1.21, 0.02)
best = float(alphas[int(np.argmin([scatter_alpha(a) for a in alphas]))])
assert abs(best - ALPHA) < 0.1, best  # reproduces the paper's alpha=0.66 (they quote one number; a 0.02 grid here)
xlo, xhi = round(min(m[0] for m in markers), 3), round(max(m[0] for m in markers), 3)
checks = [
    f"Fig. 12: {len(markers)} drawn markers all within {max(dist):.4f} dex of a table stack (x from BIN CENTRES: median {np.median(dist):.4f}; with x from the tabulated median M* and SFR the median distance is {np.median(dist_med):.3f} and the max {max(dist_med):.3f}); 1 of 117 table stacks has no marker (bin M*, SFR limits {unmatched[0]['key']}, log O/H {unmatched[0]['z']}, x {unmatched[0]['mu']:.3f})",
    f"drawn black fit line: slope {slope_fig:.3f} (paper: 0.43), value at mu_0.66=9.0: {icpt9:.3f}; rms of the 117 tabulated stacks about it: {sigma:.3f} dex (paper: sigma = 0.13 dex)",
    f"alpha minimizing the rms scatter about a linear fit of the 117 stack centres (0.02 grid): {best:.2f} (paper: 0.66)",
]
print("\n".join(checks))

tar = Path(str(SRC) + ".tar")
fig_sha = hashlib.sha256((SRC / "fig12.eps").read_bytes()).hexdigest()
arch = hashlib.sha256(tar.read_bytes()).hexdigest() if tar.exists() else None
cite = "Andrews & Martini 2013, ApJ 765, 140 (arXiv:1211.3418)"
defs = {"muAlpha": ALPHA, "metallicityQuantity": "gas-O/H", "metallicityCalibration": "Te-stacked",
        "sfrTimescaleMyr": "unspecified", "sfrIndicator": "MPA-JHU total SFR (Brinchmann+04, Salim+07)", "imf": "unspecified",
        "massDefinition": "sed-total", "population": "star-forming"}
axes = {"xDefinition": "mu_0.66 = log10(M*/Msun) - 0.66 log10(SFR/(Msun/yr)) at the centre of each M*-SFR stack bin (0.1 dex in M*, 0.5 dex in SFR); MPA-JHU total stellar mass and total SFR",
        "xUnit": "log10(Msun)", "yDefinition": "12+log10(O/H), direct (Te) method on stacked SDSS spectra, composite O+ and O++ abundance", "yUnit": "dex"}
epoch = {"zRepresentative": 0.138, "zMin": 0.027, "zMax": 0.25, "mode": "observational-bin", "snapshot": None}
sel_common = ("SDSS DR7 MPA-JHU star-forming galaxies stacked in M*-SFR bins (0.027<z<0.25, BPT AGN removed); direct-method metallicity in stacks where the [OIII]4363 / [OII]7320,7330 auroral lines are measured")
stack_pts = sorted(({"x": round(s["mu"], 3), "y": s["z"], **({"yLow": round(s["z"] - s["ez"], 3), "yHigh": round(s["z"] + s["ez"], 3)} if s["ez"] is not None else {}), "count": s["n"]} for s in stacks), key=lambda p: (p["x"], p["y"]))
prov_t = {"tier": "published-table", "citation": cite + ", machine-readable tables 2 and 3 (median M*, SFR; 12+log(O/H)) and Fig. 12", "doi": "10.1088/0004-637X/765/2/140",
          "url": "https://arxiv.org/abs/1211.3418", "retrieved": RETRIEVED, "sourceMember": "datafile2.txt (median log M*, log SFR) joined with datafile3.txt (log O/H) by stack bin; Fig. 12 = fig12.eps",
          "figureSha256": fig_sha}
if arch:
    prov_t["sourceArchiveSha256"] = arch
rec_t = {
    "id": "andrews13.sdss-stacks.fmr.mu0.66.stacks", "source": "Andrews & Martini 2013", "run": "M*-SFR stacks, direct method", "kind": "observation", "relation": "fmr",
    "epoch": epoch, "axes": axes, "domain": {"xMin": stack_pts[0]["x"], "xMax": stack_pts[-1]["x"]},
    "representation": {"type": "points", "intervalKind": "uncertainty", "connect": False, "points": stack_pts},
    "scatter": {"value": 0.13, "unit": "dex", "meaning": "scatter of the stacks about the direct-method FMR, as stated by the paper"},
    "selection": {"population": sel_common,
                  "warning": "Each point is one M*-SFR stack (not a binned median over a population). x is computed here from the stack-bin centres, which is what Fig. 12 plots (116 of the 117 stacks are drawn; the one not drawn is the stack with M* 8.6-8.7 and log SFR -1.5 to -1.0, mu_0.66 = 9.475, log O/H = 8.22, below the log SFR > -1.0 range the paper uses for its direct-method FMR; all 116 markers coincide with these x values within 0.01 dex, whereas x from the tabulated median M* and SFR does not). redshift representative 0.138 = midpoint of 0.027-0.25. The paper does not state an IMF."},
    "definitions": defs, "provenance": prov_t, "calibration": "validation", "rankable": True,
    "notes": "Error bars are the tabulated uncertainty on log(O/H). " + " ".join(checks),
}
prov_l = {"tier": "digitized-figure", "citation": cite + ", Fig. 12 (black line)", "doi": "10.1088/0004-637X/765/2/140", "url": "https://arxiv.org/abs/1211.3418", "retrieved": RETRIEVED,
          "figure": "Fig. 12", "panel": "black line, linear fit to the stacks", "checksumSha256": fig_sha, "sourceMember": "fig12.eps",
          "extractionMethod": "vector path vertices of the 3 pt black polyline (PyMuPDF get_drawings) through axes calibrated on labelled ticks (vector_figure.axis_fit)",
          "axisCalibrationPixels": {"xTicks": [list(t) for t in xt], "yTicks": [list(t) for t in yt]}, "digitizationUncertaintyDex": 0.01}
if arch:
    prov_l["sourceArchiveSha256"] = arch
x0, x1 = xlo, xhi
rec_l = {
    "id": "andrews13.sdss-stacks.fmr.mu0.66.linear-fit", "source": "Andrews & Martini 2013", "run": "linear fit drawn in Fig. 12", "kind": "observation", "relation": "fmr",
    "epoch": epoch, "axes": axes, "domain": {"xMin": x0, "xMax": x1},
    "representation": {"type": "points", "intervalKind": "unspecified", "connect": True,
                       "points": [{"x": x0, "y": round(icpt9 + slope_fig * (x0 - 9.0), 4)}, {"x": x1, "y": round(icpt9 + slope_fig * (x1 - 9.0), 4)}]},
    "scatter": {"value": 0.13, "unit": "dex", "meaning": "scatter of the stacks about the direct-method FMR, as stated by the paper"},
    "selection": {"population": sel_common,
                  "warning": f"The paper states only the slope of this fit (0.43); the intercept ({icpt9:.3f} at mu_0.66=9) is read from the vector path, so this is a digitized figure, not a published fit. The line is drawn across the whole plot window in the figure; it is clipped here to the x range of the plotted stacks ({x0}-{x1})."},
    "definitions": defs, "provenance": prov_l, "calibration": "validation", "rankable": False,
    "notes": "Two vertices of the straight line: " + checks[1],
}
for r in (rec_t, rec_l):
    assert r["domain"]["xMin"] < r["domain"]["xMax"]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec_t, rec_l]}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + checks) + "\n")
print("Wrote 2 records to", OUT, "points:", len(stack_pts))
