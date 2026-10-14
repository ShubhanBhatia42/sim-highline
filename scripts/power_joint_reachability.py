"""Calibration of the joint-reachability estimators of docs/PROTOCOL-joint-reachability.md (amendment A1) on synthetic two-code worlds. No real catalogue is read here, so nothing in this file depends on an outcome of the analysis.

A world has the block layout of the real eligible outputs (35 joint blocks and 169 outputs at z = 0, 0.95, 2.15, 3 and 4 plus the halo mass function control; protocol section 8), two codes with four parameters each, known
responses (linear, weakly quadratic, parametric spread of 3 to 30 noise units), heteroscedastic Gaussian noise, 4 % missing values, independent Latin-hypercube-like designs (1000 simulations per code) and 27 seeds. Because the
truth is known, the *true* distance of every world is computed from the noise-free responses (the same optimiser, weights and noise scale), and the verdicts are tabulated against it. Kinds of world:
  identical   both codes have the same function: true distance 0
  corner      the codes agree exactly, but only where the first code sits at a corner of its parameter box and the second at its fiducial point (the case that exposes emulator error at the edge)
  offset      every output of the second code is off by a fixed number of noise units
  shift       one family of the second code is shifted by a fixed number of noise units
  conflict    every family is reachable alone, but by a different parameter pair for each family
`world()` is the small one-snapshot world used by the unit tests. Writes data/analysis/joint-reachability-power.json and docs/POWER-joint-reachability.md.
Usage: python3 scripts/power_joint_reachability.py [--quick]   (about an hour on four cores; --quick is a smoke test and writes nothing)."""
import argparse
import itertools
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_joint_reachability as J
import analyze_model_form as A
import ingest_camels_galaxies as G
import modelform_stats as ms

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261017


def world(kind, seed, n_lh=1000, n_cv=27, snaps=("090", "062"), shift=0.0, shift_family="bhocc", noise=0.1, resp=0.25):
    """A synthetic dataset in the structure of `load_galaxies`."""
    cols = [(f, s, b) for s in snaps for f in J.FAMILIES for b in range(G.FAMILY_BINS[f])]
    P = len(cols)
    r = np.random.default_rng(seed)
    base = r.uniform(-1, 1, P)
    RT = r.normal(0, resp, (P, 4))
    RS = RT.copy() if kind != "conflict" else r.normal(0, resp, (P, 4))
    QT = r.normal(0, 0.03, (P, 4))
    fam_idx = {f: np.array([j for j, (g, s, b) in enumerate(cols) if g == f]) for f in J.FAMILIES}
    off = np.zeros(P)
    if kind == "shift":
        off[fam_idx[shift_family]] = shift
    if kind == "conflict":
        # each family reachable alone: S minus T is the difference of the two responses at a family-specific parameter pair
        for f, ix in fam_idx.items():
            u, v = r.uniform(-1, 1, 4), r.uniform(-1, 1, 4)
            off[ix] = (RT[ix] @ u) - (RS[ix] @ v)
    suites = {}
    for code, R, o in (("IllustrisTNG", RT, np.zeros(P)), ("SIMBA", RS, off)):
        rr = np.random.default_rng([seed, 1 if code == "IllustrisTNG" else 2])

        def sims(n, fixed):
            X = np.zeros((n, 6)) if fixed else rr.uniform(-1, 1, (n, 6))
            a = X[:, 2:]
            Y = base[None, :] + o[None, :] + a @ R.T + (a ** 2) @ QT.T + 0.05 * X[:, :1] + rr.normal(0, noise, (n, P))
            return {"X": X, "Y": Y, "names": [f"S_{i}" for i in range(n)]}
        suites[code] = {"LH": sims(n_lh, False), "CV": sims(n_cv, True)}
    return {"meta": {"snapshots": list(snaps), "z": {"090": 0.0, "062": 0.95, "042": 2.15, "032": 3.0, "024": 4.0}, "columns": cols, "families": J.FAMILIES}, "suites": suites}



# ---------------------------------------------------------------- worlds with the layout of the real eligible outputs
SNAPS = ("090", "062", "042", "032", "024")
Z = {"090": 0.0, "062": 0.95, "042": 2.15, "032": 3.0, "024": 4.0}
LAYOUT = {"gsmf": (9, 8, 5, 4, 0), "qf": (7, 6, 3, 0, 0), "sfms": (6, 6, 3, 0, 0), "bhms": (5, 4, 0, 0, 0), "bhocc": (7, 6, 3, 0, 0), "mzr": (6, 6, 3, 0, 0), "zstar": (7, 6, 3, 0, 0), "size": (7, 6, 3, 0, 0),
          "fgas": (7, 6, 3, 0, 0), "shmr": (5, 5, 4, 0, 0), "rho": (2, 2, 2, 2, 2), "hmf": (5, 5, 4, 3, 0)}
COLS = [(f, s, b) for s_i, s in enumerate(SNAPS) for f in J.FAMILIES for b in range(LAYOUT[f][s_i])]
NP = len(COLS)
PAIRS = list(itertools.combinations_with_replacement(range(6), 2))
FAM_IDX = {f: np.array([j for j, (g, s, b) in enumerate(COLS) if g == f]) for f in J.FAMILIES}


def make_params(kind, seed, amount=0.0, family="bhocc", sigma0=0.1, resp=0.25, corner=1.0):
    """The truth of a world: per code a baseline, linear responses R (NP x 4), quadratic Q (NP x 4) and a noise standard deviation per output; and what differs for the second code."""
    r = np.random.default_rng(seed)
    sig = sigma0 * r.uniform(0.5, 2.0, NP)
    base = r.uniform(-1, 1, NP)
    R = r.normal(0, resp, (NP, 4)) * r.choice([1.0, 3.0, 10.0], size=(NP, 1), p=[0.5, 0.35, 0.15])  # parametric spread of about 3 to 30 noise units
    Q = r.normal(0, 0.03, (NP, 4))
    codes = {"IllustrisTNG": {"base": base.copy(), "R": R.copy(), "Q": Q.copy()}, "SIMBA": {"base": base.copy(), "R": R.copy(), "Q": Q.copy()}}
    s_true = np.sqrt(2.0) * sig
    if kind == "shift":
        codes["SIMBA"]["base"][FAM_IDX[family]] += amount * s_true[FAM_IDX[family]]
    elif kind == "offset":
        codes["SIMBA"]["base"] += amount * s_true * r.choice([-1.0, 1.0], NP)
    elif kind == "conflict":
        codes["SIMBA"]["R"] = r.normal(0, resp, (NP, 4))
        for f, ix in FAM_IDX.items():
            u, v = r.uniform(-1, 1, 4), r.uniform(-1, 1, 4)
            codes["SIMBA"]["base"][ix] += (R[ix] @ u) - (codes["SIMBA"]["R"][ix] @ v)
    elif kind == "corner":
        c = np.full(4, float(corner))  # the second code's function is the first code's seen from a point `corner` away along every coordinate: S(a) = T(c + a)
        codes["SIMBA"]["base"] = base + R @ c + Q @ (c ** 2)
        codes["SIMBA"]["R"] = R + 2 * Q * c[None, :]
    return {"kind": kind, "seed": seed, "sigma": sig, "codes": codes, "amount": amount, "family": family, "corner": corner}


def function(par, code, a):
    """Noise-free outputs of a code at rows of four astrophysical coordinates (cosmology at the fiducial value)."""
    c = par["codes"][code]
    a = np.atleast_2d(a)
    return c["base"][None, :] + a @ c["R"].T + (a ** 2) @ c["Q"].T


def sample(par, n_lh=1000, n_cv=27, nan_rate=0.04):
    suites = {}
    for k, code in enumerate(("IllustrisTNG", "SIMBA")):
        rr = np.random.default_rng([par["seed"], 11 + k])

        def sims(n, fixed):
            X = np.zeros((n, 6)) if fixed else rr.uniform(-1, 1, (n, 6))
            Y = function(par, code, X[:, 2:]) + 0.05 * X[:, :1] + rr.normal(0, 1, (n, NP)) * par["sigma"][None, :]
            miss = rr.random((n, NP)) < nan_rate
            if fixed:
                miss[:, :] = False
                miss[rr.integers(0, n, 3), rr.integers(0, NP, 3)] = True
            Y[miss] = np.nan
            return {"X": X, "Y": Y, "names": [f"S_{i}" for i in range(n)]}
        suites[code] = {"LH": sims(n_lh, False), "CV": sims(n_cv, True)}
    return {"meta": {"snapshots": list(SNAPS), "z": Z, "columns": COLS, "families": J.FAMILIES}, "suites": suites}


def true_emulator(par, code):
    """The exact polynomial of the code in the feature space of the emulators (degree 2, six coordinates): an Emulator whose coefficients are the truth."""
    c = par["codes"][code]
    e = ms.Emulator(2, 0.0)
    coef = np.zeros((28, NP))
    coef[0] = c["base"]
    coef[1] = 0.05  # the cosmology term, vanishing at the fiducial cosmology
    for j in range(4):
        coef[1 + 2 + j] = c["R"][:, j]
        coef[7 + PAIRS.index((2 + j, 2 + j))] = c["Q"][:, j]
    e.coef = coef
    return e


def blocks_of_layout():
    d = {"meta": {"columns": COLS}, "suites": {s: {"LH": {"Y": np.zeros((100, NP))}, "CV": {"Y": np.random.default_rng(0).normal(size=(27, NP))}} for s in J.SUITES}}
    return J.eligibility(d)[1]


def true_distance(par, nstarts=24):
    """True distance of the world, for the joint set and for each family alone, with the weights and noise scale of the analysis but noise-free responses and no emulator error."""
    scale = np.sqrt(2.0) * par["sigma"]
    blocks = blocks_of_layout()
    ibb = {b: np.array(v) for b, v in blocks.items()}
    et, es = true_emulator(par, "IllustrisTNG"), true_emulator(par, "SIMBA")
    sets = {"all": [b for b in blocks if b[0] != "hmf"], **{"fam:" + f: [b for b in blocks if b[0] == f] for f in J.JOINT_FAMILIES}}
    out = {}
    for name, bl in sets.items():
        idx, c = J.make_set(ibb, bl, scale)
        out[name] = J.distance(et, es, idx, c, np.random.default_rng([par["seed"], 5]), nstarts=nstarts)[0]
    return out


def verdict_raw(r):
    """The rule of the analysis applied to the uncorrected distributions, summarised by their 5th, 50th and 95th percentiles (for comparison only)."""
    return A.e3_verdict(np.array([r["between_raw"]["p5"], r["between_raw"]["p50"], r["between_raw"]["p95"]]), np.array([r["control_raw"]["p95"]]), J.MARGIN)


def one(args):
    kind, amount, family, corner, rep, seed, n_lh, nsplit = args
    par = make_params(kind, seed + rep, amount=amount, family=family, corner=corner)
    td = true_distance(par, nstarts=6 if nsplit < 10 else 24)
    res = J.run(data=sample(par, n_lh=n_lh), nsplit=nsplit, nsmall=max(4, nsplit // 2), npath=max(3, nsplit // 4), nstarts=4, sens=False, workers=1)
    s, p = res["splits"], res["point"]
    fam = {f: s["fam:" + f]["verdict"] for f in J.JOINT_FAMILIES if s.get("fam:" + f)}
    a = s["all"]
    return {"kind": kind, "amount": amount, "family": family, "corner": corner, "rep": rep, "true_D_all": td["all"], "true_D_fam": {f: td["fam:" + f] for f in J.JOINT_FAMILIES}, "D_point": p["all"]["D"], "D_point_corrected": p["all"].get("D_corrected"),
            "between_corrected": a["between"], "between_raw": a["between_raw"], "control_p95_corrected": a["control"]["p95"], "J1_corrected": a["verdict"], "J1_raw": verdict_raw(a), "J1_range75": (s.get("all@0.75") or {}).get("verdict"),
            "J2": fam, "J2_raw": {f: verdict_raw(s["fam:" + f]) for f in fam}, "J2_structural": [f for f, x in fam.items() if x == "structural"], "J2_unresolved": [f for f, x in fam.items() if x == "unresolved"],
            "J3": res["J3"]["mechanism"], "J3_above_null": res["J3"]["above_null"], "ratio_between_p50": res["J3"]["ratio_between"]["p50"], "ratio_control_p95": res["J3"]["ratio_control"]["p95"], "V2": res["validations"]["V2"]["verdict"]}


def run(quick):
    t0 = time.time()
    n_lh, nsplit = (300, 4) if quick else (1000, 30)
    reps = 1 if quick else 2
    jobs = []
    seed = SEED
    for rep in range(1 if quick else 3):
        jobs.append(("identical", 0.0, "bhocc", 1.0, rep, seed, n_lh, nsplit))
    for corner in ((1.0,) if quick else (1.0, 0.75, 0.5)):
        for rep in range(reps):
            jobs.append(("corner", 0.0, "bhocc", corner, rep, seed + 100 * int(corner * 100), n_lh, nsplit))
    for amount in ((1.0,) if quick else (0.3, 0.6, 1.0, 1.5)):
        for rep in range(reps):
            jobs.append(("offset", amount, "bhocc", 1.0, rep, seed + 5000 + int(amount * 100), n_lh, nsplit))
    for amount in ((4.0,) if quick else (1.0, 2.0, 4.0, 8.0)):
        for rep in range(reps):
            jobs.append(("shift", amount, "bhocc", 1.0, rep, seed + 9000 + int(amount * 100), n_lh, nsplit))
    for rep in range(reps):
        jobs.append(("conflict", 0.0, "bhocc", 1.0, rep, seed + 13000, n_lh, nsplit))
    with mp.Pool(4) as pool:
        rows = pool.map(one, jobs, chunksize=1)
    return {"seed": SEED, "quick": quick, "rows": rows, "elapsed_s": round(time.time() - t0), "layout": {f: list(v) for f, v in LAYOUT.items()}, "n_outputs": NP}


def render(out):
    L = ["# Calibration of the joint-reachability estimators on synthetic worlds", "",
         f"Generated by `scripts/power_joint_reachability.py` (seed {out['seed']}); nothing here reads a real catalogue. Protocol: [`PROTOCOL-joint-reachability.md`](PROTOCOL-joint-reachability.md), amendment A1.", "",
         "Worlds have the block layout of the real eligible outputs (35 joint blocks, 169 outputs, plus the halo mass function control; z = 0, 0.95, 2.15, 3, 4), heteroscedastic noise (seed scatter 0.05 to 0.2), 4 % missing values, 1000 + 27 simulations per code with independent designs, and responses of 3 to 30 noise units. "
         "The *true* distance is computed from the noise-free responses with the weights and noise scale of the analysis (so it is the quantity the verdict should recover; 1 is the margin). Verdicts are those of the analysis (emulator-corrected) and, for comparison, the same rule on the uncorrected distributions (raw). "
         "*corner*: the codes agree exactly, but only with the first code at a corner of its parameter box (radius r) and the second at its fiducial point; *offset*: every output of the second code is off by a fixed number of noise units; *shift*: one family (black hole occupation) is off; *conflict*: every family reachable alone by its own parameter pair.", "",
         "| world | parameter | runs | true D (all) | median D estimate, corrected (raw) | J1 verdict, corrected | J1 verdict, raw | J1 at 75 % range | families structural alone (true D of the shifted family) | J3 class | V2 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    par_of = lambda r: r["amount"] if r["kind"] in ("offset", "shift") else r["corner"] if r["kind"] == "corner" else 0.0
    keys = sorted({(r["kind"], par_of(r)) for r in out["rows"]}, key=lambda k: (["identical", "corner", "offset", "shift", "conflict"].index(k[0]), k[1]))
    for kind, par in keys:
        rs = [r for r in out["rows"] if r["kind"] == kind and par_of(r) == par]
        cnt = lambda f: ", ".join(f"{v} {sum(1 for r in rs if str(r[f]) == v)}" for v in sorted({str(r[f]) for r in rs}))
        st = {}
        for r in rs:
            for f in r["J2_structural"]:
                st[f] = st.get(f, 0) + 1
        sh = f" ({np.median([r['true_D_fam'][rs[0]['family']] for r in rs]):.2f})" if kind == "shift" else ""
        L.append(f"| {kind} | {par if kind in ('offset', 'shift', 'corner') else ''} | {len(rs)} | {np.median([r['true_D_all'] for r in rs]):.2f} | {np.median([r['between_corrected']['p50'] for r in rs]):.2f} ({np.median([r['between_raw']['p50'] for r in rs]):.2f}) | {cnt('J1_corrected')} | {cnt('J1_raw')} | {cnt('J1_range75')} | {', '.join(f'{f} ({n}/{len(rs)})' for f, n in sorted(st.items())) or 'none'}{sh} | {cnt('J3')} | {cnt('V2')} |")
    L += ["", "`python3 scripts/power_joint_reachability.py` rewrites this file and `data/analysis/joint-reachability-power.json`.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = run(args.quick)
    if args.quick:
        print(render(out))
        return
    (ROOT / "data" / "analysis" / "joint-reachability-power.json").write_text(json.dumps(out, indent=1, default=lambda o: float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else str(o)) + "\n")
    (ROOT / "docs" / "POWER-joint-reachability.md").write_text(render(out))
    print("written; elapsed", out["elapsed_s"], "s")


if __name__ == "__main__":
    main()
