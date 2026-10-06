import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2203.10098"
DOI = "10.1093/mnras/stac806"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PANELS = {"kappa": ("jstar_vs_mstar_by_kappa_L75n1820TNG_099_centrals_fr13.pdf", "kappa_rot", "kappa_rot >= 0.5 (late-type)", "kappa_rot < 0.5 (early-type)", "kinematic morphology, kappa_rot of Sales+10 / Rodriguez-Gomez+17"),
          "plate": ("jstar_vs_mstar_by_P_Late_L75n1820TNG_099_centrals_fr13.pdf", "plate", "P(Late) >= 0.5 (spirals)", "P(Late) < 0.5 (ellipticals and lenticulars)", "visual-like morphology, P(Late) of Huertas-Company+19")}
BLUE, RED = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
records = []


def explabels(page, fr, axis):
    out = []
    for w in page.get_text("words"):
        t = w[4]
        if not (t.startswith("10") and len(t) > 2 and t[2:].isdigit()):
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if axis == "x" and 0 < cy - fr.y1 < 20 and fr.x0 - 5 <= cx <= fr.x1 + 5:
            out.append((cx, int(t[2:])))
        if axis == "y" and 0 < fr.x0 - cx < 30 and fr.y0 - 5 <= cy <= fr.y1 + 5:
            out.append((cy, int(t[2:])))
    return out


for key, (fn, slug, late, early, morph) in PANELS.items():
    pdf = SRC / "figs" / fn
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frame_from_long_lines(page, 100)
    fx, xt = vf.axis_fit_log2(page, fr, "x", explabels(page, fr, "x"))
    fy, yt = vf.axis_fit_log2(page, fr, "y", explabels(page, fr, "y"))
    lines = {c["color"]: c for c in vf.curves(page, fr, fx, fy, min_items=4) if c["width"] == 1.5}
    bands = {}
    for d in page.get_drawings():
        if d["type"] == "fs" and d.get("fill_opacity") == 0.25 and d["fill"] is not None:
            bands[tuple(round(v, 2) for v in d["fill"])] = [(fx(p.x), fy(p.y)) for p in [d["items"][0][1]] + [i[-1] for i in d["items"]]]
    for col, name, pop in ((BLUE, "late", late), (RED, "early", early)):
        med = vf.clip(lines[col]["points"], 9.0, 12.0, 1.0, 4.5)
        med = [p for i, p in enumerate(med) if i == 0 or p[0] > med[i - 1][0] + 1e-6]
        band = bands[col]
        if key == "kappa":
            assert {"late": (2.0, 2.5), "early": (1.6, 2.1)}[name][0] < med[0][1] < {"late": (2.0, 2.5), "early": (1.6, 2.1)}[name][1] and med[0][0] < 9.3, (key, name, med[0])
        pts = []
        for x, y in med:
            near = [b[1] for b in band if abs(b[0] - x) < 0.004]
            assert len(near) >= 2, (key, name, x, len(near))
            pts.append({"x": round(x, 4), "y": round(y, 4), "yLow": round(min(near), 4), "yHigh": round(max(near), 4)})
        assert 9.0 <= med[0][0] < 10.2 and all(1.5 < y < 4.2 for _, y in med) and all(p["yLow"] <= p["y"] <= p["yHigh"] for p in pts), (key, name)
        records.append(vf.record(
            rid=f"rodriguezgomez22.tng100.jstar.{slug}.{name}.z0", source="IllustrisTNG", run=f"TNG100-1 centrals, {pop}", relation="jstar", z=0.0,
            axes={"xDefinition": "log10 stellar mass of the whole Subfind object", "xUnit": "log10(Msun)", "yDefinition": "log10 specific angular momentum of the stars, j_stars, of the whole Subfind object", "yUnit": "log10(kpc km/s)"},
            points=pts, population=f"central galaxies, {pop}", interval="scatter",
            definitions={"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "massDefinition": "total-subhalo (entire Subfind object, no aperture)", "population": "centrals, split by morphology", "jDefinition": "stars, entire Subfind object, frame centred on the potential minimum (Genel+15 method)", "sfrStatistic": "median"},
            citation=f"Rodriguez-Gomez et al. 2022, MNRAS 512, 5978 (arXiv:{ARXIV}), j_stars-M_stars relation for central galaxies at z=0 ({morph})", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="j_stars versus stellar mass for IllustrisTNG centrals at z=0 (top panels, Fall diagram)", panel=f"{key} classification, {name}-type median with 16th-84th percentile band", sha=sha, member=fn, calibration="prediction",
            calib="x and y: decade labels (10^n words) snapped to major ticks and validated by the minor-tick pattern at log10(2..9); log axes",
            warning=f"Median j_stars of {pop} TNG100-1 central galaxies at z=0 with the 16th-84th percentile range at fixed stellar mass, read from the vector paths of Rodriguez-Gomez et al. 2022 ({morph}). Properties are measured for the whole Subfind object with no aperture, so the values are not comparable to aperture-based j_stars without caution; the paper's observational overlays (Fall+13, Posti+18) are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "rodriguezgomez22-tng-jstar.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} TNG j_stars-M* records from Rodriguez-Gomez+22")
