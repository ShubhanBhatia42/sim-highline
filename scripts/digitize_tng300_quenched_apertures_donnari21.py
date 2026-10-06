import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2008.00004"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
vf.TICK_MAX = 400
vf.LABEL_MAX = 200
FILES = [(0.0, "QF_ALL_theory_apertures.pdf"), (2.0, "QF_ALL_theory_apertures_33.pdf"), (3.0, "QF_ALL_theory_apertures_25.pdf")]
BLACK, ORANGE = (0.0, 0.0, 0.0), (1.0, 0.5, 0.05)
CURVES = [
    (BLACK, "[] 0", "ms1dex-2rhalf", "log10 SFR below the star-forming main sequence by 1 dex", "SFR within 2 R_half (gas)", "aperture-2rhalf-stars"),
    (BLACK, "[ 14.8 6.4 ] 0", "ms1dex-boundgas", "log10 SFR below the star-forming main sequence by 1 dex", "SFR of all gravitationally bound gas", "aperture-2rhalf-stars"),
    (ORANGE, "[] 0", "ssfr11-2rhalf", "sSFR < 1e-11 /yr", "SFR within 2 R_half (gas)", "aperture-2rhalf-stars"),
    (ORANGE, "[ 14.8 6.4 ] 0", "ssfr11-boundgas", "sSFR < 1e-11 /yr", "SFR of all gravitationally bound gas", "aperture-2rhalf-stars"),
]
AX = {"xDefinition": "log10 stellar mass (within 2 R_half)", "xUnit": "log10(Msun)", "yDefinition": "fraction of all galaxies classified as quenched", "yUnit": "fraction"}


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


records = []
for z, name in FILES:
    pdf = SRC / "figures" / name
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frames(page)
    assert len(fr) == 1
    frame = fr[0]
    fx, fy, cal = vf.calibrate(page, frame)
    assert [v for _, v in cal["yTicks"]] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0] and [v for _, v in cal["xTicks"]][:3] == [9.0, 9.5, 10.0]
    assert any(w[4] == f"z={z:g}" for w in page.get_text("words")), z
    xlo, xhi = fx(frame.x0), fx(frame.x1)
    cs = [c for c in vf.curves(page, frame, fx, fy, min_items=8) if c["width"] == 4.0]
    for color, dsh, tag, crit, ap, mdef in CURVES:
        m = [c for c in cs if near(c["color"], color) and c["dashes"] == dsh]
        assert len(m) == 1, (z, tag, len(m))
        pts = [(x, y) for x, y in m[0]["points"] if xlo <= x <= xhi]
        assert len(pts) >= 10 and all(-0.01 <= y <= 1.01 for _, y in pts), (z, tag)
        records.append(vf.record(
            rid=f"donnari21.tng300.quenched-all-{tag}.z{z:g}", source="IllustrisTNG", run=f"TNG300-1 (all galaxies; {'MS-1dex' if tag.startswith('ms1dex') else 'sSFR<1e-11'}; {'2 R_half' if tag.endswith('2rhalf') else 'all bound gas'})",
            relation="quenched", z=z, axes=AX, points=pts, population="all galaxies (centrals and satellites) with M* >= 10^9 Msun",
            warning=f"Curve read from the vector paths of Donnari et al. 2021 (MNRAS 506, 4760), different-apertures-and-definitions figure (QF_ALL_theory_apertures), TNG300 all galaxies at z={z:g}; no table exists. "
                    f"Quenched definition: {crit}; star formation measured as {ap}. The grey Poisson shading and the paper's other definitions (UVJ, 2-sigma, lifetime-average) are not extracted. No mock observational uncertainties are mentioned for this figure.",
            definitions={"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "massDefinition": mdef, "sfrTimescaleMyr": "instantaneous (gas)", "quenchingCriterion": crit, "population": "all"},
            citation=f"Donnari et al. 2021, MNRAS 506, 4760, apertures and quenched definitions (QF_ALL_theory_apertures), z={z:g}", doi="10.1093/mnras/stab1950", url=f"https://arxiv.org/abs/{ARXIV}",
            figure=name.replace(".pdf", ""), panel=f"z={z:g}", sha=sha, member=f"{name} ({tag} curve, 4 pt stroke)", calib="x: labelled ticks 9-12; y: labelled ticks 0-1; asserted", calibration="prediction"))
assert len(records) == 12
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "donnari21-tng300-quenched-apertures.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} TNG300 quenched-fraction records (z=0, 2, 3; two definitions x two apertures)")
