"""Ingest the z~0 joint distribution of log sSFR and log M* from GSWLC-2 (Salim, Boquien & Lee 2018, ApJ 859, 11,
arXiv:1804.05850) as one `distribution` record on relation `ssfr`.

The catalogue is fetched from VizieR (J/ApJ/859/11, table gswlc-m2, the medium-deep GALEX UV depth), filtered, binned
with exact integer arithmetic on the catalogue's 3-decimal values, and written as one record. Nothing but the
catalogue is used. Run:  python3 ingest_gswlc2_distribution.py [--cache TSV] [--out records.json]
(--cache re-uses an already downloaded file instead of querying VizieR; the file is hashed either way).
Style follows scripts/digitizer-template.py: edit the CONFIG block, the output path is a variable at the top."""
import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

# ---- CONFIG -------------------------------------------------------------------------------------------------
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "salim18-gswlc2-ssfr-distribution.json"
VIZIER_ASU = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"
VIZIER_TABLE = "J/ApJ/859/11/gswlc-m2"          # GSWLC-M2: "Medium-deep catalog (GSWLC-M2; Covers 49% of SDSS)"
COLUMNS = ["ObjID", "z", "logMs", "logSFR", "e_logSFR", "SED", "Survey", "UV", "MIR", "MGS"]
RETRIEVED = "2026-10-18"
REQUIRE_MGS = True                               # CDS ReadMe Note (4): use MGS=1 "for statistical studies"
REQUIRE_SED_FLAG = 0                             # CDS ReadMe Note (1): SED=0 is OK; otherwise no SED parameters are given
# bins (milli-dex integers so that binning is exact on the catalogue's 3-decimal values)
X_EDGES_MILLI = list(range(8500, 11750 + 1, 250))     # log10 M* = 8.5 ... 11.75, 0.25 dex
Y_EDGES_MILLI = list(range(-13500, -8500 + 1, 100))   # log10 sSFR [1/yr] = -13.5 ... -8.5, 0.1 dex
RECORD_ID = "salim18.gswlc2-m2.ssfr.distribution.z0.1"
# -------------------------------------------------------------------------------------------------------------


def query_url():
    params = [("-source", VIZIER_TABLE), ("-out", ",".join(COLUMNS)), ("-out.max", "unlimited"), ("-out.meta", "h")]
    return VIZIER_ASU + "?" + "&".join(f"{k}={urllib.parse.quote(v, safe=',/')}" for k, v in params)


def data_sha256(raw):
    """SHA-256 of the response without its comment lines: VizieR writes the request date and time into '#' lines, so the whole response hashes differently on every request while the data do not change."""
    return hashlib.sha256(b"\n".join(l for l in raw.split(b"\n") if not l.startswith(b"#"))).hexdigest()


def fetch(cache):
    if cache and Path(cache).exists():
        raw = Path(cache).read_bytes()
    else:
        url = query_url()
        print("VizieR query:", url)
        with urllib.request.urlopen(url, timeout=1500) as r:
            raw = r.read()
        if cache:
            Path(cache).write_bytes(raw)
    return raw, data_sha256(raw)


def parse(raw):
    lines = [l for l in raw.decode().split("\n") if l.strip() and not l.startswith("#")]
    header = lines[0].split("\t")
    assert header == COLUMNS, header
    assert set(lines[1].replace("\t", "")) == {"-"}, "expected the VizieR dash line below the header"
    cols = {h: [] for h in header}
    for l in lines[2:]:
        cells = l.split("\t")
        assert len(cells) == len(header), l
        for h, c in zip(header, cells):
            cols[h].append(c.strip())
    return cols


def milli(strings):
    """3-decimal strings -> integer milli-units; blank (VizieR '?=-99' null) -> None via a mask."""
    ok = np.array([s != "" for s in strings])
    out = np.zeros(len(strings), dtype=np.int64)
    out[ok] = [round(float(s) * 1000) for s, k in zip(strings, ok) if k]
    return out, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    raw, sha = fetch(args.cache)
    c = parse(raw)
    n_cat = len(c["ObjID"])
    z = np.array([float(s) for s in c["z"]])
    m, okm = milli(c["logMs"])
    s, oks = milli(c["logSFR"])
    sed = np.array([int(v) for v in c["SED"]])
    mgs = np.array([int(v) for v in c["MGS"]])
    mir = np.array([int(v) for v in c["MIR"]])
    survey = np.array([int(v) for v in c["Survey"]])
    assert (survey == 2).all(), "gswlc-m2 should only hold Survey=2 galaxies"
    good = okm & oks & (sed == REQUIRE_SED_FLAG)
    n_flagged = int((~good).sum())
    sel = good & (mgs == 1) if REQUIRE_MGS else good
    n_nomgs = int((good & ~sel).sum())
    m, s, z, mir = m[sel], s[sel], z[sel], mir[sel]
    ssfr = s - m                                          # integer milli-dex: log10(SFR/M*) in 1/yr
    xe = np.array(X_EDGES_MILLI)
    ye = np.array(Y_EDGES_MILLI)
    xi = np.floor_divide(m - xe[0], xe[1] - xe[0])        # exact integer binning, [lo, hi)
    yi = np.floor_divide(ssfr - ye[0], ye[1] - ye[0])
    nx, ny = len(xe) - 1, len(ye) - 1
    in_x = (xi >= 0) & (xi < nx)
    below_x = int((m < xe[0]).sum())
    above_x = int((m >= xe[-1]).sum())
    in_y = (yi >= 0) & (yi < ny)
    counts = np.zeros((nx, ny), dtype=np.int64)
    both = in_x & in_y
    np.add.at(counts, (xi[both], yi[both]), 1)
    under_y = np.zeros(nx, dtype=np.int64)
    over_y = np.zeros(nx, dtype=np.int64)
    np.add.at(under_y, xi[in_x & (yi < 0)], 1)
    np.add.at(over_y, xi[in_x & (yi >= ny)], 1)
    med_z = [round(float(np.median(z[in_x & (xi == i)])), 3) if (in_x & (xi == i)).any() else None for i in range(nx)]
    n_per_mass = [int(counts[i].sum() + under_y[i] + over_y[i]) for i in range(nx)]
    assert counts.sum() + under_y.sum() + over_y.sum() == in_x.sum()
    z_rep = round(float(np.median(z[both])), 3)
    summary = dict(catalogueRows=n_cat, withoutValidSedParameters=n_flagged, notInMGS=n_nomgs, selected=int(sel.sum()),
                   belowMassRange=below_x, aboveMassRange=above_x, ssfrBelowRange=int(under_y.sum()), ssfrAboveRange=int(over_y.sum()),
                   inDistribution=int(counts.sum()), zMedian=z_rep, zMinSelected=float(z.min()), zMaxSelected=float(z.max()),
                   fractionWithMidIR=round(float((mir[both] > 0).mean()), 4), ssfrUnderflowByMassBin=under_y.tolist(),
                   nPerMassBin=n_per_mass, medianZPerMassBin=med_z)
    print(json.dumps(summary, indent=1))
    x_edges = [round(v / 1000, 3) for v in xe]
    y_edges = [round(v / 1000, 3) for v in ye]
    q = query_url()
    rec = {
        "id": RECORD_ID,
        "source": "Salim, Boquien & Lee 2018 (GSWLC-2)",
        "run": "GSWLC-M2, SDSS main galaxy sample",
        "kind": "observation",
        "relation": "ssfr",
        "epoch": {"zRepresentative": z_rep, "zMin": 0.01, "zMax": 0.3, "mode": "observational-bin", "snapshot": None},
        "axes": {
            "xDefinition": "log10 current stellar mass from UV/optical(+mid-IR luminosity) SED fitting, Chabrier IMF (GSWLC-2 column logMs)",
            "xUnit": "log10(Msun)",
            "yDefinition": "log10 specific star-formation rate = logSFR - logMs (GSWLC-2 columns), SFR averaged over the last 100 Myr",
            "yUnit": "log10(yr^-1)",
        },
        "domain": {"xMin": x_edges[0], "xMax": x_edges[-1]},
        "representation": {
            "type": "distribution",
            "xEdges": x_edges,
            "yEdges": y_edges,
            "counts": counts.tolist(),
            "weighting": "number",
            "intervalKind": "scatter",
        },
        "scatter": None,
        "selection": {
            "population": "all galaxies (star-forming and quiescent) of the SDSS Main Galaxy Sample in GSWLC-M2",
            "sampleSize": int(counts.sum()),
            "sampleSizeSelected": int(sel.sum()),
            "excluded": {"catalogueRows": n_cat, "noSedParameters_or_SEDflagNot0": n_flagged, "notInMGS": n_nomgs,
                         "logMsBelow8.5": below_x, "logMsAtOrAbove11.75": above_x,
                         "logSsfrBelow-13.5": int(under_y.sum()), "logSsfrAtOrAbove-8.5": int(over_y.sum())},
            "ssfrUnderflowByMassBin": under_y.tolist(),
            "medianRedshiftPerMassBin": med_z,
            "fractionWithMidIRInSEDFit": summary["fractionWithMidIR"],
            "warning": "Flux-limited (r_petro<18.0, 0.01<z<0.30), counts are plain numbers, not 1/Vmax weighted; the catalogue gives no Vmax. "
                       "Galaxies with sSFR below the lower sSFR edge are not in the counts (listed per mass bin in ssfrUnderflowByMassBin). "
                       "The sample is therefore not volume complete at low stellar mass, and the relative weight of red and blue galaxies at fixed mass is set by the flux limit there. "
                       "Neither Salim+16 nor Salim+18 states a stellar-mass completeness limit.",
        },
        "definitions": {
            "massDefinition": "sed-total",
            "imf": "chabrier03",
            "cosmology": {"H0": 70.4, "Om": 0.272},
            "population": "all",
            "sfrTimescaleMyr": 100,
            "sfrStatistic": "unspecified",
            "sfrIndicator": "GSWLC-2 SED+L_IR fit (UV/optical SED fitting constrained by the 12/22 micron WISE-derived IR luminosity where available, UV/optical SED fit otherwise)",
            "massBasis": "current stellar mass from the CIGALE SED fit",
            "weighting": "number",
        },
        "provenance": {
            "tier": "catalog-derived",
            "citation": "Salim, Boquien & Lee 2018, ApJ 859, 11 (GSWLC-2), VizieR J/ApJ/859/11 table gswlc-m2; GSWLC-1: Salim et al. 2016, ApJS 227, 2",
            "doi": None,
            "url": "https://arxiv.org/abs/1804.05850",
            "retrieved": RETRIEVED,
            "catalogUrl": "https://cdsarc.cds.unistra.fr/viz-bin/cat/J/ApJ/859/11",
            "query": q,
            "checksumSha256": sha,
            "checksumNote": "sha256 of the VizieR TSV response for the query above (selected columns, all rows, as returned on the retrieval date) without its '#' comment lines, which carry the request date and time",
            "script": "scripts/ingest_gswlc2_distribution.py",
        },
        "calibration": "validation",
        "rankable": True,
        "notes": f"{int(counts.sum())} galaxies in the distribution. Selection: SED flag = 0 with finite logMs and logSFR, MGS flag = 1. "
                 "sSFR = logSFR - logMs computed from the 3-decimal catalogue values; binning is exact integer arithmetic, bins are [lo, hi).",
    }
    Path(args.out).write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
    print("Wrote 1 record to", args.out)


if __name__ == "__main__":
    sys.exit(main())
