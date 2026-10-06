import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1706.06605"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
tex = next(SRC.glob("*.tex")).read_text(errors="ignore")
a = tex.index("Stellar mass functions and luminosity functions}\n\\label{app:smf}")
body = tex[a:]
blocks = re.split(r"\\multicolumn\{8\}\{c\}\{\$z=(\d+)\$\}", body)
table = {}
for z, chunk in zip(blocks[1::2], blocks[2::2]):
    rows = []
    for line in chunk.split("\n"):
        m = re.match(r"\s*(-?\d+\.\d+)\s*&\s*(-?\d+\.\d+)\s*&", line)
        if m:
            rows.append((float(m.group(1)), float(m.group(2))))
    table[int(z)] = rows
assert sorted(table) == list(range(5, 13)), sorted(table)
PUBLISHED = [(5, 3.83, 0.76), (5, 9.85, -4.02), (6, 3.83, 0.87), (6, 9.69, -3.98), (8, 5.29, -0.01), (10, 8.04, -3.44)]
for z, x, y in PUBLISHED:
    assert (x, y) in table[z], (z, x, y)
assert all(len(v) >= 6 and all(r[0] < s[0] for r, s in zip(v, v[1:])) and all(r[1] > s[1] for r, s in zip(v, v[1:])) for v in table.values()), "mass function must fall monotonically"
def mid_slope(rows, lo=4.9, hi=7.6):
    r = [(x, y) for x, y in rows if lo < x < hi]
    mx, my = sum(x for x, _ in r) / len(r), sum(y for _, y in r) / len(r)
    return sum((x - mx) * (y - my) for x, y in r) / sum((x - mx) ** 2 for x, _ in r)


assert abs(mid_slope(table[6]) - (-1.83 + 1)) < 0.2, mid_slope(table[6])
assert abs(mid_slope(table[12]) - (-2.18 + 1)) < 0.35, mid_slope(table[12])
assert mid_slope(table[12]) < mid_slope(table[6])
sha = vf.sha256(next(SRC.glob("*.tex")))
records = []
for z, rows in sorted(table.items()):
    pts = [{"x": x, "y": y} for x, y in rows]
    records.append(vf.record(
        rid=f"ma18.fire2.gsmf.z{z}", source="FIRE-2", run="FIRE-2 high-z zoom sample (volume-weighted)", relation="gsmf", z=float(z), z_range=(z - 0.5, z + 0.5),
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function (Mpc^-3 dex^-1), derived from the zoom sample with volume weights", "yUnit": "log10(Mpc^-3 dex^-1)"},
        points=pts, population="central galaxies in halos above 10^7.5 Msun (weighted zoom sample)",
        warning="Transcribed from the appendix table of Ma et al. 2018 (MNRAS 478, 1694). Computed from all halo snapshots within +-0.5 of the redshift, weighted to represent a cosmological volume and counting only halos above 10^7.5 Msun; "
                "a zoom-in sample, not a periodic volume, so not directly rankable. Epoch recorded as the +-0.5 window around the nominal redshift.",
        definitions={"massDefinition": "stars-within-third-Rmax-masked", "imf": "kroupa01", "cosmology": {"H0": 68, "Om": 0.31}, "densityFrame": "comoving", "population": "centrals"},
        citation="Ma et al. 2018, MNRAS 478, 1694, Table of stellar mass functions (Appendix)", doi="10.1093/mnras/sty1024", url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Appendix table (tbl:smf)", panel=f"z={z}", sha=sha, member="arXiv LaTeX source, appendix table 'Stellar mass functions and luminosity functions' (transcribed)",
        calib="table values, no calibration", tier="published-table", uncertainty=0.0, calibration="prediction", rankable=False,
        note="Spot-checked in the script against published rows (z=5, 6, 8, 10); mass function checked to fall monotonically and the mid-mass slopes to agree with the paper\'s quoted faint-end slopes alpha=-1.83 (z~6) and -2.18 (z~12), as dlogphi/dlogM = alpha+1."))
    records[-1]["provenance"].pop("axisCalibrationPixels", None)
    records[-1]["provenance"].pop("digitizationUncertaintyDex", None)
    records[-1]["provenance"]["extractionMethod"] = "parsed directly from the arXiv LaTeX table"
ALPHA, BETA = 1.58, 7.10
GAMMA, DELTA = -0.14, -1.10
fit = vf.record(
    rid="ma18.fire2.shmr-fit.z5-12", source="FIRE-2", run="FIRE-2 high-z zoom sample (power-law fit)", relation="shmr", z=8.5, z_range=(5.0, 12.0),
    axes={"xDefinition": "log10 halo mass (AHF spherical overdensity, Bryan & Norman virial)", "xUnit": "log10(Msun)", "yDefinition": "log10 stellar-to-halo mass ratio, M*/Mhalo, from log M* = alpha (log Mhalo - 10) + beta", "yUnit": "dex"},
    points=[(7.5, ALPHA * -2.5 + BETA - 7.5), (12.0, ALPHA * 2.0 + BETA - 12.0)], population="central galaxies, all halo snapshots at z=5-12",
    warning="Power-law fit of Ma et al. 2018 (eq. smhm) to the median M*-Mhalo relation of all halo snapshots at z=5-12, valid for 10^7.5 < Mhalo < 10^12 Msun; the paper finds no significant evolution over this range and the median at a given redshift deviates by at most 0.1 dex. "
            f"Dispersion in log M*: sigma = exp[{GAMMA} (log Mhalo - 10) + ({DELTA})]. One relation for the whole redshift range, so the epoch is the interval z=5-12.",
    definitions={"massDefinition": "stars-within-third-Rmax-masked", "imf": "kroupa01", "cosmology": {"H0": 68, "Om": 0.31}, "haloMassDefinition": "Bryan-Norman-virial", "haloMassHistory": "current", "population": "centrals"},
    citation="Ma et al. 2018, MNRAS 478, 1694, eqs. (smhm) and (scatter)", doi="10.1093/mnras/sty1024", url=f"https://arxiv.org/abs/{ARXIV}", figure="eq. smhm", panel="fit", sha=sha,
    member="arXiv LaTeX source, SMHM fit parameters (alpha, beta, gamma, delta) = (1.58, 7.10, -0.14, -1.10)", calib="published fit parameters", tier="published-fit", uncertainty=0.0, calibration="prediction", rankable=False,
    note="Fit parameters transcribed from the paper text.")
fit["representation"] = {"type": "parametric", "equation": "log10(M*/Mhalo) = alpha (log Mhalo - 10) + beta - log Mhalo", "expression": "alpha*(x-10)+beta-x",
                         "parameters": {"alpha": ALPHA, "beta": BETA, "gamma": GAMMA, "delta": DELTA}}
fit["domain"] = {"xMin": 7.5, "xMax": 12.0}
for k in ("axisCalibrationPixels", "digitizationUncertaintyDex"):
    fit["provenance"].pop(k, None)
fit["provenance"]["extractionMethod"] = "transcribed from the paper text"
records.append(fit)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ma18-fire2-gsmf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIRE-2 records (GSMF z=5-12 from the appendix table, SHMR fit) from Ma+18; {len(PUBLISHED)} rows spot-checked")
