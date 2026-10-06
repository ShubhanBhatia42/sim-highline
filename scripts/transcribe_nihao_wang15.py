import json
import math
from pathlib import Path

import numpy as np

TABLE = """
g3.54e09 3.95e9 3.02e4 0
g4.36e09 9.54e9 3.30e4 0
g4.99e09 5.72e9 3.76e5 5.8e-5
g5.22e09 6.32e9 1.18e5 1.2e-5
g5.41e09 5.11e9 1.21e6 0
g5.59e09 6.46e9 1.74e6 1.7e-4
g5.84e09 5.95e9 1.16e5 6.3e-5
g7.05e09 1.05e10 2.27e6 0
g7.34e09 6.05e9 4.22e5 0
g9.26e09 6.14e9 5.37e4 0
g1.09e10 1.09e10 6.55e6 0
g1.18e10 1.10e10 3.41e6 0
g1.23e10 9.08e9 1.60e6 0
g1.44e10 1.70e10 6.69e6 0
g1.47e10 1.52e10 9.00e6 1.3e-3
g1.50e10 1.40e10 3.42e6 0
g1.57e10 1.29e10 8.93e6 0
g1.88e10 1.88e10 1.65e7 3.9e-3
g1.89e10 2.13e10 1.29e7 3.1e-3
g1.90e10 2.40e10 1.20e7 1.4e-3
g1.92e10 1.98e10 5.30e6 1.4e-4
g1.95e10 1.37e10 3.82e6 0
g2.09e10 1.66e10 9.35e6 0
g2.34e10 2.57e10 1.36e7 0
g2.37e10 2.43e10 9.65e6 0
g2.39e10 1.46e10 5.94e6 1.7e-4
g2.63e10 2.70e10 4.28e7 0
g2.64e10 3.26e10 2.93e7 0
g2.80e10 2.77e10 3.68e7 2.5e-3
g2.83e10 2.50e10 2.96e7 0
g2.94e10 3.22e10 5.86e7 4.2e-4
g3.19e10 3.54e10 1.47e7 3.9e-5
g3.44e10 4.88e10 6.32e7 4.7e-3
g3.67e10 3.15e10 5.49e7 0
g3.93e10 3.30e10 3.75e7 0
g4.27e10 4.25e10 6.16e7 4.4e-3
g4.48e10 6.04e10 1.37e8 3.9e-5
g4.86e10 5.16e10 1.22e8 3.7e-3
g4.94e10 5.26e10 1.11e8 7.8e-3
g4.99e10 4.90e10 1.22e8 9.4e-3
g5.05e10 4.29e10 9.47e7 7.8e-5
g6.12e10 4.97e10 9.13e7 7.8e-5
g6.37e10 1.15e11 2.12e8 1.2e-2
g6.77e10 9.28e10 4.84e8 8.7e-2
g6.91e10 7.08e10 2.50e8 2.9e-3
g7.12e10 4.88e10 1.37e8 1.5e-2
g8.89e10 9.22e10 4.02e8 2.9e-2
g9.59e10 8.84e10 2.76e8 8.7e-2
g1.05e11 1.18e11 5.67e8 6.0e-2
g1.08e11 1.20e11 8.47e8 2.7e-2
g1.37e11 1.48e11 2.02e9 9.5e-2
g1.52e11 1.57e11 7.92e8 3.8e-2
g1.57e11 1.58e11 1.15e9 6.7e-2
g1.59e11 1.68e11 6.69e8 7.9e-4
g1.64e11 1.93e11 9.13e8 0.38
g2.04e11 2.09e11 4.70e9 0.79
g2.19e11 1.31e11 9.27e8 9.8e-2
g2.39e11 2.58e11 5.80e9 1.12
g2.41e11 2.53e11 4.10e9 0.62
g2.42e11 2.68e11 5.48e9 0.39
g2.54e11 2.67e11 3.50e9 0.87
g3.06e11 3.11e11 7.42e9 1.25
g3.21e11 3.03e11 3.67e9 1.10
g3.23e11 8.93e10 3.60e8 5.5e-2
g3.49e11 4.33e11 3.97e9 0.61
g3.55e11 4.23e11 3.85e9 0.66
g3.59e11 3.49e11 4.36e9 0.74
g3.71e11 4.08e11 1.24e10 1.49
g4.90e11 3.25e11 3.43e9 0.42
g5.02e11 5.75e11 1.46e10 0.92
g5.31e11 5.28e11 1.64e10 2.26
g5.36e11 6.88e11 1.18e10 3.88
g5.38e11 6.46e11 1.85e10 1.24
g5.46e11 3.25e11 3.78e9 0.37
g5.55e11 5.20e11 1.71e10 2.75
g6.96e11 8.00e11 3.30e10 10.40
g7.08e11 8.06e11 3.05e10 3.66
g7.44e11 1.18e12 1.85e10 12.95
g7.55e11 8.93e11 3.11e10 2.92
g7.66e11 9.30e11 5.92e10 2.71
g8.06e11 9.43e11 4.48e10 13.19
g8.13e11 9.91e11 6.68e10 3.67
g8.26e11 1.02e12 4.68e10 2.04
g8.28e11 1.16e12 1.77e10 1.01
g1.12e12 1.12e12 7.85e10 4.29
g1.77e12 2.19e12 1.39e11 8.47
g1.92e12 2.34e12 1.58e11 8.13
g2.79e12 3.53e12 1.96e11 11.09
"""
rows = [line.split() for line in TABLE.strip().splitlines()]
ids = [r[0] for r in rows]
m200, mstar, sfr = (np.array([float(r[i]) for r in rows]) for i in (1, 2, 3))
assert len(rows) == 88 and len(set(ids)) == 88, len(rows)
assert ids == sorted(ids, key=lambda s: float(s[1:])), "IDs must follow the table order (ascending DM-only halo mass)"
assert 3.0e4 <= mstar.min() < 1e5 and 1.9e11 < mstar.max() < 2e11 and 3.9e9 < m200.min() and m200.max() < 3.6e12

URL = "https://arxiv.org/abs/1503.04818"
PROV = {"tier": "published-table", "citation": "Wang et al. 2015, MNRAS 454, 83 (NIHAO project I), Tables A1-A2", "doi": "10.1093/mnras/stv1937", "url": URL,
        "retrieved": "2026-10-05", "sourceMember": "Appendix A, Tables A1 and A2 (88 main target haloes, z=0), transcribed from the arXiv v3 PDF"}
DEFS = {"imf": "chabrier03", "cosmology": {"H0": 67.1, "Om": 0.3175}, "massDefinition": "sphere-0.2R200"}
EPOCH = {"zRepresentative": 0.0, "zNominal": 0.0, "zMin": 0.0, "zMax": 0.0, "mode": "published-epoch", "snapshot": None}
SEL = ("NIHAO main target haloes: isolated zoom-in centrals selected without regard to structure or merger history, so not a volume-complete sample. "
       "M200 from AHF with Delta=200 times the critical density; M* within 0.2 R200; SFR from stars formed within 0.2 R200 over the last 100 Myr. No AGN feedback.")


def median_bins(x, y, edges, nmin=5):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (x >= lo) & (x < hi)
        if sel.sum() >= nmin:
            p16, p50, p84 = np.percentile(y[sel], [16, 50, 84])
            out.append({"x": round((lo + hi) / 2, 3), "y": round(float(p50), 4), "yLow": round(float(p16), 4), "yHigh": round(float(p84), 4), "count": int(sel.sum())})
    return out


def record(rid, rel, rep, axes, defs, rankable, tier, warn_extra, notes, run):
    pts = rep["points"]
    return {"id": rid, "source": "NIHAO zoom suite", "run": run, "kind": "simulation", "relation": rel, "epoch": EPOCH, "axes": axes,
            "domain": {"xMin": min(p["x"] for p in pts), "xMax": max(p["x"] for p in pts)}, "representation": rep,
            "scatter": {"lower": "16th percentile", "upper": "84th percentile"} if rep["intervalKind"] == "scatter" else None,
            "selection": {"population": "isolated zoom centrals", "warning": (SEL + " " + warn_extra).strip()},
            "definitions": {**DEFS, **defs, "population": "isolated-zoom-centrals"}, "provenance": {**PROV, "tier": tier},
            "calibration": "prediction", "rankable": rankable, "notes": notes}


lx, lr = np.log10(m200), np.log10(mstar / m200)
shmr_pts = [{"x": round(float(a), 4), "y": round(float(b), 4)} for a, b in sorted(zip(lx, lr))]
sf = sfr > 0
lm, ls = np.log10(mstar[sf]), np.log10(sfr[sf])
sfms_pts = [{"x": round(float(a), 4), "y": round(float(b), 4)} for a, b in sorted(zip(lm, ls))]
shmr_axes = {"xDefinition": "log10 M200 (AHF, 200x critical density)", "xUnit": "log10(Msun)", "yDefinition": "log10 M*(<0.2 R200) / M200", "yUnit": "dex"}
sfms_axes = {"xDefinition": "log10 M*(<0.2 R200)", "xUnit": "log10(Msun)", "yDefinition": "log10 SFR averaged over 100 Myr within 0.2 R200", "yUnit": "log10(Msun/yr)"}
shmr_defs = {"haloMassDefinition": "M200crit", "haloMassHistory": "current"}
sfms_defs = {"sfrTimescaleMyr": 100, "sfrStatistic": "median"}
nzero = int((~sf).sum())
records = [
    record("wang15.nihao.shmr.galaxies.z0", "shmr", {"type": "points", "intervalKind": "unspecified", "connect": False, "points": shmr_pts}, shmr_axes, shmr_defs, False,
           "published-table", "", "Individual galaxies as tabulated (88).", "Wang+15, individual galaxies"),
    record("wang15.nihao.shmr.median.z0", "shmr", {"type": "points", "intervalKind": "scatter", "connect": True, "points": median_bins(lx, lr, np.arange(9.5, 12.76, 0.5))},
           shmr_axes, shmr_defs, True, "catalog-derived", "Medians computed by sim-highline from the 88 tabulated galaxies in 0.5 dex bins with at least 5 galaxies.",
           "Binned from Wang et al. 2015 Tables A1-A2.", "Wang+15, binned medians"),
    record("wang15.nihao.sfms.galaxies.z0", "sfms", {"type": "points", "intervalKind": "unspecified", "connect": False, "points": sfms_pts}, sfms_axes, sfms_defs, False,
           "published-table", f"{nzero} galaxies with tabulated SFR = 0.00 (no stars formed in 100 Myr at the table's precision) are omitted.", "Individual galaxies as tabulated.", "Wang+15, individual galaxies"),
    record("wang15.nihao.sfms.median.z0", "sfms", {"type": "points", "intervalKind": "scatter", "connect": True, "points": median_bins(lm, ls, np.arange(6.0, 11.6, 0.5))},
           sfms_axes, sfms_defs, True, "catalog-derived", f"Medians of the {int(sf.sum())} galaxies with SFR > 0, 0.5 dex bins with at least 5 galaxies; {nzero} SFR = 0 galaxies omitted, so low-mass medians are biased high.",
           "Binned from Wang et al. 2015 Tables A1-A2.", "Wang+15, binned medians"),
]
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "nihao-wang15.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"NIHAO: {len(rows)} galaxies, {int(sf.sum())} with SFR>0; {len(records)} records")
