"""Dutton et al. 2017 (NIHAO XII, arXiv:1610.06375) per-galaxy Tully-Fisher points from the data table of the paper (label tab:mvall, continued as tab:fits): the arXiv source \\input's table1a.txt and table1b.txt, 83 NIHAO galaxies.
This replaces the per-galaxy records dutton17.nihao.{btfr-all-baryons,btfr-stars-neutral-gas,stfr-stars}.galaxies.z0 that had been read from the vector paths of Fig. 4 (scripts/digitize_nihao_tf_dutton17.py) on the belief that no table is published. The three .fit.z0 records are left as they are (the table gives the points, not the plotted fit line).
The records are replaced in place in OUT (the other records of the file are kept). Run: python3 scripts/ingest_nihao_tf_dutton17_table.py [OUT]"""
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "1610.06375"
DOI = "10.1093/mnras/stx458"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "curves" / "dutton17-nihao-tf.json"
RETRIEVED = "2026-10-18"
SHA = {"table1a.txt": "20b8cee830587a17db8fd132167d0e970b7f7740986eaca33d53328663f229c7",
       "table1b.txt": "9736eafa3a644df17b104ee6fd3a198e8886b397f0b507f91916043595d7a234",
       "nihaoXII_2017.03.07.tex": "d10d98b5aeab1264989baecd783bc2ace88c98fdaa0992aa8ef559e454df9e6d"}

SRC = vf.fetch_arxiv(ARXIV)
for name, sha in SHA.items():
    assert hashlib.sha256((SRC / name).read_bytes()).hexdigest() == SHA[name], f"{name} changed in the arXiv source"
tex = " ".join((SRC / "nihaoXII_2017.03.07.tex").read_text(errors="ignore").split())

# the table: ID, then columns (2)..(11) = log R_HI, log V_HI, log Vmax_DMO, log V200, log V200_DMO, log M_star, log M_neut, log M_gal, log M_bar, log M_bar_DMO
COL = {"VHI": 1, "Mstar": 5, "Mneut": 6, "Mgal": 7, "Mbar": 8}
for q in ("column (3) circular velocity measured at the \\HI\\, radius", "column (7) stellar mass, column (8) neutral gas mass, column (9) galaxy baryonic mass (column 7 plus column 8)",
          "column (10) baryonic mass inside the virial radius of the hydro simulation"):
    assert q in tex, q
rows = []
for fname in ("table1a.txt", "table1b.txt"):
    for line in (SRC / fname).read_text().splitlines():
        if line.strip():
            cells = [c.strip() for c in line.replace("\\\\", "").split("&")]
            assert len(cells) == 11, line
            rows.append((cells[0], [float(c) for c in cells[1:]]))
assert len(rows) == 83 and len({r[0] for r in rows}) == 83
A = np.array([r[1] for r in rows])
assert np.abs(np.log10(10 ** A[:, COL["Mstar"]] + 10 ** A[:, COL["Mneut"]]) - A[:, COL["Mgal"]]).max() < 0.002   # column 9 = column 7 plus column 8, as the caption says

# numbers printed in the paper's text: slopes (and jackknife errors) of the straight-line fits of log M on log V_HI by least squares, "uncertainties on a and b using jackknife re-sampling"
TEXT = {"Mbar": (3.11, 0.07, "The full baryonic mass has slope of $3.11\\pm0.07$"), "Mgal": (3.97, 0.09, "the `observable' baryons have a slope of $3.97\\pm0.09$"),
        "Mstar": (5.04, 0.17, "Simulations have a slope of 5.04$\\pm0.17$")}
slopes = {}
for key, (b, err, quote) in TEXT.items():
    assert quote in tex, quote
    x, y = A[:, COL["VHI"]], A[:, COL[key]]
    slope = np.polyfit(x, y, 1)[0]
    leave_one_out = np.array([np.polyfit(np.delete(x, i), np.delete(y, i), 1)[0] for i in range(83)])
    jk = np.sqrt(82 / 83 * np.sum((leave_one_out - leave_one_out.mean()) ** 2))
    assert round(slope, 2) == b and round(jk, 2) == err, (key, slope, jk, b, err)
    slopes[key] = round(float(slope), 3)
assert 20 <= 10 ** A[:, COL["VHI"]].min() <= 21 and 230 <= 10 ** A[:, COL["VHI"]].max() <= 240   # "20 <~ V_HI <~ 240 km/s" in the text (the velocity range probed)

DEF = {"imf": "chabrier03", "cosmology": {"H0": 67.1, "Om": 0.3175}}
POP = "individual zoom galaxies (not volume complete)"
VAXIS = "log10 circular velocity at the HI radius (R_HI, enclosing 90% of HI flux)"
SPEC = [
    dict(rid="dutton17.nihao.btfr-all-baryons.galaxies.z0", run="NIHAO zoom sample (per galaxy, all-baryons)", relation="btfr", panel="upper left", key="Mbar",
         axes={"xDefinition": VAXIS, "xUnit": "log10(km/s)", "yDefinition": "log10 total baryonic mass within the virial radius", "yUnit": "log10(Msun)"}, mdef="all-baryons-within-virial-radius",
         cols="x = column (3) log V_HI, y = column (10) log M_bar"),
    dict(rid="dutton17.nihao.btfr-stars-neutral-gas.galaxies.z0", run="NIHAO zoom sample (per galaxy, stars+neutral-gas)", relation="btfr", panel="upper right", key="Mgal",
         axes={"xDefinition": VAXIS, "xUnit": "log10(km/s)", "yDefinition": "log10 stars plus neutral gas mass", "yUnit": "log10(Msun)"}, mdef="stars-plus-neutral-gas",
         cols="x = column (3) log V_HI, y = column (9) log M_gal"),
    dict(rid="dutton17.nihao.stfr-stars.galaxies.z0", run="NIHAO zoom sample (per galaxy, stars)", relation="stfr", panel="lower left", key="Mstar",
         axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": VAXIS, "yUnit": "log10(km/s)"}, mdef="stellar mass",
         cols="x = column (7) log M_star, y = column (3) log V_HI"),
]

old = {}
if OUT.exists():
    old = {r["id"]: r for r in json.loads(OUT.read_text())["records"]}
records = []
for s in SPEC:
    v, m = A[:, COL["VHI"]], A[:, COL[s["key"]]]
    pts = sorted((round(float(a), 3), round(float(b), 3)) for a, b in (zip(m, v) if s["relation"] == "stfr" else zip(v, m)))
    r = vf.record(
        rid=s["rid"], source="NIHAO zoom suite", run=s["run"], relation=s["relation"], z=0, axes=s["axes"], points=pts, population=POP,
        warning=("Per-galaxy values from the data table of Dutton et al. 2017 (83 NIHAO galaxies; arXiv source files table1a.txt and table1b.txt, label tab:mvall), the numbers plotted as black filled circles in the "
                 f"{s['panel']} panel of Fig. 4 (arXiv source numbering). Stars and neutral gas (M_neut = 1.33 M_HI) are measured inside 0.2 R200; M_bar is all stars and gas within R200. "
                 "Haloes are selected uniformly in log halo mass from ~10 to ~12 without reference to merger history, concentration or spin, but the zoom sample is not volume complete, so the points are context, not a rankable prediction."),
        definitions={**DEF, "massDefinition": s["mdef"], "velocityDefinition": "circular velocity at R_HI", "population": "zoom-centrals"},
        citation=f"Dutton et al. 2017 (NIHAO XII), MNRAS 467, 4937, data table (label tab:mvall, arXiv source) of the values plotted in Fig. 4 (arXiv source numbering), {s['panel']} panel",
        doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure=None, panel=None, sha=SHA["table1a.txt"],
        member="table1a.txt and table1b.txt (\\input into nihaoXII_2017.03.07.tex; rows 1-52 and 53-83)", calib="", calibration="unknown",
        interval="scatter", connect=False, strict=False, tier="published-table", uncertainty=0.0, retrieved=RETRIEVED, rankable=False,
        scatter={"fitSlopeMeasured": slopes[s["key"]], "fitSlopeStatedInText": TEXT[s["key"]][0], "fitSlopeDefinition": "slope b of log10 M against log10 V_HI, least squares on the table"},
        note="Values of the paper's data table, equal to the earlier figure read (Fig. 4 vector paths) to <0.01 dex; not rankable because the zoom sample is not volume complete.")
    for k in ("figure", "panel", "axisCalibrationPixels", "digitizationUncertaintyDex"):
        r["provenance"].pop(k, None)
    r["provenance"]["checksumSha256Table1b"] = SHA["table1b.txt"]
    r["provenance"]["extractionMethod"] = f"parsed from the arXiv LaTeX table files (83 rows, values as printed to 3 decimals): {s['cols']}"
    # per-point comparison with the digitized record being replaced (nearest-neighbour assignment in the plane)
    o = old.get(s["rid"])
    if o and o["provenance"]["tier"] == "digitized-figure":
        P = np.array([[p["x"], p["y"]] for p in o["representation"]["points"]])
        T = np.array(pts)
        C = np.hypot(P[:, None, 0] - T[None, :, 0], P[:, None, 1] - T[None, :, 1])
        i, j = linear_sum_assignment(C)
        assert len(P) == len(T) == 83 and (C.argmin(1) == j).all()
        d = np.abs(P[i] - T[j])
        print(f"{s['rid']}: max |dx| {d[:, 0].max():.4f} |dy| {d[:, 1].max():.4f}, median |dx| {np.median(d[:, 0]):.4f} |dy| {np.median(d[:, 1]):.4f}; max/median distance {C[i, j].max():.4f}/{np.median(C[i, j]):.4f} dex")
        assert C[i, j].max() < 0.01
    records.append(r)

doc = json.loads(OUT.read_text()) if OUT.exists() else {"schemaVersion": "1.0.0", "records": []}
new = {r["id"]: r for r in records}
doc["records"] = [new.pop(r["id"], r) for r in doc["records"]] + list(new.values())
OUT.write_text(json.dumps(doc, indent=2) + "\n")
print(f"Replaced {len(records)} NIHAO Tully-Fisher per-galaxy records from the paper's table; fit slopes {slopes} reproduce the printed 3.11, 3.97, 5.04")
