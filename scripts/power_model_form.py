"""Calibration of the estimators of docs/PROTOCOL-model-form.md on synthetic data. No real curve and no CAMELS simulation is read here, so nothing in this file depends on an outcome of the analysis.

E1: false-positive rate and power of the funnel rule (Pitman-Morgan p < 0.05 and a 90 % cluster-bootstrap lower bound > 0) for seven families of Gaussian-process offsets on the real grid, for a stationary
    null, for growing spread (ratios 1.5 to 5, two correlation lengths) and for nulls that violate the assumptions of the test (different persistence in the two bands, heavy tails, excursions).
E3, E4: synthetic twin codes (1000 Latin-hypercube-like simulations plus 27 seeds each, seed scatter 0.1 dex) whose responses to four parameters are known and which differ by a known step above z = 3.5:
    what the verdict of E3 (reachability against matched-size controls and the seed margin) and of E4 (calibrate to the same curve at z <= 3, compare 90 % intervals at z >= 4.1) say as the step grows,
    for a weak and a strong response of the parameters.
Writes data/analysis/model-form-power.json and docs/POWER-model-form.md. Usage: python3 scripts/power_model_form.py [--quick]   (about 15 minutes on four cores; --quick runs a smoke-sized version and writes nothing)."""
import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_model_form as A
import modelform_stats as ms

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261016
GRID = A.Z_PUB
N_FAM = 7


def amp_curve(ratio, z=GRID):
    """Standard deviation (dex) of the offsets: 0.15 at z <= 1.75, growing log-linearly by `ratio` to z = 6.25."""
    return 0.15 * ratio ** np.clip((z - 1.75) / 4.5, 0, 1)


def draw_rows(scenario, ratio, ell, rng):
    """N_FAM rows of offsets on the real grid for a scenario."""
    amp = amp_curve(ratio)
    if scenario == "stationary":
        return ms.gp_draws(GRID, amp, ell, rng, N_FAM)
    lo, hi = GRID < 4.0, GRID >= 4.0
    if scenario in ("persistence_low_wiggly", "persistence_low_persistent"):
        ell_lo, ell_hi = (0.35, 6.0) if scenario == "persistence_low_wiggly" else (6.0, 0.35)
        out = np.zeros((N_FAM, len(GRID)))
        out[:, lo] = ms.gp_draws(GRID[lo], np.full(lo.sum(), 0.15), ell_lo, rng, N_FAM)
        out[:, hi] = ms.gp_draws(GRID[hi], np.full(hi.sum(), 0.15), ell_hi, rng, N_FAM)
        return out
    base = ms.gp_draws(GRID, np.full(len(GRID), 0.15), 1.5, rng, N_FAM)
    if scenario == "t3_shared":  # a multivariate t with 3 degrees of freedom per family
        return base * np.sqrt(3.0 / rng.chisquare(3, size=(N_FAM, 1)))
    if scenario == "t3_per_band":
        sl, sh = np.sqrt(3.0 / rng.chisquare(3, size=(N_FAM, 1))), np.sqrt(3.0 / rng.chisquare(3, size=(N_FAM, 1)))
        return base * np.where(GRID[None, :] < 4.0, sl, sh)
    if scenario == "excursions":  # a smooth bump of 0.5 dex in a band with probability 0.1 per family and band
        out = base.copy()
        for i in range(N_FAM):
            for band in ((0.5, 3.0), (5.0, 7.5)):
                if rng.random() < 0.1:
                    c = rng.uniform(*band)
                    out[i] += rng.choice([-1, 1]) * 0.5 * np.exp(-0.5 * ((GRID - c) / 0.7) ** 2)
        return out
    raise ValueError(scenario)


def e1_chunk(args):
    scenario, ratio, ell, nrep, seed, nboot = args
    rng = np.random.default_rng(seed)
    pm = ci = both = 0
    phis = []
    for k in range(nrep):
        Y = draw_rows(scenario, ratio, ell, rng)
        r = A.pub_funnel(Y, GRID, np.random.default_rng([seed, k]), nboot)
        if "phi_ci90" not in r:
            continue
        a, b = r["pitman_morgan"]["p_one_sided"] < 0.05, r["phi_ci90"][0] > 0
        pm += a
        ci += b
        both += a and b
        phis.append(r["phi"])
    return {"scenario": scenario, "ratio": ratio, "ell": ell, "n": len(phis), "pm": pm, "ci": ci, "both": both, "phi_sum": float(np.sum(phis))}


def twin_world(step, scale, seed, noise=0.1):
    """Two synthetic CAMELS-like codes on the real redshift grid: the observed curve (Madau and Dickinson, Chabrier) minus 0.05 dex as the fiducial SFRD of both, four known responses (weak: 0.25, 0.2, 0.15, 0.1 dex per unit
    coordinate, multiplied by `scale`; the second code responds 10 % more), and a step of `step` dex above z = 3.5 in the second code."""
    zc = np.round(np.arange(0.1, 13.95, 0.2), 1)
    base = A.madau_dickinson(zc) - 0.05
    shp = np.array([np.exp(-0.5 * ((zc - c) / 2.5) ** 2) for c in (1.0, 3.0, 5.0, 7.0)])
    suites = {}
    for code, off, mult, k in (("IllustrisTNG", 0.0, 1.0, 1), ("SIMBA", step, 1.1, 2)):
        rr = np.random.default_rng([seed, k])
        resp = np.array([0.25, 0.2, 0.15, 0.1]) * scale * mult

        def sims(n, prefix, fixed):
            out = {}
            for i in range(n):
                p = ({"Om": 0.3, "s8": 0.8, "ASN1": 1.0, "AAGN1": 1.0, "ASN2": 1.0, "AAGN2": 1.0} if fixed else
                     {"Om": float(rr.uniform(0.1, 0.5)), "s8": float(rr.uniform(0.6, 1.0)), "ASN1": float(4 ** rr.uniform(-1, 1)), "AAGN1": float(4 ** rr.uniform(-1, 1)), "ASN2": float(2 ** rr.uniform(-1, 1)), "AAGN2": float(2 ** rr.uniform(-1, 1))})
                x = A.to_x(p)
                y = base + off * (zc > 3.5) + 0.1 * x[0] + x[2:] @ (resp[:, None] * shp) + rr.normal(0, noise, len(zc))
                out[f"{prefix}_{i}"] = {"params": p, "seed": i, "sfrd": [round(float(v), 4) for v in y]}
            return out
        suites[code] = {"LH": sims(1000, "LH", False), "CV": sims(27, "CV", True)}
    return {"zEdges": [round(v, 1) for v in np.arange(0, 14.01, 0.2)], "zCentres": [float(v) for v in zc], "suites": suites}


def twin_chunk(args):
    step, scale, rep, seed, ncontrol = args
    data = twin_world(step, scale, seed + rep)
    A.load_camels = lambda path=None: data
    res = A.run_camels(None, seed + rep, nboot=0, ncontrol=ncontrol, nstarts=3, sensitivity=False)
    r, k = res["reachability"], res["calibration"]
    return {"step": step, "scale": scale, "rep": rep, "E3_verdict": r["verdict"], "D_full": r["full"]["D_dex"], "between_p5": r["between_full"]["p5"], "between_p95": r["between_full"]["p95"], "control_p95": r["controls_full"]["p95"], "margin": r["margin_dex"],
            "E3_high_verdict": r["between_bands"]["high"]["verdict"], "E4_verdict": k["verdict"], "E4_disjoint": k["disjoint_fraction"],
            "E4_width_median": float(np.median([w for c in k["codes"].values() for w in c["interval_width"]])), "E4_ess_min": min(c["ess"] for c in k["codes"].values())}


def run(quick):
    t0 = time.time()
    nrep_e1, nboot, ncontrol, reps = (6, 40, 6, 1) if quick else (200, 300, 40, 3)
    nrep_null = 6 if quick else 400
    jobs = []
    seed = SEED
    for ell in (1.0, 2.5):
        for ratio in (1.0, 1.5, 2.0, 3.0, 5.0):
            for part in range(4):
                jobs.append(("stationary", ratio, ell, nrep_e1 // 4 if not quick else nrep_e1, seed, nboot))
                seed += 1
    for scen in ("persistence_low_wiggly", "persistence_low_persistent", "t3_shared", "t3_per_band", "excursions"):
        for part in range(4):
            jobs.append((scen, 1.0, 1.5, nrep_null // 4 if not quick else nrep_null, seed, nboot))
            seed += 1
    with mp.Pool(4) as pool:
        parts = pool.map(e1_chunk, jobs)
    agg = {}
    for p in parts:
        key = (p["scenario"], p["ratio"], p["ell"])
        a = agg.setdefault(key, {"scenario": p["scenario"], "ratio": p["ratio"], "ell": p["ell"], "n": 0, "pm": 0, "ci": 0, "both": 0, "phi_sum": 0.0})
        for f in ("n", "pm", "ci", "both", "phi_sum"):
            a[f] += p[f]
    e1 = []
    for a in agg.values():
        n = max(a["n"], 1)
        e1.append({"scenario": a["scenario"], "true_sd_ratio": a["ratio"], "correlation_length": a["ell"], "replicates": a["n"], "rule_met": a["both"] / n, "pitman_morgan_only": a["pm"] / n, "bootstrap_only": a["ci"] / n,
                   "phi_mean": a["phi_sum"] / n, "phi_true": float(np.log10(a["ratio"]))})
    tjobs = [(step, scale, rep, SEED + 1000 * (1 + int(scale)) + 10 * int(step * 10), ncontrol) for step in ((0.0, 0.6) if quick else (0.0, 0.15, 0.3, 0.6, 1.0)) for scale in (1.0, 3.0) for rep in range(reps)]
    with mp.Pool(4) as pool:
        twins = pool.map(twin_chunk, tjobs)
    out = {"seed": SEED, "quick": quick, "E1": e1, "twins": twins, "elapsed_s": round(time.time() - t0)}
    return out


def render(out):
    def pc(x):
        return f"{100 * x:.0f} %"
    L = ["# Calibration of the estimators of the model-form analysis on synthetic data", "",
         "Generated by `scripts/power_model_form.py` (seed %d); nothing here reads a real curve or a CAMELS simulation. Protocol: [`PROTOCOL-model-form.md`](PROTOCOL-model-form.md), section 5." % out["seed"], "",
         "## E1: the funnel rule", "", "Seven families of Gaussian-process offsets on the real grid (z = 0.25 to 8), standard deviation 0.15 dex growing log-linearly by the stated ratio between z = 1.75 and 6.25. Rule met = both conditions; the two parts are given alone.", ""]
    rows = [r for r in out["E1"] if r["scenario"] == "stationary"]
    L += ["| true SD ratio | correlation length | replicates | rule met | Pitman-Morgan alone | bootstrap alone |", "|---|---|---|---|---|---|"]
    L += [f"| {r['true_sd_ratio']} | {r['correlation_length']} | {r['replicates']} | {pc(r['rule_met'])} | {pc(r['pitman_morgan_only'])} | {pc(r['bootstrap_only'])} |" for r in sorted(rows, key=lambda r: (r["true_sd_ratio"], r["correlation_length"]))]
    L += ["", "Nulls that break the assumptions of the test (equal spread in both bands; correlation length 1.5 unless stated). Persistence: bands of correlation length 0.35 and 6 (or the reverse); t3: offsets scaled by a Student-t factor with 3 degrees of freedom, shared by both bands or independent per band; excursions: a 0.5 dex bump in a band with probability 0.1 per family and band.", "",
          "| scenario | replicates | rule met | Pitman-Morgan alone | bootstrap alone |", "|---|---|---|---|---|"]
    L += [f"| {r['scenario']} | {r['replicates']} | {pc(r['rule_met'])} | {pc(r['pitman_morgan_only'])} | {pc(r['bootstrap_only'])} |" for r in out["E1"] if r["scenario"] != "stationary"]
    L += ["", "## E3 and E4 on synthetic twin codes", "",
          "Two codes with the same four-parameter responses (scaled by `scale`: 1 gives the rms parametric spread of a few tenths of a dex, 3 a strong response; the second code responds 10 % more), seed scatter 0.1 dex, identical below z = 3.5 and offset by `step` dex above it; both calibrated to the Madau and Dickinson curve at z <= 2.9.", "",
          "| step (dex) | scale | runs | E3 verdicts | median D after retuning | E3 high-band verdicts | E4 verdicts | median E4 disjoint share | median E4 interval width (dex) |", "|---|---|---|---|---|---|---|---|---|"]
    keys = sorted({(t["step"], t["scale"]) for t in out["twins"]})
    for st, sc in keys:
        ts = [t for t in out["twins"] if t["step"] == st and t["scale"] == sc]
        cnt = lambda f: ", ".join(f"{v} {sum(1 for t in ts if t[f] == v)}" for v in sorted({t[f] for t in ts}))
        L.append(f"| {st} | {sc} | {len(ts)} | {cnt('E3_verdict')} | {np.median([t['D_full'] for t in ts]):.3f} | {cnt('E3_high_verdict')} | {cnt('E4_verdict')} | {pc(np.median([t['E4_disjoint'] for t in ts]))} | {np.median([t['E4_width_median'] for t in ts]):.2f} |")
    L += ["", "`python3 scripts/power_model_form.py` rewrites this file and `data/analysis/model-form-power.json`.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = run(args.quick)
    if args.quick:
        print(render(out)[:2000])
        return
    (ROOT / "data" / "analysis" / "model-form-power.json").write_text(json.dumps(out, indent=1, default=lambda o: float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else str(o)) + "\n")
    (ROOT / "docs" / "POWER-model-form.md").write_text(render(out))
    print("written; elapsed", out["elapsed_s"], "s")


if __name__ == "__main__":
    main()
