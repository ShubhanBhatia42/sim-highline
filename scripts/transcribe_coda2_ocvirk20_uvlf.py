"""Cosmic Dawn II (CoDa II; Ocvirk et al. 2020, MNRAS 496, 4087; arXiv:1811.11192): the UV luminosity functions the paper tabulates in its appendix (LFs4paper.tex of the arXiv source),
at z = 6, 7, 8 and 10: for each of 0.5-mag bins from M_AB1600 = -24 to -3 the base-10 logarithm of the median, the average, the minimum and the maximum of the luminosity function of
five independent sub-boxes (each 1/5 of the 94.44 cMpc box). The record holds the median (the thick line of the paper's Fig. 12) with the minimum-maximum envelope of the five
sub-boxes (the shaded area of that figure); the average column is not stored. An empty cell of the table means the quantity is zero (log undefined) and is absent from the record.
Magnitudes are intrinsic (the paper: "assuming no dust extinction"), computed from the BPASS Z = 0.001 binary population model with a Kroupa IMF for all star particles of each halo.
Usage: python3 scripts/transcribe_coda2_ocvirk20_uvlf.py [SOURCE_DIR]   (writes data/curves/ocvirk20-coda2-uvlf.json)"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1811.11192"
DOI = "10.1093/mnras/staa1266"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
TABLE = SRC / "LFs4paper.tex"
SHA = vf.sha256(TABLE)
L_BOX = 94.44  # cMpc, Table 1 of the paper ("Comoving box size 94.44 Mpc (64 h^-1 Mpc)")

rows = {}
for line in TABLE.read_text().split("\\\\"):
    c = [x.strip() for x in line.replace("\\hline", "").split("&")]
    if len(c) == 17 and re.fullmatch(r"-\d+\.\d", c[0]):
        rows[float(c[0])] = [float(x) if x else None for x in c[1:]]
MAGS = sorted(rows)
ZS = [6.0, 7.0, 8.0, 10.0]
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


def col(z, k):
    """k = 0 median, 1 average, 2 minimum, 3 maximum (log10 per mag per cMpc^3)."""
    return {m: rows[m][4 * ZS.index(z) + k] for m in MAGS}


# --------------------------------------------------------------------- checks against the paper
check(MAGS[0] == -24.0 and MAGS[-1] == -3.0 and len(MAGS) == 43 and all(abs(b - a - 0.5) < 1e-9 for a, b in zip(MAGS, MAGS[1:])),
      "the table covers M_AB1600 = -24 to -3 in 0.5 mag bins (conclusions: 'from M_AB1600 = -3 to -24')")
vsub = L_BOX ** 3 / 5
check(abs(vsub - 168000) / 168000 < 0.01, f"one sub-box is Lbox^3/5 = {vsub:,.0f} cMpc^3 (text: about 168,000 cMpc^3)")
limit = {}
for z in ZS:
    med = col(z, 0)
    peak = max((m for m in MAGS if med[m] is not None), key=lambda m: med[m])
    check(peak == -11.0, f"z = {z:g}: the median luminosity function peaks at M_AB1600 = {peak} (text: maximum at about -11 at all redshifts)")
    faint = [m for m in MAGS if m > -11.0 and med[m] is not None and med[m] >= med[-11.0] - 0.5]
    run = [m for m in faint if all(med[k] is not None and med[k] >= med[-11.0] - 0.5 for k in MAGS if -11.0 < k <= m)]
    limit[z] = max(run)
check(limit[6.0] == -6.0, f"z = 6: the plateau (median within 0.5 dex of the peak) extends faintward of -11 down to M_AB1600 = {limit[6.0]} (text: 'at z = 6 the plateau extends down to -6')")
check(limit[10.0] < limit[8.0] < limit[7.0] < limit[6.0], f"the faint limit of the plateau moves to fainter magnitudes with time (z = 10, 8, 7, 6: {[limit[z] for z in (10.0, 8.0, 7.0, 6.0)]}; text: plateau 'extending to fainter magnitudes as time goes by')")
# the table itself: statistics of five sub-boxes must be ordered and an average is at least a fifth of the largest value
for z in ZS:
    med, avg, lo, hi = (col(z, k) for k in range(4))
    n = 0
    for m in MAGS:
        if hi[m] is None:
            check(all(v[m] is None for v in (med, avg, lo)), f"z = {z:g}, M = {m}: empty row has no statistic")
            continue
        n += 1
        assert avg[m] is not None, (z, m)
        ok = avg[m] <= hi[m] + 0.006 and avg[m] >= hi[m] - math.log10(5) - 0.011
        ok = ok and (lo[m] is None or lo[m] <= avg[m] + 0.006) and (med[m] is None or (lo[m] is None or lo[m] <= med[m]) and med[m] <= hi[m])
        assert ok, ("table statistics out of order", z, m, med[m], avg[m], lo[m], hi[m])
    check(n > 20, f"z = {z:g}: median, average, minimum and maximum are ordered in all {n} populated bins (the average of five sub-boxes lies between max/5 and max)")
# the brightest populated bins hold single galaxies: values step as log10(N) above the one-galaxy value
one = min(v for k in (0, 2, 3) for z in ZS for v in col(z, k).values() if v is not None)
sing = [v for z in ZS for k in (0, 2, 3) for v in col(z, k).values() if v is not None and v < one + 0.8]
dev = max(min(abs(v - (one + math.log10(n))) for n in range(1, 7)) for v in sing)
check(abs(one - -4.88) < 0.005 and dev < 0.03, f"the sparsest bins sit at the one-galaxy value {one} + log10(N) (largest deviation {dev:.3f} dex over {len(sing)} entries): the transcription has no digit errors there")
fifths = [v for z in ZS for v in col(z, 1).values() if v is not None and v < one - 0.1]
dev5 = max(min(abs(v - (one + math.log10(n / 5))) for n in range(1, 5)) for v in fifths)
check(dev5 < 0.03, f"the averages below the one-galaxy value are N/5 galaxies (largest deviation {dev5:.3f} dex over {len(fifths)} entries)")
unit = 10 ** one
note_unit = f"A single galaxy in one sub-box bin is 10^{one} = {unit:.3g} per mag per cMpc^3, so V x dM = {1 / unit:,.0f} cMpc^3 mag; with the stated sub-box volume of {vsub:,.0f} cMpc^3 that is a bin of {1 / unit / vsub:.2f} mag, not the 0.5 mag spacing of the table (the paper does not explain the difference of about 10 percent). Counting the public catalogue (VizieR VI/146, scripts/ingest_coda2_vizier.py) in 0.5 mag bins on the table's labels gives values 0.044 dex lower than the table's average column for every bin brighter than M_AB1600 = -11.5 with 30 or more galaxies (scatter 0.003 dex; a factor 1.107 in volume) and values lower by 0.1 to 0.5 dex at fainter magnitudes; this is not reconciled, and the tabulated values are stored as printed."

AX = {"xDefinition": "absolute UV magnitude M_AB1600 (intrinsic, no dust; AB)", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude (median of five sub-boxes)", "yUnit": "log10(cMpc^-3 mag^-1)"}
DEF = {"imf": "kroupa01", "cosmology": {"H0": 67.7, "Om": 0.307}, "densityFrame": "comoving", "uvBand": "rest-frame 1600 A, AB", "dustCorrection": "none (intrinsic)",
       "population": "all galaxies (friends-of-friends halos of at least 1e8 Msun, 246 dark matter particles; all star particles of each halo)"}
RUN = "CoDa II (94.44 cMpc box, 4096^3 cells), median of five sub-boxes"
records = []
for z in ZS:
    med, lo, hi = col(z, 0), col(z, 2), col(z, 3)
    pts = []
    for m in MAGS:
        if med[m] is None:
            continue
        p = {"x": m, "y": med[m]}
        if lo[m] is not None:
            p["yLow"] = lo[m]
        if hi[m] is not None:
            p["yHigh"] = hi[m]
        pts.append(p)
    assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and len(pts) > 20
    # the median is nonzero in a single contiguous run of bins
    idx = [MAGS.index(p["x"]) for p in pts]
    assert idx == list(range(idx[0], idx[-1] + 1)), z
    records.append({
        "id": f"ocvirk20.coda2.uvlf.z{z:g}", "source": "CoDa II", "run": RUN, "kind": "simulation", "relation": "uvlf",
        "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None}, "axes": AX,
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "scatter", "connect": True, "points": pts}, "scatter": None,
        "selection": {"population": "all galaxies of the constrained Local-Universe box (halos above 1e8 Msun)",
                      "warning": f"Intrinsic (dust-free) UV luminosity function of the CoDa II box at z = {z:g} in 0.5 mag bins, as tabulated in the appendix of Ocvirk et al. 2020: the line is the median of the luminosity functions of five independent, equal sub-boxes (each 1/5 of the volume, about 168,000 cMpc^3), the band is their minimum and maximum, which shows the variance between volumes of that size and is not an uncertainty of the median. "
                                 f"Bins where the median or the minimum is zero in the table are empty there (the log is undefined), so the curve starts at M_AB1600 = {pts[0]['x']:g} and the band has no lower edge in the sparse bins. The box is a constrained realization of the Local Universe (a Virgo, Local Group and Fornax progenitor region), not a random volume. Magnitudes use the BPASS Z = 0.001 binary population model with a Kroupa IMF and no dust; the observed luminosity function would be fainter."},
        "definitions": DEF,
        "provenance": {"tier": "published-table", "citation": "Ocvirk et al. 2020, MNRAS 496, 4087 (doi 10.1093/mnras/staa1266), appendix table of CoDa II UV luminosity functions at four epochs", "doi": DOI,
                       "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-24", "checksumSha256": SHA, "sourceMember": "LFs4paper.tex (arXiv source), columns (1) median, (3) minimum and (4) maximum",
                       "extractionMethod": "transcribed from the arXiv LaTeX table and parsed by script; checked against numbers printed in the text (see the script)"},
        "calibration": "calibration-adjacent",
        "rankable": True,
        "notes": "Values as tabulated by the authors. The paper tuned the star formation efficiency (0.02) to the observed cosmic star formation rate density and the escape fraction (0.42) to a reionization redshift near 6, so the luminosity function is not a pure prediction. " + note_unit})

out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ocvirk20-coda2-uvlf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} CoDa II UV luminosity function records ({len(checks)} checks passed)")
