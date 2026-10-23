"""THESAN-1 cosmic star formation rate density from the file released by the THESAN project (https://www.thesan-project.com/thesan/quantities/sfrd_Thesan1.dat; the data page https://www.thesan-project.com/thesan/data.html assigns it to Kannan et al. 2022, arXiv:2110.00584).
This replaces kannan22.thesan.sfrd.t1, read from the vector paths of the paper's figure (scripts/digitize_thesan_kannan22_uvlf_sfrd.py), by the released numbers. The sibling uvlf_Thesan1.dat is NOT used (its definition is unknown and it does not match the digitized UVLF).
Nothing is written if the repository already holds a THESAN-1 sfrd record of tier official-table with another id (it would be a duplicate). The record is replaced in place in OUT. Run: python3 scripts/ingest_thesan1_sfrd_kannan22.py [OUT]"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "2110.00584"
DOI = "10.1093/mnras/stab3710"
URL = "https://www.thesan-project.com/thesan/quantities/sfrd_Thesan1.dat"
FILE_SHA = "7cb854c975c9ad218f28e77cf8c169f71c75d2d36f9521edcbaeebcf3805f509"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "curves" / "kannan22-thesan-uvlf-sfrd.json"
RID = "kannan22.thesan.sfrd.t1"
RETRIEVED = "2026-10-18"

# is the quantity already held as an official-table record (any file next to OUT)?
for f in sorted(OUT.parent.glob("*.json")):
    for r in json.loads(f.read_text()).get("records", []):
        if r["source"] == "THESAN-1" and r["relation"] == "sfrd" and r["provenance"]["tier"] == "official-table" and r["id"] != RID:
            sys.exit(f"{r['id']} ({f.name}) already holds THESAN-1 sfrd as official-table: {RID} would be a duplicate")

raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
assert hashlib.sha256(raw).hexdigest() == FILE_SHA, "the data file changed: " + hashlib.sha256(raw).hexdigest()
text = raw.decode().splitlines()
assert text[0] == "#z SFRD [Msun/yr/Mpc^3]"
data = np.array([[float(v) for v in line.split()] for line in text[1:] if line.strip() and not line.startswith("#")])
data = data[np.argsort(data[:, 0])]
z, sfrd = data[:, 0], data[:, 1]
dz = np.diff(z)
assert len(z) == 49 and (sfrd > 0).all() and dz.min() > 0.1937 and dz.max() < 0.1940
# the 49 equally spaced redshifts are the centres of 49 bins of width 0.19388 between z = 5.5 and 15 (inferred from the numbers, not stated in the file)
assert abs(z[0] - dz.mean() / 2 - 5.5) < 1e-3 and abs(z[-1] + dz.mean() / 2 - 15.0) < 1e-3

# the paper: final redshift 5.5, the figure's axis label says comoving, "all the SF in the simulation volume"
SRC = vf.fetch_arxiv(ARXIV)
tex = " ".join((SRC / "thesan.tex").read_text(errors="ignore").split())
for q in ("from $z = 20$ down to $z = 5.5$", "The simulations on the other hand include all the SF in the simulation volume, down to the resolution limit",
          "the low resolution simulations show an order of magnitude lower SFR rate at high redshifts"):
    assert q in tex, q
words = [w[4] for w in pymupdf.open(SRC / "figures" / "sfrbin.pdf")[0].get_text("words")]
assert "cMpc−3])" in words and "log(ρSFR" in words   # y-axis label of the figure: log(rho_SFR [Msun yr-1 cMpc-3])

pts = [{"x": float(a), "y": round(float(np.log10(b)), 4)} for a, b in zip(z, sfrd)]
r = vf.record(
    rid=RID, source="THESAN-1", run="THESAN-1", relation="sfrd", z=10, z_range=(float(z[0]), float(z[-1])), z_nominal=10,
    axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic star-formation rate density of all gas cells in the box", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
    points=[(p["x"], p["y"]) for p in pts], population="all galaxies in the box",
    warning=("Total cosmic SFR density of THESAN-1 versus redshift from the file released by the THESAN project (49 redshifts, which are the centres of equal bins of 0.194 in z between z = 5.5 and 15; the file header gives only 'SFRD [Msun/yr/Mpc^3]'). "
             "The unit is comoving: the file equals the total curve of the paper's figure, whose axis is labelled cMpc-3. The halo-mass-split contributions are not in the file. The paper notes the SFRD is converged below z=8 only; lower-resolution runs fall an order of magnitude short at high z."),
    definitions={"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "densityFrame": "comoving", "sfrIndicator": "instantaneous SFR of star-forming gas", "population": "all galaxies",
                 "sfrIntegrationLimit": "total over all halos in the box", "dustCorrection": "none"},
    citation=f"Kannan et al. 2022, MNRAS 511, 4005 (arXiv:{ARXIV}), THESAN data release file sfrd_Thesan1.dat (assigned to Kannan et al. 2022 on https://www.thesan-project.com/thesan/data.html), evolution of the star formation rate density",
    doi=DOI, url=URL, figure=None, panel=None, sha=FILE_SHA, member="sfrd_Thesan1.dat", calib="", calibration="prediction", interval="unspecified", connect=True,
    tier="official-table", uncertainty=0.0, retrieved=RETRIEVED, rankable=False, scatter=None,
    note="Numbers released by the THESAN project; they agree with the earlier figure read to a median of 0.003 dex. Not rankable: single 95.5 cMpc box, converged only below z=8, aggregation and bin averaging not stated in the file.")
for k in ("figure", "panel", "axisCalibrationPixels", "digitizationUncertaintyDex"):
    r["provenance"].pop(k, None)
r["representation"]["points"] = pts                                            # redshifts as released (4 decimals)
r["domain"] = {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]}
r["provenance"]["definitionFills"] = ["kannan22-thesan-sfrd"]
r["provenance"]["extractionMethod"] = "released two-column ASCII file read as is: column 1 = redshift, column 2 = SFRD [Msun/yr/Mpc^3], converted to log10; 49 rows, sorted by increasing redshift"

doc = json.loads(OUT.read_text()) if OUT.exists() else {"schemaVersion": "1.0.0", "records": []}
old = {x["id"]: x for x in doc["records"]}.get(RID)
if old and old["provenance"]["tier"] == "digitized-figure":
    P = np.array([[p["x"], p["y"]] for p in old["representation"]["points"]])
    yf = np.log10(sfrd)
    inside = (z >= P[0, 0]) & (z <= P[-1, 0])
    d_new = np.abs(yf[inside] - np.interp(z[inside], P[:, 0], P[:, 1]))            # each released point against the digitized curve
    m = (P[:, 0] >= z[0]) & (P[:, 0] <= z[-1])
    d_old = np.abs(P[m, 1] - np.interp(P[m, 0], z, yf))                           # each digitized vertex against the released curve
    print(f"{RID}: released points inside the digitized range {inside.sum()}/49: max {d_new.max():.4f} median {np.median(d_new):.4f} dex; digitized vertices inside the released range {m.sum()}/{len(P)}: max {d_old.max():.4f} median {np.median(d_old):.4f} dex; "
          f"digitized vertices outside the released range: {P[~m].tolist()}")
    assert d_new.max() < 0.02 and np.median(d_new) < 0.005
doc["records"] = [r if x["id"] == RID else x for x in doc["records"]] if old else doc["records"] + [r]
OUT.write_text(json.dumps(doc, indent=2) + "\n")
print(f"Replaced {RID} by the released THESAN-1 SFRD file ({len(pts)} points, z {z[0]:.4f} to {z[-1]:.4f})")
