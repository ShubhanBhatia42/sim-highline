import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1510.05645"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = next(SRC.rglob("size_mass.pdf"))
BINS = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0)]
POP = {(0.2, 0.13, 0.53): ("active", "active (sSFR above the redshift-dependent limit)"), (0.53, 0.13, 0.33): ("passive", "passive (sSFR below the redshift-dependent limit)")}
BAND = {"active": (0.2, 0.13, 0.53), "passive": (0.8, 0.4, 0.47)}
AX = {"xDefinition": "log10 stellar mass (3D 30 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": "log10 physical 3D stellar half-mass radius R50 of bound stars (100 pkpc sphere)", "yUnit": "log10(kpc)"}


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)
assert len(fr) == 4
fx, xt = vf.axis_fit(page, fr[2], "x")
fy, yt = vf.axis_fit(page, fr[0], "y")
assert [v for _, v in xt] == [9.0, 10.0, 11.0, 12.0] and [v for _, v in yt] == [1.5, 1.0, 0.5, 0.0]
words = page.get_text("words")
drs = page.get_drawings()
records = []
for i, ((lo, hi), r) in enumerate(zip(BINS, fr)):
    col = i % 2
    xr = vf.shifted(fx, fr[2 + col].x0 - fr[2].x0)
    fyr = vf.shifted(fy, r.y0 - fr[0].y0)
    nums = sorted(float(w[4]) for w in words if re.fullmatch(r"\d\.\d", w[4]) and r.x0 + 40 < (w[0] + w[2]) / 2 < r.x1 and r.y0 < (w[1] + w[3]) / 2 < r.y0 + 60)
    assert nums[:2] == [lo, hi], (i, nums)
    ztag = f"{lo:g}-{hi:g}"
    zmid = (lo + hi) / 2
    curves = [c for c in vf.curves(page, r, xr, fyr, min_items=6) if c["width"] == 2.0 and c["dashes"] == "[] 0" and any(near(c["color"], k) for k in POP)]
    assert len(curves) == 2, (i, len(curves))
    for c in curves:
        pk = next(k for k in POP if near(c["color"], k))
        key, desc = POP[pk]
        line = c["points"]
        band = []
        for d in drs:
            if d["fill"] is not None and near(d["fill"], BAND[key]) and d["rect"].intersects(r) and all(it[0] == "l" for it in d["items"]) and len(d["items"]) >= 14:
                if d["color"] is not None and near(d["color"], BAND[key]):
                    pts = [(xr(p.x), fyr(p.y)) for it in d["items"] for p in (it[1], it[2])]
                    if sum(1 for x, y in pts if any(abs(x - lx) < 0.01 for lx, _ in line)) >= len(pts) * 0.8:
                        band = pts
        assert band, (i, key)
        pts = []
        for x, y in line:
            ys = [py for px, py in band if abs(px - x) < 0.01]
            assert len(ys) >= 2, (i, key, x)
            pts.append({"x": round(x, 3), "y": round(y, 4), "yLow": round(min(ys), 4), "yHigh": round(max(ys), 4)})
        records.append(vf.record(
            rid=f"furlong17.eagle-l100n1504.size-{key}.z{ztag}", source="EAGLE", run=f"Ref-L100N1504 ({key})", relation="size", z=zmid, z_range=(lo, hi), axes=AX, points=pts, population=f"{desc} galaxies", interval="scatter",
            warning=f"Median curve and 16th-84th percentile band read from the vector paths of Furlong et al. 2017 Fig. 1 (size-mass; arXiv source numbering), {lo:g}<z<{hi:g} panel; no table exists. "
                    f"The paper plots redshift bins, so the epoch is recorded as the bin with its midpoint as representative; the exact snapshots combined in a bin are not stated. Bins of 0.2 dex; bins with fewer than 10 galaxies are shown as individual points in the paper and are not extracted. "
                    "Active and passive are split at log10(sSFR_lim/Gyr^-1) = 0.5z - 2.",
            definitions={"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "sizeDefinition": "stellar-half-mass-3d-100pkpc", "population": key,
                         "quenchingCriterion": "log10 sSFR_lim(z)/Gyr^-1 = 0.5z - 2"},
            citation=f"Furlong et al. 2017, MNRAS 465, 722, Fig. (size-mass; arXiv source numbering), {lo:g}<z<{hi:g} panel", doi="10.1093/mnras/stw2740", url=f"https://arxiv.org/abs/{ARXIV}",
            figure="size-mass figure (fig:size_mass)", panel=f"{lo:g}<z<{hi:g}", sha=sha, member=f"{PDF.name} ({key} solid curve with percentile band)",
            calib="x: labelled ticks 9-12 (bottom-left panel, shared columns); y: labelled ticks 0-1.5 (top-left panel, shared rows); labels asserted", calibration="prediction"))
assert len(records) == 8
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "furlong17-eagle-sizes.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE size-mass records (active/passive, 4 redshift bins) from Furlong+17 vector paths")
