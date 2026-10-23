"""Blank et al. 2019 (NIHAO black holes, arXiv:1906.06955) z = 0 per-galaxy points from the paper's table of galaxies (label tab:galaxies, library.tex of the arXiv source): halo mass M200, stellar mass M* and black hole mass M_BH of the 50 galaxies simulated with black holes.
This replaces the z = 0 records blank19.nihao-bh.bh-galaxies.z0 (Fig. 3) and blank19.nihao-bh.shmr-galaxies.z0 (Fig. 1) that had been read from the figures (scripts/digitize_nihao_blank19.py) on the belief that no table is published. Only z = 0 is tabulated, so the z = 1, 2, 4 records and the fit lines stay as they are.
The records are replaced in place in OUT (the other records of the file are kept). Run: python3 scripts/ingest_nihao_bh_blank19_table.py [OUT]"""
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "1906.06955"
DOI = "10.1093/mnras/stz1688"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "curves" / "blank19-nihao.json"
RETRIEVED = "2026-10-18"
TEX_SHA = "95428970f12d147e24bc0d1d62a6aae1081ce15f3b2c203da1d0b863e5d76db8"
FIG1_XMAX = 13.477   # right edge of the plotted M200 axis of Fig. 1 (plot_msmhx4.eps, panel z=0), from the tick calibration of the figure

SRC = vf.fetch_arxiv(ARXIV)
raw = (SRC / "library.tex").read_bytes()
assert hashlib.sha256(raw).hexdigest() == TEX_SHA, "library.tex changed in the arXiv source"
lines = raw.decode(errors="ignore").split("\n")
flat = " ".join(" ".join(lines).split())

# the table: blocks of rows separated by \hline (5 original with BH, the same 5 without BH, 7 new 60 Mpc, 38 new 90 Mpc, 6 without BH)
start = next(i for i, l in enumerate(lines) if "\\label{tab:galaxies}" in l)
end = next(i for i in range(start, len(lines)) if "\\end{tabular}" in lines[i])
assert "log \\left( M_{200} [\\mathrm{M}_{\\sun}] \\right)" in lines[start + 2] and "M_{\\star} [\\mathrm{M}_{\\sun}]" in lines[start + 2] and "M_{\\mathrm{BH}} [\\mathrm{M}_{\\mathrm{\\sun}}]" in lines[start + 2]
blocks, cur = [], []
for i in range(start + 3, end):
    m = re.match(r"\s*(g[\d.]+e\d+)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*([\d.]+)\s*&\s*([\d.]+)\s*&\s*(-|[\d.]+)\s*\\\\", lines[i])
    if m:
        cur.append(dict(line=i + 1, name=m[1], m200=float(m[5]), mstar=float(m[6]), mbh=None if m[7] == "-" else float(m[7])))
    elif lines[i].strip().startswith("\\hline") and cur:
        blocks.append(cur)
        cur = []
if cur:
    blocks.append(cur)
assert [len(b) for b in blocks] == [5, 5, 7, 38, 6] and [b[0]["mbh"] is not None for b in blocks] == [True, False, True, True, False]
rows = [r for b in blocks for r in b]
bh = [r for r in rows if r["mbh"] is not None]

# numbers printed in the paper's text that the table must reproduce
for q in ("In total we have 50 galaxies with black hole feedback and 11 galaxies without black hole feedback",
          "We take five galaxies from the original NIHAO suite", "we additionally take seven new galaxies", "We then take 38 new galaxies",
          "resimulate five galaxies from the original NIHAO sample with black hole physics, which have $z=0$ halo masses from $8 \\times 10^{11}$ to $3 \\times 10^{12}\\,\\mathrm{M}_{\\sun}$"):
    assert q in flat, q
assert len(bh) == 50 and len(rows) - len(bh) == 11 and len(blocks[0]) == 5 and len(blocks[2]) == 7 and len(blocks[3]) == 38
o5 = [10 ** r["m200"] for r in blocks[0]]
assert round(min(o5) / 1e11) == 8 and round(max(o5) / 1e12) == 3, (min(o5), max(o5))   # 8.3e11 ... 3.1e12 = "from 8e11 to 3e12"
assert abs(max(r["m200"] for r in bh) - 13.55) < 1e-9 and round(10 ** 13.55 / 1e13) == 4   # "up to 4e13"

DEF = {"imf": "chabrier03", "cosmology": {"H0": 67.1, "Om": 0.3175}, "massDefinition": "sphere-0.2R200"}
POP = "individual zoom galaxies (not volume complete)"
SPEC = [
    dict(rid="blank19.nihao-bh.bh-galaxies.z0", relation="bh", fig="Fig. 3", panel="z=0",
         axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 black hole mass", "yUnit": "log10(Msun)"},
         defs={**DEF, "bhMassMethod": "intrinsic", "population": "zoom-centrals"}, pts=[(r["mstar"], r["mbh"]) for r in bh], cols="x = log(M_star), y = log(M_BH)"),
    dict(rid="blank19.nihao-bh.shmr-galaxies.z0", relation="shmr", fig="Fig. 1", panel="z=0",
         axes={"xDefinition": "log10 halo mass M200 (200x critical density)", "xUnit": "log10(Msun)", "yDefinition": "log10 stellar-to-halo mass ratio, M*/M200", "yUnit": "dex"},
         defs={**DEF, "haloMassDefinition": "M200crit", "haloMassHistory": "current", "population": "zoom-centrals"}, pts=[(r["m200"], r["mstar"] - r["m200"]) for r in bh], cols="x = log(M_200), y = log(M_star) - log(M_200)"),
]

old = {}
if OUT.exists():
    old = {r["id"]: r for r in json.loads(OUT.read_text())["records"]}
records = []
for s in SPEC:
    pts = sorted((round(a, 4), round(b, 4)) for a, b in s["pts"])
    shmr = s["relation"] == "shmr"
    r = vf.record(
        rid=s["rid"], source="NIHAO zoom suite", run="NIHAO zoom sample with black holes (per galaxy)", relation=s["relation"], z=0, axes=s["axes"], points=pts, population=POP,
        warning=(f"Per-galaxy values from the table of galaxies of Blank et al. 2019 (label tab:galaxies, arXiv source library.tex), the 50 galaxies simulated with black holes; values as printed to 2 decimals, the numbers plotted in {s['fig']} (z=0 panel). "
                 + ("The ratio M*/M200 is computed here as log M* minus log M200 from the two rounded table columns (rounding error up to 0.01 dex). Two galaxies (g3.26e13, g3.89e13; log M200 = 13.51, 13.55) lie beyond the right edge of the plotted M200 axis of Fig. 1 (13.48) and were not drawn there. " if shmr else "")
                 + "Zoom selections are not volume complete, so the sample is not rankable. Stellar mass is the mass of all stars within 0.2 R200."),
        definitions=s["defs"], citation=f"Blank et al. 2019, MNRAS 487, 5476, table of galaxies and their properties (label tab:galaxies, arXiv source), the values plotted in {s['fig']}, {s['panel']} panel",
        doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure=None, panel=None, sha=TEX_SHA, member=f"library.tex, table tab:galaxies (rows at lines {rows[0]['line']}-{rows[-1]['line']} of the arXiv source)", calib="", calibration="unknown",
        interval="scatter", connect=False, strict=False, tier="published-table", uncertainty=0.0, retrieved=RETRIEVED, rankable=False, scatter=None,
        note="Values of the paper's table of galaxies, equal to the earlier figure read to <0.01 dex; not rankable because the zoom sample is not volume complete.")
    for k in ("figure", "panel", "axisCalibrationPixels", "digitizationUncertaintyDex"):
        r["provenance"].pop(k, None)
    r["provenance"]["definitionFills"] = ["blank19-nihao-mass"]
    r["provenance"]["extractionMethod"] = f"parsed from the arXiv LaTeX table 'tab:galaxies' (61 rows, the 50 with a black hole mass used): {s['cols']}"
    o = old.get(s["rid"])
    if o and o["provenance"]["tier"] == "digitized-figure":
        P = np.array([[p["x"], p["y"]] for p in o["representation"]["points"]])
        T = np.array(pts)
        C = np.hypot(P[:, None, 0] - T[None, :, 0], P[:, None, 1] - T[None, :, 1])
        i, j = linear_sum_assignment(C)
        assert (C.argmin(1) == j).all()
        d = np.abs(P[i] - T[j])
        left = sorted(set(range(len(T))) - set(j))
        print(f"{s['rid']}: {len(P)} digitized vs {len(T)} table points; max |dx| {d[:, 0].max():.4f} |dy| {d[:, 1].max():.4f}, median |dx| {np.median(d[:, 0]):.4f} |dy| {np.median(d[:, 1]):.4f}; max/median distance {C[i, j].max():.4f}/{np.median(C[i, j]):.4f} dex; table points without a digitized partner: {[T[k].tolist() for k in left]}")
        assert C[i, j].max() < 0.01
        assert all(T[k][0] > FIG1_XMAX for k in left) if shmr else not left
    records.append(r)

doc = json.loads(OUT.read_text()) if OUT.exists() else {"schemaVersion": "1.0.0", "records": []}
new = {r["id"]: r for r in records}
doc["records"] = [new.pop(r["id"], r) for r in doc["records"]] + list(new.values())
OUT.write_text(json.dumps(doc, indent=2) + "\n")
print(f"Replaced {len(records)} NIHAO black-hole z=0 per-galaxy records from the paper's table of galaxies")
