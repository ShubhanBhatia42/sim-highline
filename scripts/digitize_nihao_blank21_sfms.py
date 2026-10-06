import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2008.13379"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDFDIR = SRC / "pdf"
ZS = [0.0, 1.0, 2.0, 4.0]
BLUE = (0.12, 0.47, 0.71)
FIGS = {
    "sfms": dict(eps="sfr_mstar_zx4", rel="sfms", xs=[4, 5, 6, 7, 8, 9, 10, 11], ys=[-6, -5, -4, -3, -2, -1, 0, 1],
                 axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 SFR averaged over 200 Myr within 0.2 R_vir", "yUnit": "log10(Msun/yr)"},
                 defs={"imf": "chabrier03", "cosmology": {"H0": 67.1, "Om": 0.3175}, "massDefinition": "unspecified", "sfrTimescaleMyr": 200, "sfrStatistic": "instantaneous-200Myr", "population": "zoom-centrals"}),
}


def explabels(words, pick):
    return sorted((pick(w), float(w[4][2:])) for w in words if re.fullmatch(r"10-?\d{1,2}", w[4]) and pick(w) is not None)


records = []
for key, cfg in FIGS.items():
    pdf = PDFDIR / f"{cfg['eps']}.pdf"
    if not pdf.exists():
        eps = next(SRC.rglob(f"{cfg['eps']}.eps"))
        PDFDIR.mkdir(exist_ok=True)
        subprocess.run(["epstopdf", str(eps), f"--outfile={pdf}"], check=True)
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frames(page)
    assert len(fr) == 5
    panels = fr[1:]
    words = page.get_text("words")
    zlab = {w[4]: w for w in words if re.fullmatch(r"z=\d", w[4])}
    fx_col, fy_row = {}, {}
    for col, pn in ((0, panels[2]), (1, panels[3])):
        lab = explabels(words, lambda w, pn=pn: (w[0] + w[2]) / 2 if w[1] > pn.y1 and pn.x0 - 3 < (w[0] + w[2]) / 2 < pn.x1 + 3 else None)
        fx_col[col], xt = vf.axis_fit(page, pn, "x", labels=lab)
        assert len(xt) >= 3, (key, xt)
    for row, pn in ((0, panels[0]), (1, panels[2])):
        lab = explabels(words, lambda w, pn=pn: (w[1] + w[3]) / 2 if w[0] < pn.x0 and pn.y0 - 3 < (w[1] + w[3]) / 2 < pn.y1 + 3 else None)
        fy_row[row], yt = vf.axis_fit(page, pn, "y", labels=lab)
        assert len(yt) >= 4, (key, yt)
    for i, (z, pn) in enumerate(zip(ZS, panels)):
        col, row = i % 2, i // 2
        label = f"z={z:g}"
        zw = zlab[label]
        assert pn.x0 <= zw[0] <= pn.x1 and pn.y0 <= zw[1] <= pn.y1, label
        fx, fy = fx_col[col], fy_row[row]
        pts = sorted(vf.markers(page, pn, fx, fy, BLUE, max_size=8.0, min_size=3.0))
        line = [c for c in vf.curves(page, pn, fx, fy, min_items=50) if c["color"] == BLUE and c["width"] == 1.0 and c["dashes"] == "[] 0"]
        assert len(pts) >= 20 and len(line) == 1, (key, z, len(pts), len(line))
        sel = lambda p: p
        common = dict(source="NIHAO zoom suite", relation=cfg["rel"], z=z, axes=cfg["axes"], definitions=cfg["defs"], citation=f"Blank et al. 2021 (NIHAO XXVI), MNRAS, SFR-M* figure (fig:sfr_mstar_zx4), {label} panel",
                      doi="10.1093/mnras/staa2670", url=f"https://arxiv.org/abs/{ARXIV}", figure="fig:sfr_mstar_zx4", panel=label, sha=sha, member=f"{pdf.name} (converted from {cfg['eps']}.eps)",
                      calib="x: labelled decades from the bottom-row panels (shared by column); y: labelled decades from the left-column panels (shared by row); both snapped to tick marks", calibration="unknown")
        conv = ""
        records.append(vf.record(
            rid=f"blank21.nihao.{key}-galaxies.z{z:g}", run="NIHAO zoom sample (per galaxy)", points=sel(pts), population="individual zoom galaxies (not volume complete)",
            warning=f"Marker centres of the simulated galaxies read from the vector paths of Blank et al. 2021 SFR-M* figure ({label}); no table is published. Zoom selections are not volume complete, so the sample is not rankable.{conv} "
                    "Marker centres, so the points are the plotted values, not binned medians.", interval="scatter", connect=False, strict=False, **common))
        lp = sel([(x, y) for x, y in line[0]["points"]])
        lp = [(x, y) for x, y in lp if fx(pn.x0) - 1e-6 <= x <= fx(pn.x1) + 1e-6]
        records.append(vf.record(
            rid=f"blank21.nihao.{key}-fit.z{z:g}", run="NIHAO zoom sample (linear fit)", points=lp, population="fit to the plotted zoom galaxies",
            warning=f"Black fit line of Blank et al. 2021 SFR-M* figure ({label}): " + ("a linear fit to the NIHAO galaxies with non-zero SFR (zero-SFR lower-limit arrows are excluded from the fit and from this record)")
                    + f"; vertices of the plotted line.{conv} Fit to a zoom selection, not volume complete.", **common))
for r in records:
    assert r["representation"]["points"], r["id"]
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "blank21-nihao-sfms.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} NIHAO SFMS records (galaxies and fits) from Blank+21 vector paths")
