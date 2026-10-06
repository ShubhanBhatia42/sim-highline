import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2306.04024"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
RUNS = {(0.07, 0.47, 0.2): ("l1_m9", "L1_m9", 1000.0), (0.2, 0.13, 0.53): ("l2p8_m9", "L2p8_m9", 2800.0),
        (0.87, 0.8, 0.47): ("l1_m10", "L1_m10", 1000.0), (0.8, 0.4, 0.47): ("l1_m8", "L1_m8", 1000.0)}
DEF = {"imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}}
FIGS = {
    "shmr": dict(pdf="SMHM_2_Panel.pdf", fig=9, xs=[11, 12, 13, 14, 15], ys=[8, 9, 10, 11, 12], rel="shmr",
                 axes={"xDefinition": "log10 halo mass M_BN98 (Bryan & Norman 1998)", "xUnit": "log10(Msun)",
                       "yDefinition": "log10 median stellar-to-halo mass ratio, M*(<50 pkpc, with 0.3 dex mock scatter)/M_BN98", "yUnit": "dex"},
                 defs={**DEF, "massDefinition": "aperture-50pkpc", "haloMassDefinition": "BN98", "haloMassHistory": "current", "population": "centrals"}, pop="central galaxies",
                 what="median stellar mass as a function of halo mass for central galaxies at z=0, converted here to log10(M*/M_BN98); the 16th-84th percentile shading is not extracted",
                 panel="left-top (resolutions and box sizes, z=0)"),
    "bh": dict(pdf="SMBHM_2_panel.pdf", fig=12, xs=[9, 10, 11, 12], ys=[5, 6, 7, 8, 9, 10, 11], rel="bh",
               axes={"xDefinition": "log10 stellar mass (3D 50 pkpc aperture, with 0.3 dex mock scatter)", "xUnit": "log10(Msun)",
                     "yDefinition": "log10 median mass of the most massive black hole in the galaxy", "yUnit": "log10(Msun)"},
               defs={**DEF, "massDefinition": "aperture-50pkpc", "population": "all", "bhMassMethod": "intrinsic"}, pop="all galaxies",
               what="median mass of the most massive black hole in the galaxy versus the galaxy's stellar mass at z=0; the 16th-84th percentile shading is not extracted",
               panel="left (resolutions and box sizes, z=0)"),
}


def near(c, t):
    return c is not None and all(abs(a - b) < 0.01 for a, b in zip(c, t))


def labels(words, frame, axis):
    out = []
    for w in words:
        if not re.fullmatch(r"10\d{1,2}", w[4]):
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if axis == "x" and w[1] > frame.y1 and frame.x0 - 20 < cx < frame.x1 + 5:
            out.append((cx, float(w[4][2:])))
        if axis == "y" and w[0] < frame.x0 and frame.y0 - 5 < cy < frame.y1 + 5:
            out.append((cy, float(w[4][2:])))
    return sorted(out)


records = []
for key, cfg in FIGS.items():
    pdf = SRC / "Images" / cfg["pdf"]
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    frame = vf.frames(page)[0]
    words = page.get_text("words")
    xl, yl = labels(words, frame, "x"), labels(words, frame, "y")
    fx, xt = vf.axis_fit(page, frame, "x", labels=xl)
    fy, yt = vf.axis_fit(page, frame, "y", labels=yl)
    assert [v for _, v in xt] == cfg["xs"] and sorted(v for _, v in yt) == cfg["ys"], (key, xt, yt)
    xlo, xhi, ylo, yhi = fx(frame.x0), fx(frame.x1), min(fy(frame.y0), fy(frame.y1)), max(fy(frame.y0), fy(frame.y1))
    seen = set()
    for cu in vf.curves(page, frame, fx, fy, min_items=8):
        c = next((RUNS[k] for k in RUNS if near(cu["color"], k)), None)
        if c is None or cu["dashes"] != "[] 0" or cu["width"] != 1.5:
            continue
        rkey, run, box = c
        pts = [(x, y) for x, y in cu["points"] if xlo <= x <= xhi and ylo <= y <= yhi]
        if key == "shmr":
            pts = [(x, y - x) for x, y in pts]
        assert rkey not in seen and len(pts) >= 8 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (key, rkey)
        seen.add(rkey)
        records.append(vf.record(
            rid=f"schaye23.flamingo-{rkey}.{key}.z0", source="FLAMINGO", run=run, relation=cfg["rel"], z=0.0, axes=cfg["axes"], points=pts, population=cfg["pop"],
            warning=f"Solid segment only of the curve in Schaye et al. 2023 (MNRAS 526, 4978) Fig. {cfg['fig']} ({cfg['panel']}): {cfg['what']}. Curves are dotted below the minimum stellar mass used "
                    f"for calibration; the dotted part is omitted. {run}: box {box:g} cMpc, fiducial galaxy formation model and cosmology. The paper gives no table.",
            definitions=cfg["defs"], citation=f"Schaye et al. 2023, MNRAS 526, 4978, Fig. {cfg['fig']} (arXiv source numbering)", doi="10.1093/mnras/stad2419", url=f"https://arxiv.org/abs/{ARXIV}",
            figure=f"Figure {cfg['fig']}", panel=cfg["panel"], sha=sha, member=f"Images/{pdf.name} (solid {run} line, 1.5 pt stroke)",
            calib="both axes: labelled decades snapped to tick marks (exponent from the label text, spacing consistent)", calibration="prediction"))
    assert seen == {v[0] for v in RUNS.values()}, (key, seen)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "schaye23-flamingo-relations.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FLAMINGO SHMR and BH records from Schaye+23 vector paths")
