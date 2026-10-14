"""Cosmic star formation rate density histories of the CAMELS IllustrisTNG and SIMBA simulations (Villaescusa-Navarro et al. 2021, arXiv:2010.00619; first generation: 25 Mpc/h boxes, 256^3 dark matter
particles plus 256^3 gas elements), reduced to a fixed redshift grid.

The inputs are the star formation logs the codes wrote while running (extra_files/sfr.txt of every simulation on https://users.flatironinstitute.org/~camels/), 44 MB for IllustrisTNG and 8 MB for SIMBA.
Each file is streamed, hashed (SHA-256 of the original bytes) and reduced; nothing is stored but the result. The Latin-hypercube set LH (1000 simulations per code, 6 parameters: Omega_m, sigma_8 and four
astrophysical factors, a different initial seed for each) and the cosmic-variance set CV (27 simulations at the fiducial parameters, 27 seeds) are read. Writes data/ensembles/camels-sfrd.json.

Usage: python3 scripts/ingest_camels_sfrd.py [--limit N] [--workers W]. Reproducible: the files are public and fixed since 2019 to 2022; the hashes in the output say whether they changed."""
import argparse
import hashlib
import io
import json
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://users.flatironinstitute.org/~camels"
SUITES = {"IllustrisTNG": {"sfr_col": 2, "param_dir": "IllustrisTNG"}, "SIMBA": {"sfr_col": 2, "param_dir": "SIMBA"}}
SETS = {"LH": 1000, "CV": 27}
H = 0.6711  # the same for every simulation of the first generation
BOX = 25.0  # Mpc/h, comoving
VOLUME = (BOX / H) ** 3  # cMpc^3
ZGRID = [round(0.1 + 0.2 * k, 1) for k in range(70)]  # bin centres 0.1 ... 13.9, bin width 0.2 (z = 0 to 14)
ZEDGES = [round(0.2 * k, 1) for k in range(71)]
PARAMS = ["Om", "s8", "ASN1", "AAGN1", "ASN2", "AAGN2"]


def get(url, retries=4):
    for k in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sim-highline-ingest"}), timeout=300) as r:
                return r.read()
        except Exception:
            if k == retries - 1:
                raise
            time.sleep(2 ** k)


def time_of_a(a, om):
    """Cosmic time (yr) at scale factor a in a flat LCDM universe, h = H below."""
    ol = 1.0 - om
    return (2.0 / (3.0 * np.sqrt(ol))) * np.arcsinh(np.sqrt(ol / om) * np.asarray(a) ** 1.5) * (977.792e9 / (100.0 * H))


def reduce_sfr(raw, om, col):
    """Mean log10 SFR density in every redshift bin: the time integral of the logged total SFR over the bin divided by its duration, over the comoving volume of the box."""
    d = pd.read_csv(io.BytesIO(raw), sep=r"\s+", header=None, engine="c").values
    a, s = d[:, 0], d[:, col]
    order = np.argsort(a, kind="stable")
    a, s = a[order], s[order]
    _, last = np.unique(a[::-1], return_index=True)  # restarts repeat times: keep the last record of each
    keep = len(a) - 1 - last
    a, s = a[np.sort(keep)], s[np.sort(keep)]
    t = time_of_a(a, om)
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (s[1:] + s[:-1]) * np.diff(t))])
    edges_a = 1.0 / (1.0 + np.array(ZEDGES))  # decreasing z -> increasing a is reversed
    out = []
    for lo, hi in zip(ZEDGES[:-1], ZEDGES[1:]):
        a_hi, a_lo = 1.0 / (1.0 + lo), 1.0 / (1.0 + hi)
        if a_lo < a[0] or a_hi > a[-1] + 1e-6:
            out.append(None if a_lo < a[0] else None)
            continue
        c_hi, c_lo = np.interp(a_hi, a, cum), np.interp(a_lo, a, cum)
        dt = float(time_of_a(a_hi, om) - time_of_a(a_lo, om))
        mean = (c_hi - c_lo) / dt
        out.append(round(float(np.log10(mean / VOLUME)), 4) if mean > 0 else None)
    return out, float(np.trapezoid(s, t) if hasattr(np, "trapezoid") else np.trapz(s, t))


def one(args):
    suite, sset, name, om, col = args
    url = f"{BASE}/Sims/{suite}/{sset}/{name}/extra_files/sfr.txt"
    raw = get(url)
    sfrd, integral = reduce_sfr(raw, om, col)
    return name, {"sfrd": sfrd, "formedMassMsun": float(f"{integral:.4e}"), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def parameters(suite, sset):
    txt = get(f"{BASE}/Parameters/{SUITES[suite]['param_dir']}/CosmoAstroSeed_{suite}_L25n256_{sset}.txt").decode()
    rows = {}
    for line in txt.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        f = line.split()
        rows[f[0]] = {"params": dict(zip(PARAMS, (float(v) for v in f[1:7]))), "seed": int(float(f[7]))}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "data" / "ensembles" / "camels-sfrd.json"))
    args = ap.parse_args()
    result = {"schemaVersion": "1.0.0", "source": "CAMELS first-generation simulations (Villaescusa-Navarro et al. 2021, ApJ 915, 71; arXiv:2010.00619), sfr.txt logs written by the codes", "base": BASE,
              "volumeCMpc3": round(VOLUME, 1), "boxMpcPerH": BOX, "h": H, "zEdges": ZEDGES, "zCentres": ZGRID, "unit": "log10(Msun yr^-1 cMpc^-3)",
              "reduction": "time-averaged SFR in each redshift bin (trapezoid on the logged rows, duplicate times from restarts dropped), column 3 of the log (totsfrrate; equal on average to rate_in_msunperyear), divided by the comoving volume",
              "parameterMeaning": {"IllustrisTNG": {"ASN1": "galactic wind energy per unit star formation (x fiducial 3.6e51 erg)", "AAGN1": "kinetic-mode black hole feedback energy", "ASN2": "galactic wind speed", "AAGN2": "kinetic-mode feedback burstiness"},
                                   "SIMBA": {"ASN1": "mass loading of the galactic winds", "AAGN1": "momentum flux of the QSO and jet-mode black hole feedback", "ASN2": "galactic wind speed", "AAGN2": "jet speed of the jet-mode black hole feedback"}},
              "parameterRanges": {"Om": [0.1, 0.5], "s8": [0.6, 1.0], "ASN1": [0.25, 4.0], "AAGN1": [0.25, 4.0], "ASN2": [0.5, 2.0], "AAGN2": [0.5, 2.0]}, "suites": {}}
    t0 = time.time()
    for suite in SUITES:
        result["suites"][suite] = {}
        for sset, n in SETS.items():
            table = parameters(suite, sset)
            names = [k for k in table if k.startswith(sset + "_")]
            assert len(names) == n, (suite, sset, len(names))
            names = sorted(names, key=lambda k: int(k.split("_")[1]))[: args.limit]
            jobs = [(suite, sset, k, table[k]["params"]["Om"], SUITES[suite]["sfr_col"]) for k in names]
            sims = {}
            with ProcessPoolExecutor(args.workers) as ex:
                for k, (name, rec) in enumerate(ex.map(one, jobs, chunksize=2)):
                    sims[name] = {**table[name], **rec}
                    if (k + 1) % 50 == 0:
                        print(f"{suite} {sset}: {k + 1}/{len(jobs)}  {time.time() - t0:.0f} s", flush=True)
            result["suites"][suite][sset] = sims
            print(f"{suite} {sset}: {len(sims)} simulations  {time.time() - t0:.0f} s", flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, separators=(",", ":")) + "\n")
    print("wrote", args.out, Path(args.out).stat().st_size, "bytes")


if __name__ == "__main__":
    main()
