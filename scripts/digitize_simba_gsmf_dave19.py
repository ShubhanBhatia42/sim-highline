import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1901.10203"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "mfssfr_m100n1024.pdf"
ZLABEL = [("z=5.9", 5.9), ("z=2", 2.0), ("z=4", 4.0), ("z=1", 1.0), ("z=3", 3.0), ("z=0.1", 0.1)]
GREEN, BLUE, RED = (0.0, 0.5, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
DEF = {"massDefinition": "caesar-6dfof-galaxy-total", "imf": "chabrier03", "cosmology": {"H0": 68, "Om": 0.3}, "densityFrame": "unspecified", "population": "all"}
AX = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)",
      "yDefinition": "log10 galaxy stellar mass function (axis label Phi [Mpc^-3]; per-dex normalisation and comoving frame not stated)", "yUnit": "log10(Mpc^-3)"}


def near(c, t):
    return c is not None and all(abs(a - b) < 0.01 for a, b in zip(c, t))


page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)
assert len(fr) == 6
fx_col = {}
for i in (4, 5):
    fx, _fy, c = vf.calibrate(page, fr[i], ysign=-1)
    assert [v for _, v in c["xTicks"]] == [9.0, 10.0, 11.0, 12.0]
    fx_col[round(fr[i].x0)] = fx
words = page.get_text("words")
records = []
for i, (label, z) in enumerate(ZLABEL):
    r = fr[i]
    assert any(w[4] == label and r.x0 <= w[0] <= r.x1 and r.y0 <= w[1] <= r.y1 for w in words), label
    fx = fx_col[round(r.x0)]
    _fx, fy, c = vf.calibrate(page, r, fx=fx, ysign=-1)
    ys = [v for _, v in c["yTicks"]]
    assert len(ys) >= 4 and all(a - b == 1 for a, b in zip(ys, ys[1:])), (label, ys)
    xlo, xhi = fx(r.x0), fx(r.x1)
    curves = {}
    for cu in vf.curves(page, r, fx, fy, min_items=3):
        if (cu["width"] or 0) != 1.5:
            continue
        key = "total" if near(cu["color"], GREEN) and cu["dashes"] == "[] 0" else "sf" if near(cu["color"], BLUE) else "q" if near(cu["color"], RED) else None
        if key:
            curves[key] = [(x, y) for x, y in cu["points"] if xlo - 1e-6 <= x <= xhi + 1e-6]
    assert set(curves) == {"total", "sf", "q"}, (label, set(curves))
    band = []
    for d in page.get_drawings():
        if d["fill"] is not None and near(d["fill"], GREEN) and d["rect"].intersects(r) and all(it[0] == "l" for it in d["items"]) and len(d["items"]) > 6:
            band += [(fx(p.x), fy(p.y)) for it in d["items"] for p in (it[1], it[2])]
    assert band, label
    tot = []
    for x, y in curves["total"]:
        ys_at = [by for bx, by in band if abs(bx - x) < 0.004]
        assert len(ys_at) >= 2, (label, x)
        tot.append({"x": round(x, 3), "y": round(y, 4), "yLow": round(min(ys_at), 4), "yHigh": round(max(ys_at), 4)})
    assert all(p["yLow"] <= p["y"] + 0.01 <= p["yHigh"] + 0.02 for p in tot), label
    common = dict(source="SIMBA", relation="gsmf", z=z, axes=AX, citation=f"Dave et al. 2019, MNRAS 486, 2827, Fig. 4 (arXiv source numbering), {label} panel", doi="10.1093/mnras/stz937",
                  url=f"https://arxiv.org/abs/{ARXIV}", figure="Figure 4", panel=label, sha=sha, member=f"{PDF.name}",
                  calib="x: labelled ticks 9-12 from the bottom-row panels (shared columns); y: each panel's own labelled ticks; labels asserted",
                  calibration="target" if z <= 0.1 else "prediction")
    records.append(vf.record(
        rid=f"dave19.simba-m100n1024.gsmf.z{z:g}", run="m100n1024 (all galaxies)", points=tot, population="all galaxies", interval="uncertainty",
        warning=f"Curve vertices and jackknife band (8 sub-octants) read from the vector paths of Dave et al. 2019 Fig. 4 ({label}); no table exists. Vertices outside the plotted mass range are clipped.",
        definitions=dict(DEF), **common))
    for key, name, crit in (("sf", "central star-forming", "sSFR above 10^(-1.8+0.3z) Gyr^-1"), ("q", "central quenched", "sSFR below 10^(-1.8+0.3z) Gyr^-1")):
        pts = curves[key]
        records.append(vf.record(
            rid=f"dave19.simba-m100n1024.gsmf-{key}.z{z:g}", run=f"m100n1024 ({name} centrals)", points=pts, population=f"{name} galaxies (centrals only)",
            warning=f"Dashed curve of Dave et al. 2019 Fig. 4 ({label}) for {name} central galaxies; no table exists. Centrals only, so it does not sum to the all-galaxy curve; vertices outside the plotted mass range are clipped.",
            definitions={**DEF, "population": "centrals", "quenchingCriterion": crit}, **common))
assert len(records) == 18
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dave19-simba-gsmf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} SIMBA GSMF records (total with jackknife band, SF and Q centrals) from Dave+19 vector paths")
