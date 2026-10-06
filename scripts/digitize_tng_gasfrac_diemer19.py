import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1902.10714"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
SIMS = {(0.12, 0.47, 0.71): ("tng100", "TNG100-1"), (1.0, 0.5, 0.05): ("tng300", "TNG300-1")}
GAS = {"hi": ("mstar_fstar_split_hi_nosplit.pdf", "hi-fraction", "HI"), "h2": ("mstar_fstar_split_h2_nosplit.pdf", "h2-fraction", "H2")}


def near(c, t, tol=0.02):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


records = []
for key, (name, rel, phase) in GAS.items():
    pdf = SRC / name
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    top, bot = vf.frames(page)
    words = page.get_text("words")
    ylab = sorted(((w[1] + w[3]) / 2, float(w[4][2:].replace("−", "-"))) for w in words if re.fullmatch(r"10[−-]?\d{1,2}", w[4]) and w[0] < top.x0 and top.y0 - 3 < (w[1] + w[3]) / 2 < top.y1 + 3)
    xlab = sorted(((w[0] + w[2]) / 2, float(w[4][2:])) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[1] > bot.y1 and bot.x0 - 2 < (w[0] + w[2]) / 2 < bot.x1 + 3)
    fy, yt = vf.axis_fit_log2(page, top, "y", ylab)
    fx, xt = vf.axis_fit_log2(page, bot, "x", xlab)
    assert [v for _, v in xt][:3] == [9.0, 10.0, 11.0] and sorted(v for _, v in yt)[0] == -4.0, (xt, yt)
    polys = []
    for d in page.get_drawings():
        if d["type"] == "fs" and d["fill"] is not None and len(d["items"]) >= 12 and all(i[0] == "l" for i in d["items"]) and d["rect"].width > 30 and d["rect"].y1 < top.y1 + 2:
            run = next((v for k, v in SIMS.items() if near(d["fill"], k)), None)
            if run:
                pts = [d["items"][0][1]] + [i[2] for i in d["items"]]
                byx = {}
                for p in pts:
                    byx.setdefault(round(fx(p.x), 2), []).append(fy(p.y))
                polys.append((run, d.get("fill_opacity"), byx))
    for color, (rk, rname) in SIMS.items():
        mine = [p for p in polys if p[0][0] == rk]
        wide = [p for p in mine if p[1] is not None and p[1] < 0.35]
        narrow = [p for p in mine if p[1] is not None and p[1] >= 0.35]
        assert len(wide) == 1 and len(narrow) == 1, (key, rk, [(p[1], len(p[2])) for p in mine])
        W, N = wide[0][2], narrow[0][2]
        xs = sorted(x for x in N if len(N[x]) >= 2 and x in W and len(W[x]) >= 2)
        assert len(xs) >= 5, (key, rk, len(xs))
        pts, scat = [], []
        for x in xs:
            lo, hi = min(N[x]), max(N[x])
            pts.append({"x": round(x, 3), "y": round((lo + hi) / 2, 4), "yLow": round(lo, 4), "yHigh": round(hi, 4)})
            scat.append({"x": round(x, 3), "yLow68": round(min(W[x]), 4), "yHigh68": round(max(W[x]), 4)})
        records.append(vf.record(
            rid=f"diemer19.{rk}.{rel}.z0", source="IllustrisTNG", run=f"{rname} ({phase} gas fraction)", relation=rel, z=0.0,
            axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": f"log10 median {phase} mass over stellar mass, M_{phase}/M* (galaxies above the detection threshold only)", "yUnit": "dex"},
            points=pts, population=f"galaxies with {phase} fraction above the Calette+18 detection threshold (the fraction below it is shown separately in the paper and not extracted)",
            warning=f"Read from the vector paths of Diemer et al. 2019 (MNRAS 487, 1529), gas-fraction figure (mstar_fstar_split_{key}_nosplit), top panel, z=0; no table exists. "
                    f"The plotted median is the centre of the dark band, whose edges (yLow, yHigh) span the nine HI-H2 transition models used, i.e. a systematic envelope, not a statistical error; the mean 68 per cent scatter of the models is stored under scatter. "
                    "TNG100 and TNG300 differ in volume and resolution; neither is rankable as a single-model median.",
            interval="uncertainty", scatter={"description": "mean 68 per cent scatter (light band), mean of the 16th/84th percentile contours of the nine models", "points": scat},
            definitions={"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "massDefinition": "unspecified", "population": "galaxies-above-detection-threshold", "gasPhase": phase},
            citation="Diemer et al. 2019, MNRAS 487, 1529, HI and H2 gas fractions vs stellar mass (arXiv source numbering), z=0", doi="10.1093/mnras/stz1323", url=f"https://arxiv.org/abs/{ARXIV}",
            figure=f"mstar_fstar_split_{key}_nosplit", panel="top panel", sha=sha, member=f"{name} (dark envelope band centre, light 68% band)",
            calib="x: log decades 10^9-10^12 from the bottom panel; y: log decades 10^-4..10^0 from the top panel; minor-tick validated", calibration="prediction"))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "diemer19-tng-gasfrac.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} TNG HI and H2 gas-fraction records")
