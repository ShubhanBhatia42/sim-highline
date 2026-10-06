import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1812.07584"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
vf.LABEL_MAX = 400
RUNS = {
    (1.0, 0.5, 0.05): ("tng300", "IllustrisTNG", "TNG300-1", {"H0": 67.74, "Om": 0.3089}),
    (0.12, 0.47, 0.71): ("tng100", "IllustrisTNG", "TNG100-1", {"H0": 67.74, "Om": 0.3089}),
    (0.84, 0.15, 0.16): ("illustris", "Illustris", "Illustris-1", {"H0": 70.4, "Om": 0.2726}),
}
CRIT = {"[] 0": ("sfr1dex", "SFR below the star-forming main sequence by 1 dex (linear MS extrapolated at high mass; SFR within 2 R_half over 200 Myr)"),
        "[ 37 16 ] 0": ("uvj", "TNG UVJ colour cut (dust-attenuated rest-frame U-V vs V-J, Donnari et al. 2019 eqs. TNG_cut)")}
ZS = [0.3, 0.75, 1.75]
XMAX = 11.5
PDF = SRC / "QfracVSmass.pdf"
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)[1:]
assert len(fr) == 3
fx0, fy, cal = vf.calibrate(page, fr[0])
assert [v for _, v in cal["xTicks"]] == [9.0, 9.5, 10.0, 10.5, 11.0, 11.5] and [v for _, v in cal["yTicks"]] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
words = page.get_text("words")
records = []
for i, (z, r) in enumerate(zip(ZS, fr)):
    fx = vf.shifted(fx0, r.x0 - fr[0].x0)
    if i:
        vf.check_labels(page, r, "x", fx)
    label = f"z={z:g}"
    assert any(w[4] == label and r.x0 <= (w[0] + w[2]) / 2 <= r.x1 and w[3] < r.y0 + 150 for w in words), label
    for c in vf.curves(page, r, fx, fy, min_items=6):
        if c["color"] not in RUNS or c["width"] != 10.0 or c["dashes"] not in CRIT:
            continue
        key, source, run, cosmo = RUNS[c["color"]]
        ckey, cdesc = CRIT[c["dashes"]]
        pts = [(x, y) for x, y in c["points"] if x <= XMAX + 1e-6]
        assert len(pts) >= 12 and all(-0.01 <= y <= 1.01 for _, y in pts), (z, run)
        records.append(vf.record(
            rid=f"donnari19.{key}.quenched-{ckey}.z{z:g}", source=source, run=f"{run} ({'SFR<MS-1dex' if ckey == 'sfr1dex' else 'UVJ'})", relation="quenched", z=z,
            axes={"xDefinition": "log10 stellar mass (within 2 R_half)", "xUnit": "log10(Msun)", "yDefinition": "fraction of galaxies classified as quenched", "yUnit": "fraction"},
            points=pts, population="all galaxies (centrals and satellites) with M* >= 10^9 Msun",
            warning=f"Curve vertices read from the vector paths of Donnari et al. 2019 (MNRAS 485, 4817), Quenched-fraction figure, {label} panel; no table exists. "
                    "The paper's curves include mock observational uncertainties of 0.2 dex on M* and 0.3 dex on SFR, so they are not the raw catalogue fractions. "
                    + ("Illustris is shown only with the SFR-based selection." if key == "illustris" else "") + " The paper's z labels are the plotted epochs; curves extend past 10^11.5 Msun but are clipped by the axis there and dropped here.",
            definitions={"massDefinition": "aperture-2rhalf-stars", "imf": "chabrier03", "cosmology": cosmo, "population": "all", "sfrTimescaleMyr": 200, "quenchingCriterion": cdesc},
            citation="Donnari et al. 2019, MNRAS 485, 4817, quenched-fraction figure (fig:Qfrac_methods, bottom panels)", doi="10.1093/mnras/stz712", url=f"https://arxiv.org/abs/{ARXIV}",
            figure="fig:Qfrac_methods (bottom panels; QfracVSmass.pdf)", panel=f"{label} panel", sha=sha, member=f"{PDF.name} ({run}, {ckey} line, 10 pt stroke)",
            calib="x: labelled ticks 9-11.5; y: labelled ticks 0-1; the three panels share axes (offset by frame origin; labels asserted)", uncertainty=0.01,
            calibration="prediction"))
assert len(records) == 15, len(records)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "donnari19-quenched.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} quenched-fraction records from Donnari+19 vector paths")
