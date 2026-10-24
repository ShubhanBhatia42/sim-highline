"""Cosmic Dawn II (CoDa II; Ocvirk et al. 2020, MNRAS 496, 4087): the public galaxy catalogues of the CoDa II simulation, VizieR VI/146 (CDS), one file per snapshot at z = 6, 7, 8 and 10.
Each row is a friends-of-friends dark matter halo (linking length 0.2, at least 246 dark matter particles = 1e8 Msun) with the stellar mass inside r200, the SFR (stellar mass formed in the last 10 Myr)
and the dust-free M_AB1600 (ReadMe: "Galaxies are identified as Friends-of-Friends dark matter haloes with a linking length ll=0.2. Stars are associated to each halo if they are within a sphere of radius r200.
Magnitudes are computed using a BPASS stellar population model ... No dust opacity is considered."). Records: the galaxy stellar mass function and the stellar mass-halo mass relation of the whole 94.44 cMpc box.
Before anything is written the script checks the catalogue against the paper: the row counts of the ReadMe, the 246-particle halo limit, the fractions of the star formation rate in galaxies brighter than M_AB1600 = -17 and -13
(63 and 94 percent at z = 6, 18 and 76 percent at z = 10, printed in section 3.3), the faintest magnitudes (about -5 at z = 6 and -5.5 at z = 10) and the shape of the luminosity function against the paper's appendix table.
Usage: python3 scripts/ingest_coda2_vizier.py [CATALOGUE_DIR]   (halo{6,7,8,10}.dat.gz from https://cdsarc.cds.unistra.fr/ftp/VI/146/, downloaded if absent; writes data/curves/ocvirk20-coda2-catalogue.json)"""
import gzip
import hashlib
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

BASE = "https://cdsarc.cds.unistra.fr/ftp/VI/146/"
DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/coda2_vizier_VI146")
DOI = "10.1093/mnras/staa1266"
L_BOX = 94.44          # cMpc, Table 1 of the paper
V_BOX = L_BOX ** 3
M_DM = 4.07e5          # Msun, dark matter particle mass, Table 1
ROWS = {6: 4330547, 7: 3654273, 8: 2879910, 10: 1369444}   # ReadMe, file summary
MIN_N = 10
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


def load(z):
    DIR.mkdir(parents=True, exist_ok=True)
    f = DIR / f"halo{z}.dat.gz"
    if not f.exists():
        urllib.request.urlretrieve(BASE + f.name, f)
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    a = np.fromstring(gzip.open(f, "rt").read(), sep=" ").reshape(-1, 9)
    return a, sha


# the appendix table of the paper (average over five sub-boxes), to compare the shape of the luminosity function
tab = {}
for line in (vf.fetch_arxiv("1811.11192") / "LFs4paper.tex").read_text().split("\\\\"):
    c = [x.strip() for x in line.replace("\\hline", "").split("&")]
    if len(c) == 17 and re.fullmatch(r"-\d+\.\d", c[0]):
        tab[float(c[0])] = [float(x) if x else None for x in c[1:]]

AX_M = "log10 stellar mass inside r200 of the friends-of-friends halo"
records = []
for z in (6, 7, 8, 10):
    a, sha = load(z)
    Mh, Ms, sfr, mag = a[:, 0], a[:, 4], a[:, 7], a[:, 8]
    check(len(a) == ROWS[z], f"z = {z}: {len(a)} rows, as the ReadMe's file summary")
    check(Mh.min() / M_DM >= 246 and Mh.min() < 1.01e8, f"z = {z}: the lightest halo is {Mh.min() / M_DM:.1f} dark matter particles = {Mh.min():.4g} Msun (paper: haloes of 246 particles, 1e8 Msun)")
    star = Ms > 0
    lit = mag < 90
    check((star == lit).all(), f"z = {z}: M_AB1600 is defined exactly for the haloes with stars")
    pos = sfr > 0
    tot = sfr[pos].sum()
    if z in (6, 10):
        want = {6: (63, 94), 10: (18, 76)}[z]
        got = [100 * sfr[pos & (mag < lim)].sum() / tot for lim in (-17, -13)]
        check(all(abs(g - w) <= 2.5 for g, w in zip(got, want)), f"z = {z}: {got[0]:.1f} and {got[1]:.1f} percent of the star formation rate is in galaxies with M_AB1600 < -17 and < -13 (paper: {want[0]} and {want[1]} percent)")
    faint = mag[lit].max()
    wantf, tol = {6: (-5.0, 0.3), 10: (-5.5, 0.5)}.get(z, (None, None))
    if wantf is not None:
        check(abs(faint - wantf) <= tol, f"z = {z}: faintest galaxy has M_AB1600 = {faint:.2f} (paper: about {wantf})")
    # shape of the luminosity function against the paper's table (average column): a constant offset for M < -11.5
    zi = [6, 7, 8, 10].index(z)
    diff = []
    for m in sorted(tab):
        avg = tab[m][4 * zi + 1]
        n = ((mag >= m - 0.25) & (mag < m + 0.25)).sum()
        if avg is not None and n >= 30 and m <= -11.5:
            diff.append(math.log10(n / (V_BOX * 0.5)) - avg)
    check(len(diff) > 8 and np.std(diff) < 0.01 and abs(np.mean(diff) + 0.043) < 0.01,
          f"z = {z}: the catalogue luminosity function (0.5 mag bins on the table's labels, Lbox^3) differs from the paper's table by {np.mean(diff):+.3f} dex, scatter {np.std(diff):.3f}, over the {len(diff)} bins brighter than -11.5 that hold at least 30 galaxies (fainter bins differ by up to 0.2 to 0.5 dex; not reconciled)")

    # ---- galaxy stellar mass function: bins of 0.25 dex from 10^5 Msun; a bin is kept when it holds at least 10 galaxies and at most 1 percent of them sit in haloes below 2 x 1e8 Msun
    lm = np.log10(Ms[star])
    mh_s = Mh[star]
    edges = np.arange(5.0, 11.01, 0.25)
    pts = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (lm >= lo) & (lm < hi)
        n = int(sel.sum())
        if n < MIN_N:
            continue
        near = float((mh_s[sel] < 2e8).mean())
        if near > 0.01:
            continue
        phi = n / (V_BOX * 0.25)
        p = {"x": round((lo + hi) / 2, 3), "y": round(math.log10(phi), 4), "yHigh": round(math.log10((n + math.sqrt(n)) / (V_BOX * 0.25)), 4), "count": n}
        if n > math.sqrt(n):
            p["yLow"] = round(math.log10((n - math.sqrt(n)) / (V_BOX * 0.25)), 4)
        pts.append(p)
    check(len(pts) >= 8 and pts[0]["x"] < 5.8, f"z = {z}: stellar mass function in {len(pts)} bins from log M* = {pts[0]['x']}")
    base = dict(source="CoDa II", run="CoDa II (94.44 cMpc box), VizieR VI/146 galaxy catalogue", z=float(z))
    defs_common = {"imf": "unspecified", "cosmology": {"H0": 67.7, "Om": 0.307}, "massDefinition": "sphere-R200"}
    records.append({
        "id": f"ocvirk20.coda2.gsmf.z{z}", "source": "CoDa II", "run": base["run"], "kind": "simulation", "relation": "gsmf",
        "epoch": {"zRepresentative": float(z), "zNominal": float(z), "zMin": float(z), "zMax": float(z), "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": AX_M, "xUnit": "log10(Msun)", "yDefinition": "log10 number density per dex of stellar mass (comoving), Poisson errors", "yUnit": "log10(cMpc^-3 dex^-1)"},
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": pts}, "scatter": None,
        "selection": {"population": "all friends-of-friends haloes above 1e8 Msun that hold stars (each halo counts once, with all stars inside r200)",
                      "warning": f"Galaxy stellar mass function of the whole CoDa II box at z = {z}, counted by sim-highline from the public catalogue (0.25 dex bins; error bars are Poisson). A galaxy is a friends-of-friends halo, so the satellites of a halo are inside its stellar mass; only haloes above 1e8 Msun (246 particles) are in the catalogue, "
                                 f"and bins are kept only where at least 10 galaxies are counted and no more than 1 percent of them live in haloes below 2e8 Msun, so that the missing lighter haloes cannot change the bin (the lowest kept bin is log M* = {pts[0]['x']}). The box is a constrained realization of the Local Universe, not a random volume. "
                                 "The paper states the Kroupa IMF only for its ionizing and UV source model, so the IMF of the stellar mass is left unspecified."},
        "definitions": {**defs_common, "densityFrame": "comoving", "population": "all friends-of-friends haloes above 1e8 Msun that hold stars"},
        "provenance": {"tier": "catalog-derived", "citation": "Ocvirk et al. 2020, MNRAS 496, 4087 (doi 10.1093/mnras/staa1266); galaxy catalogue VizieR VI/146 (CDS); mass function counted by sim-highline", "doi": DOI,
                       "url": "https://cdsarc.cds.unistra.fr/viz-bin/cat/VI/146", "retrieved": "2026-10-24", "checksumSha256": sha, "sourceMember": f"halo{z}.dat.gz (columns M*, MAB1600)",
                       "extractionMethod": "histogram of the stellar mass column of the public catalogue divided by the box volume 94.44^3 cMpc^3 and the bin width"},
        "calibration": "prediction", "rankable": True,
        "notes": "Computed by sim-highline from the public catalogue; the same snapshot's UV luminosity function is in ocvirk20-coda2-uvlf.json (the paper's own table)."})

    # ---- stellar mass-halo mass relation: median of M*/Mh over all haloes in 0.25 dex bins of halo mass (haloes without stars count as zero), kept where more than half of the haloes hold stars
    edges = np.arange(8.0, 12.51, 0.25)
    lmh = np.log10(Mh)
    ratio = Ms / Mh
    pts = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (lmh >= lo) & (lmh < hi)
        n = int(sel.sum())
        if n < MIN_N or (Ms[sel] > 0).mean() <= 0.5:
            continue
        p16, p50, p84 = np.percentile(ratio[sel], [16, 50, 84])
        p = {"x": round((lo + hi) / 2, 3), "y": round(math.log10(p50), 4), "count": n}
        if p16 > 0:
            p["yLow"] = round(math.log10(p16), 4)
        p["yHigh"] = round(math.log10(p84), 4)
        pts.append(p)
    check(len(pts) >= 6, f"z = {z}: stellar mass-halo mass relation in {len(pts)} bins from log Mh = {pts[0]['x']}")
    records.append({
        "id": f"ocvirk20.coda2.shmr.z{z}", "source": "CoDa II", "run": base["run"], "kind": "simulation", "relation": "shmr",
        "epoch": {"zRepresentative": float(z), "zNominal": float(z), "zMin": float(z), "zMax": float(z), "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": "log10 friends-of-friends halo mass (linking length 0.2)", "xUnit": "log10(Msun)", "yDefinition": "log10 median stellar-to-halo mass ratio M*/Mh (stars inside r200)", "yUnit": "dex"},
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "scatter", "connect": True, "points": pts}, "scatter": {"lower": "16th percentile", "upper": "84th percentile"},
        "selection": {"population": "all friends-of-friends haloes above 1e8 Msun, including those without stars",
                      "warning": f"Median stellar-to-halo mass ratio of the whole CoDa II box at z = {z}, computed by sim-highline from the public catalogue in 0.25 dex bins of halo mass; haloes without stars count as a ratio of zero, so a bin is kept only where more than half of its haloes hold stars "
                                 f"(the lightest kept bin is log Mh = {pts[0]['x']}; below it the median is zero because star formation is suppressed or has not started) and holds at least 10 haloes; the 16th percentile is given only where it is above zero. "
                                 "The halo mass is the friends-of-friends mass and the stellar mass is all stars inside r200, satellites included. The box is a constrained realization of the Local Universe, not a random volume."},
        "definitions": {**defs_common, "haloMassDefinition": "FOF", "haloMassHistory": "current", "population": "all friends-of-friends haloes above 1e8 Msun, including those without stars"},
        "provenance": {"tier": "catalog-derived", "citation": "Ocvirk et al. 2020, MNRAS 496, 4087 (doi 10.1093/mnras/staa1266); galaxy catalogue VizieR VI/146 (CDS); medians computed by sim-highline", "doi": DOI,
                       "url": "https://cdsarc.cds.unistra.fr/viz-bin/cat/VI/146", "retrieved": "2026-10-24", "checksumSha256": sha, "sourceMember": f"halo{z}.dat.gz (columns Mhalo, M*)",
                       "extractionMethod": "median and 16th-84th percentiles of M*/Mhalo of the public catalogue in 0.25 dex bins of Mhalo"},
        "calibration": "prediction", "rankable": True,
        "notes": "Computed by sim-highline from the public catalogue. The paper does not show this relation."})

out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ocvirk20-coda2-catalogue.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} CoDa II records from the VizieR catalogue ({len(checks)} checks passed)")
for c in checks:
    print("  ok:", c)
