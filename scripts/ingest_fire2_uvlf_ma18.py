"""Ma et al. 2018 (arXiv:1706.06605) FIRE-2 predicted UV luminosity functions at z = 6, 8, 10, 12, from the numerical files the authors released with the paper (hiz_smf_lf.zip, files LF_UV_sim_z06/08/10/12.txt: M_1500 and log phi per row).
This replaces the earlier records of the same ids that had been read from the paper's figure (scripts/digitize_fire2_uvlf_ma18.py, removed): the figure read agreed with these files to 0.0005. The values are cross-checked against the paper's own appendix table (two decimals) in the LaTeX source.
The archive is served over plain http only (the host's certificate is rejected by current clients), so its SHA-256 is asserted. Run: python3 scripts/ingest_fire2_uvlf_ma18.py"""
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "1706.06605"
DOI = "10.1093/mnras/sty1024"
URL = "http://www.tapir.caltech.edu/~xchma/data/hiz_smf_lf.zip"
ZIP_SHA = "94ea32b37b795ad9b19c3e9abfa5e33e1126edb2362e34a19030752bc3b20a91"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "ma18-fire2-uvlf.json"
RETRIEVED = "2026-10-21"

raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
assert hashlib.sha256(raw).hexdigest() == ZIP_SHA, "the archive changed: " + hashlib.sha256(raw).hexdigest()
zf = zipfile.ZipFile(io.BytesIO(raw))
members = {Path(n).name: n for n in zf.namelist()}

# the paper's own appendix table (two decimals): columns log M*, log phi*, M1500, log phi1500, ...
SRC = vf.fetch_arxiv(ARXIV)
tex = next(SRC.glob("*.tex")).read_text(errors="ignore")
body = tex[tex.index("Stellar mass functions and luminosity functions}\n\\label{app:smf}"):]
blocks = re.split(r"\\multicolumn\{8\}\{c\}\{\$z=(\d+)\$\}", body)
table = {}
for z, chunk in zip(blocks[1::2], blocks[2::2]):
    rows = []
    for line in chunk.split("\n"):
        m = re.match(r"\s*-?\d+\.\d+\s*&\s*-?\d+\.\d+\s*&\s*(-?\d+\.\d+)\s*&\s*(-?\d+\.\d+)\s*&", line)
        if m:
            rows.append((float(m.group(1)), float(m.group(2))))
    table[int(z)] = rows

records = []
for z in (6, 8, 10, 12):
    name = f"LF_UV_sim_z{z:02d}.txt"
    data = np.loadtxt(io.StringIO(zf.read(members[name]).decode()))
    pts = [(round(float(x), 4), round(float(y), 4)) for x, y in data]
    assert len(pts) == len(table[z]), (z, len(pts), len(table[z]))
    assert all(abs(a[0] - b[0]) < 0.006 and abs(a[1] - b[1]) < 0.006 for a, b in zip(pts, table[z])), (z, pts, table[z])   # the released file and the paper's table are the same numbers
    assert all(a[0] < b[0] for a, b in zip(pts, pts[1:])) and all(a[1] < b[1] for a, b in zip(pts, pts[1:])), z
    r = vf.record(
        rid=f"ma18.fire2.uvlf.z{z:g}", source="FIRE-2", run="FIRE-2 high-z zoom sample (volume-weighted)", relation="uvlf", z=float(z),
        axes={"xDefinition": "absolute magnitude at rest-frame 1500 A (intrinsic, no dust attenuation)", "xUnit": "mag (AB)", "yDefinition": "log10 luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"},
        points=sorted(pts), population="central galaxies of the zoom-in sample, weighted to the halo mass function", interval="unspecified", connect=False, scatter=True,
        definitions={"imf": "kroupa01", "cosmology": {"H0": 68, "Om": 0.31}, "densityFrame": "comoving", "uvBand": "rest-frame 1500 A", "dustCorrection": "none (intrinsic)", "population": "centrals"},
        citation=f"Ma et al. 2018, MNRAS 478, 1694 (arXiv:{ARXIV}), predicted luminosity functions at 1500 A, z={z:g}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure=None, panel=None, sha=ZIP_SHA, member=f"{name} in hiz_smf_lf.zip ({URL}; served over http only)", calib="", calibration="prediction",
        warning="Open symbols of the paper's figure: the luminosity function derived from the weighted FIRE-2 zoom-in sample (the dashed model lines are not stored). Magnitudes are intrinsic: no dust attenuation, BPASS v2 binary models with a Kroupa IMF. A zoom-in sample, not a periodic volume, so not directly rankable.",
        tier="official-table", uncertainty=0.0, retrieved=RETRIEVED, rankable=False, strict=False,
        note="Numerical file released by the authors; equal to the paper's appendix table (checked row by row to its two decimals) and to the earlier figure read to 0.0005.")
    r["epoch"]["mode"] = "published-epoch"
    for k in ("figure", "panel", "axisCalibrationPixels", "digitizationUncertaintyDex"):
        r["provenance"].pop(k, None)
    r["provenance"]["extractionMethod"] = "numerical data file released by the authors, read as is"
    records.append(r)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIRE-2 UV luminosity function records from the released files of Ma+18")
