"""Can retuning make two feedback models agree on every galaxy observable at once? IllustrisTNG and SIMBA in CAMELS.

Implements docs/PROTOCOL-joint-reachability.md section by section; every departure is reported as a deviation in the generated docs/ANALYSIS-joint-reachability.md. Reads data/ensembles/camels-galaxies.json (written by
scripts/ingest_camels_galaxies.py) and data/ensembles/camels-sfrd.json (validations). Writes data/analysis/joint-reachability.json and docs/ANALYSIS-joint-reachability.md. Nothing here changes a stored record."""
import copy
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_model_form as A
import modelform_stats as ms

warnings.filterwarnings("ignore", category=RuntimeWarning, message="(Mean of empty slice|All-NaN slice|Degrees of freedom|invalid value)")
ROOT = Path(__file__).resolve().parent.parent
SEED = 20261016
FAMILIES = ["gsmf", "qf", "sfms", "bhms", "bhocc", "mzr", "zstar", "size", "fgas", "shmr", "rho", "hmf"]
JOINT_FAMILIES = [f for f in FAMILIES if f != "hmf"]
FAMILY_NAMES = {"gsmf": "stellar mass function", "qf": "quenched fraction", "sfms": "star-forming main sequence", "bhms": "black hole mass at fixed M*", "bhocc": "black hole occupation", "mzr": "gas metallicity at fixed M*",
                "zstar": "stellar metallicity at fixed M*", "size": "stellar half-mass radius at fixed M*", "fgas": "gas fraction at fixed M*", "shmr": "stellar-to-halo mass ratio", "rho": "stellar mass and SFR density", "hmf": "halo mass function (negative control)"}
MARGIN = 1.0
FLOOR = 0.02
MIN_FINITE_LH, MIN_CV = 0.9, 20
DEGREE_Z_NOTE = "degree chosen per code by 10-fold cross-validation over all eligible outputs (protocol section 4)"
SUITES = ("IllustrisTNG", "SIMBA")


# ---------------------------------------------------------------- data
def load_galaxies(path=None):
    d = json.loads(Path(path or ROOT / "data" / "ensembles" / "camels-galaxies.json").read_text())
    snaps = list(d["snapshots"])
    cols = [(f, s, b) for s in snaps for f in FAMILIES for b in range(d["familyBins"][f])]
    out = {"meta": {"snapshots": snaps, "z": {s: d["snapshots"][s] for s in snaps}, "columns": cols, "families": FAMILIES}, "suites": {}}
    for suite in SUITES:
        arr = {}
        for sset in ("LH", "CV"):
            sims = d["suites"][suite][sset]
            names = sorted(sims, key=lambda k: int(k.split("_")[1]))
            X = np.array([A.to_x(sims[n]["params"]) for n in names])
            Y = np.full((len(names), len(cols)), np.nan)
            for i, n in enumerate(names):
                for j, (f, s, b) in enumerate(cols):
                    sn = sims[n]["snaps"].get(s)
                    if sn and "values" in sn:
                        v = sn["values"][f][b]
                        if v is not None:
                            Y[i, j] = v
            arr[sset] = {"X": X, "Y": Y, "names": names}
        out["suites"][suite] = arr
    return out


def block_of(cols):
    return [(f, s) for f, s, _ in cols]


def eligibility(data):
    cols = data["meta"]["columns"]
    ok = np.ones(len(cols), bool)
    detail = {}
    for suite in SUITES:
        lh, cv = data["suites"][suite]["LH"]["Y"], data["suites"][suite]["CV"]["Y"]
        fl, fc = np.isfinite(lh).mean(axis=0), np.isfinite(cv).sum(axis=0)
        e = (fl >= MIN_FINITE_LH) & (fc >= MIN_CV)
        detail[suite] = {"finite_lh": fl, "finite_cv": fc, "ok": e}
        ok &= e
    blocks = {}
    for j, ((f, s, b), e) in enumerate(zip(cols, ok)):
        if e:
            blocks.setdefault((f, s), []).append(j)
    nb = {}
    for f, sn, b in cols:
        nb[(f, sn)] = nb.get((f, sn), 0) + 1
    blocks = {k: v for k, v in blocks.items() if len(v) >= min(3, nb[k])}  # a block needs 3 eligible outputs, or all of them if it has fewer (the two densities)
    keep = np.zeros(len(cols), bool)
    for v in blocks.values():
        keep[v] = True
    return keep, blocks, detail


# ---------------------------------------------------------------- emulators and noise
def mean_cv_ratio(X, Y, Ycv, degree, cols, ridge=A.RIDGE, h=A.KERNEL_H, seed=0):
    cv, _ = A.cv_errors(X, Y, degree, ridge, h, seed=seed)
    sn = np.nanstd(Ycv, axis=0, ddof=1)
    return float(np.nanmean((cv / np.maximum(sn, FLOOR))[cols]))


def choose_degree_joint(X, Y, Ycv, cols, ridge=A.RIDGE, h=A.KERNEL_H):
    e2 = mean_cv_ratio(X, Y, Ycv, 2, cols, ridge, h)
    e3 = mean_cv_ratio(X, Y, Ycv, 3, cols, ridge, h)
    return (3 if e3 < 0.98 * e2 else 2), e2, e3


def build_emulators(data, keep, degrees=None, ridge=A.RIDGE, h=A.KERNEL_H):
    """Per code: emulator on all outputs, degree, seed noise, cross-validation error (fold assignment different from the one that chose the degree)."""
    emus, info = {}, {}
    for suite in SUITES:
        lh, cv = data["suites"][suite]["LH"], data["suites"][suite]["CV"]
        if degrees and degrees.get(suite):
            deg, e2, e3 = degrees[suite], None, None
        else:
            deg, e2, e3 = choose_degree_joint(lh["X"], lh["Y"], cv["Y"], keep, ridge, h)
        emus[suite] = A.fit_emulator(lh["X"], lh["Y"], deg, ridge, h)
        cvr, ncv = A.cv_errors(lh["X"], lh["Y"], deg, ridge, h, seed=1)
        sn = np.nanstd(cv["Y"], axis=0, ddof=1)
        info[suite] = {"degree": deg, "cv_rmse": cvr, "seed_noise": sn, "emulator_error": np.sqrt(np.maximum(0.0, cvr ** 2 - sn ** 2)), "cv_mean": np.nanmean(cv["Y"], axis=0), "mean_cv_ratio_deg2": e2, "mean_cv_ratio_deg3": e3, "n_cv_test": ncv}
    return emus, info


def noise_scale(info, floor=FLOOR, with_emulator_error=True):
    t, s = info["IllustrisTNG"], info["SIMBA"]
    v = t["seed_noise"] ** 2 + s["seed_noise"] ** 2
    if with_emulator_error:
        v = v + t["emulator_error"] ** 2 + s["emulator_error"] ** 2
    return np.maximum(np.sqrt(v), floor)


def make_set(idx_by_block, blocks, scale):
    """Outputs and scaling of a set of blocks: column indices and c_k = sqrt(w_k) / s_k, with w_k giving every block the same total weight and mean(w) = 1 over the set."""
    idx = np.concatenate([idx_by_block[b] for b in blocks])
    wb = np.concatenate([np.full(len(idx_by_block[b]), 1.0 / len(idx_by_block[b])) for b in blocks])
    wb = wb / wb.mean()
    return idx, np.sqrt(wb) / scale[idx]


def scaled(emu, idx, c):
    e = ms.Emulator(emu.degree, emu.ridge)
    e.coef = emu.coef[:, idx] * c[None, :]
    return e


def distance(emu_t, emu_s, idx, c, rng, lam=1.0, nstarts=4):
    et, es = scaled(emu_t, idx, c), scaled(emu_s, idx, c)
    d, a = A.reachability(et, es, np.ones(len(idx), bool), rng, lam=lam, nstarts=nstarts)
    return d, a


def fiducial_distance(emu_t, emu_s, idx, c):
    z = np.zeros((1, 4))
    pt, ps = A.predict_astro(scaled(emu_t, idx, c), z)[0], A.predict_astro(scaled(emu_s, idx, c), z)[0]
    return float(np.sqrt(np.nanmean((pt - ps) ** 2)))


# ---------------------------------------------------------------- the sets of outputs
def define_sets(blocks, snaps, path=None):
    """Named sets of blocks: all (joint, without hmf), each family alone, each snapshot (all joint families), the hmf control, and optionally the nested sets of a greedy path and the drop-one sets."""
    fam_blocks = {f: [b for b in blocks if b[0] == f] for f in FAMILIES}
    sets = {"all": [b for b in blocks if b[0] != "hmf"]}
    for f in FAMILIES:
        if fam_blocks[f]:
            sets["fam:" + f] = fam_blocks[f]
    for s in snaps:
        bs = [b for b in sets["all"] if b[1] == s]
        if len(bs) >= 3:
            sets["z:" + s] = bs
    for f in JOINT_FAMILIES:
        rest = [b for b in sets["all"] if b[0] != f]
        if fam_blocks[f] and rest:
            sets["drop:" + f] = rest
    if path:
        for j in range(1, len(path) + 1):
            sets[f"path:{j}"] = [b for f in path[:j] for b in fam_blocks[f]]
    return sets


def greedy_path(emus, scale, idx_by_block, sets, rng, nstarts=4):
    """Forward selection of families: at every step the family whose addition gives the largest point distance."""
    fams = [f for f in JOINT_FAMILIES if sets.get("fam:" + f)]
    chosen, steps = [], []
    while len(chosen) < len(fams):
        best = None
        for f in fams:
            if f in chosen:
                continue
            bl = [b for g in chosen + [f] for b in sets["fam:" + g]]
            idx, c = make_set(idx_by_block, bl, scale)
            d, _ = distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, rng, nstarts=nstarts)
            if best is None or d > best[1]:
                best = (f, d)
        chosen.append(best[0])
        steps.append({"family": best[0], "D": best[1]})
    return chosen, steps


_CTX = {}


def _split_worker(k):
    """One split (module level so that a forked pool can run it): halves of both codes, then every set whose count exceeds k."""
    c = _CTX
    rng = np.random.default_rng([SEED, 53, k])
    halves = {}
    for suite in SUITES:
        lh = c["data"]["suites"][suite]["LH"]
        ia, ib = A.split_halves(len(lh["X"]), rng)
        halves[suite] = (A.fit_emulator(lh["X"][ia], lh["Y"][ia], c["degrees"][suite]), A.fit_emulator(lh["X"][ib], lh["Y"][ib], c["degrees"][suite]))
    out = {}
    for name, (idx, cc) in c["prepared"].items():
        if k >= c["counts"][name]:
            continue
        b = distance(halves["IllustrisTNG"][0], halves["SIMBA"][0], idx, cc, rng, nstarts=c["nstarts"])[0]
        out[name] = (b, distance(halves["IllustrisTNG"][0], halves["IllustrisTNG"][1], idx, cc, rng, nstarts=c["nstarts"])[0], distance(halves["SIMBA"][0], halves["SIMBA"][1], idx, cc, rng, nstarts=c["nstarts"])[0])
    return out


def reach_splits(data, degrees, scale, idx_by_block, sets, counts, nstarts, workers=4):
    """Matched-size comparison of protocol section 4: per split both codes' LH sets are divided in halves A and B; between = D(TNG A, SIMBA A), controls = D(TNG A, TNG B) and D(SIMBA A, SIMBA B), the same search effort for all.
    `counts` gives the number of splits used by each set (the first splits). Splits are independent and each has its own random stream, so they run in a forked pool without changing the result."""
    import multiprocessing as mp
    _CTX.clear()
    _CTX.update({"data": data, "degrees": degrees, "prepared": {name: make_set(idx_by_block, bl, scale) for name, bl in sets.items()}, "counts": counts, "nstarts": nstarts})
    n = max(counts.values())
    if workers > 1:
        with mp.get_context("fork").Pool(workers) as pool:
            parts = pool.map(_split_worker, range(n), chunksize=1)
    else:
        parts = [_split_worker(k) for k in range(n)]
    res = {name: {"between": [], "control_IllustrisTNG": [], "control_SIMBA": []} for name in sets}
    for part in parts:
        for name, (b, ct, cs) in part.items():
            res[name]["between"].append(b)
            res[name]["control_IllustrisTNG"].append(ct)
            res[name]["control_SIMBA"].append(cs)
    return res


def summarize_splits(r, margin=MARGIN):
    btw = np.array(r["between"])
    ctl = np.array(r["control_IllustrisTNG"] + r["control_SIMBA"])
    if btw.size == 0:
        return None
    return {"n": int(btw.size), "between": {"p5": A.pct(btw, 5), "p50": A.pct(btw, 50), "p95": A.pct(btw, 95)}, "control": {"median": A.pct(ctl, 50), "p95": A.pct(ctl, 95)}, "verdict": A.e3_verdict(btw, ctl, margin)}


# ---------------------------------------------------------------- the response (descriptive)
def response_table(emus, info, scale, blocks, idx_by_block):
    """Change of every block's outputs (rms over the block's outputs, in units of the noise scale) when one parameter moves from -1 to +1 at the others' fiducial values."""
    rows = {}
    for suite in SUITES:
        em = emus[suite]
        rows[suite] = {}
        for b in blocks:
            idx = idx_by_block[b]
            r = []
            for j in range(4):
                lo, hi = np.zeros((1, 4)), np.zeros((1, 4))
                lo[0, j], hi[0, j] = -1.0, 1.0
                d = (A.predict_astro(em, hi)[0] - A.predict_astro(em, lo)[0])[idx] / scale[idx]
                r.append(float(np.sqrt(np.nanmean(d ** 2))))
            rows[suite]["|".join(b)] = r
    return rows


# ---------------------------------------------------------------- validations
def validations(data, info, emus, keep, blocks, idx_by_block, scale, sets, splits, rng, nstarts):
    v = {}
    v["V1"] = {}
    for suite in SUITES:
        ratio = (info[suite]["cv_rmse"] / np.maximum(info[suite]["seed_noise"], FLOOR))[keep]
        v["V1"][suite] = {"fraction_below_1.5": float(np.nanmean(ratio <= 1.5)), "median_ratio": float(np.nanmedian(ratio)), "max_ratio": float(np.nanmax(ratio)), "n_outputs": int(keep.sum())}
    v["V1"]["passed"] = bool(all(v["V1"][s]["fraction_below_1.5"] >= 0.8 for s in SUITES))
    hm = splits.get("fam:hmf")
    sm = summarize_splits(hm) if hm else None
    v["V2"] = {"verdict": sm["verdict"] if sm else None, "summary": sm, "passed": bool(sm and sm["verdict"] == "removable")}
    # V3 and V4 against the star formation logs of camels-sfrd.json
    sf_path = ROOT / "data" / "ensembles" / "camels-sfrd.json"
    cols = data["meta"]["columns"]
    j_rho = {s: [j for j, (f, sn, b) in enumerate(cols) if f == "rho" and sn == "090"] for s in ("090",)}
    v["V3"] = v["V4"] = None
    if sf_path.exists() and j_rho["090"]:
        sd = json.loads(sf_path.read_text())
        v3, v4 = {}, {}
        for suite in SUITES:
            lh = data["suites"][suite]["LH"]
            diffs, ratios = [], []
            for i, n in enumerate(lh["names"]):
                rec = sd["suites"][suite]["LH"].get(n)
                if not rec or rec["sfrd"][0] is None or not np.isfinite(lh["Y"][i, j_rho["090"][1]]):
                    continue
                diffs.append(lh["Y"][i, j_rho["090"][1]] - rec["sfrd"][0])
                if np.isfinite(lh["Y"][i, j_rho["090"][0]]) and rec["formedMassMsun"] > 0:
                    ratios.append(10 ** lh["Y"][i, j_rho["090"][0]] * sd["volumeCMpc3"] / rec["formedMassMsun"])
            v3[suite] = {"median_difference_dex": float(np.median(diffs)) if diffs else None, "n": len(diffs)}
            v4[suite] = {"median_ratio": float(np.median(ratios)) if ratios else None, "n": len(ratios)}
        v["V3"] = {**v3, "passed": bool(all(v3[s]["median_difference_dex"] is not None and abs(v3[s]["median_difference_dex"]) <= 0.2 for s in SUITES))}
        v["V4"] = {**v4, "passed": bool(all(v4[s]["median_ratio"] is not None and 0.45 <= v4[s]["median_ratio"] <= 0.75 for s in SUITES))}
    idx, c = make_set(idx_by_block, sets["all"], scale)
    d4, _ = distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, np.random.default_rng([SEED, 71]), nstarts=nstarts)
    d8, _ = distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, np.random.default_rng([SEED, 72]), nstarts=3 * nstarts)
    v["V5"] = {"D_starts_low": d4, "D_starts_high": d8, "relative_change": float(abs(d4 - d8) / max(d8, 1e-12)), "passed": bool(abs(d4 - d8) / max(d8, 1e-12) < 0.05)}
    return v


# ---------------------------------------------------------------- run
def run(data=None, nsplit=200, nsmall=100, npath=50, nstarts=4, sens=True, workers=4):
    data = data or load_galaxies()
    keep, blocks, detail = eligibility(data)
    cols = data["meta"]["columns"]
    idx_by_block = {b: np.array(v) for b, v in blocks.items()}
    snaps = data["meta"]["snapshots"]
    emus, info = build_emulators(data, keep)
    degrees = {s: info[s]["degree"] for s in SUITES}
    scale = noise_scale(info)
    sets = define_sets(blocks, snaps)
    out = {"meta": {"snapshots": snaps, "z": data["meta"]["z"], "n_outputs_total": len(cols), "n_outputs_eligible": int(keep.sum()), "n_blocks": len(blocks), "degrees": degrees, "margin": MARGIN, "floor": FLOOR, "families": FAMILIES,
                    "blocks": {"|".join(b): {"family": b[0], "snapshot": b[1], "z": data["meta"]["z"][b[1]], "outputs": [int(cols[j][2]) for j in v]} for b, v in idx_by_block.items()}},
           "eligibility": {suite: {"finite_lh_min": float(np.min(detail[suite]["finite_lh"][keep])), "n_outputs_ok": int(detail[suite]["ok"].sum())} for suite in SUITES}}
    out["noise"] = {suite: {"median_seed_noise": float(np.nanmedian(info[suite]["seed_noise"][keep])), "median_emulator_error": float(np.nanmedian(info[suite]["emulator_error"][keep])), "mean_cv_ratio_deg2": info[suite]["mean_cv_ratio_deg2"], "mean_cv_ratio_deg3": info[suite]["mean_cv_ratio_deg3"]} for suite in SUITES}
    # point distances
    rp = np.random.default_rng([SEED, 51])
    pts = {}
    for name, bl in sets.items():
        idx, c = make_set(idx_by_block, bl, scale)
        d, a = distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, rp, nstarts=2 * nstarts)
        pts[name] = {"D": d, "D_fiducial": fiducial_distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c), "n_outputs": int(len(idx)), "n_blocks": len(bl), "a_tng": [float(v) for v in a[:4]], "a_simba": [float(v) for v in a[4:]]}
    out["point"] = pts
    # greedy path
    chosen, steps = greedy_path(emus, scale, idx_by_block, sets, np.random.default_rng([SEED, 52]), nstarts=nstarts)
    out["greedy_path"] = steps
    sets_all = define_sets(blocks, snaps, path=chosen)
    # splits: all (nsplit), families and snapshots (nsmall), drop-one sets and the nested sets of the path (npath)
    counts = {n: (nsplit if n == "all" else npath if n.startswith(("path:", "drop:")) else nsmall) for n in sets_all}
    sp = reach_splits(data, degrees, scale, idx_by_block, sets_all, counts, nstarts, workers=workers)
    out["splits"] = {name: summarize_splits(r) for name, r in sp.items()}
    # J3: the joint distance against the distance of the families tuned separately, D_sep^2 = sum over families of (blocks of the family / all blocks) * D(family)^2; D(all)^2 >= D_sep^2 by construction
    fam_names = [f for f in JOINT_FAMILIES if "fam:" + f in sp]
    wf = {f: pts["fam:" + f]["n_blocks"] / pts["all"]["n_blocks"] for f in fam_names}
    sep_pt = float(sum(wf[f] * pts["fam:" + f]["D"] ** 2 for f in fam_names))
    r_, ex = [], []
    for k in range(min(len(sp["all"]["between"]), nsmall)):
        ds2 = sum(wf[f] * sp["fam:" + f]["between"][k] ** 2 for f in fam_names if len(sp["fam:" + f]["between"]) > k)
        r_.append(sp["all"]["between"][k] ** 2 / max(ds2, 1e-12))
        ex.append(sp["all"]["between"][k] ** 2 - ds2)
    fam_struct = [f for f in fam_names if out["splits"]["fam:" + f]["verdict"] == "structural"]
    ctl95 = out["splits"]["all"]["control"]["p95"]
    kind = None
    if out["splits"]["all"]["verdict"] == "structural":
        kind = "irreducible" if fam_struct else "conflict"
    out["J3"] = {"mechanism": kind, "ratio_interpretable": bool(math.sqrt(sep_pt) > ctl95), "D_separate_point": math.sqrt(sep_pt), "ratio_point": pts["all"]["D"] ** 2 / max(sep_pt, 1e-12), "excess_point": pts["all"]["D"] ** 2 - sep_pt,
                 "ratio_splits": {"p5": A.pct(r_, 5), "p50": A.pct(r_, 50), "p95": A.pct(r_, 95), "n": len(r_)}, "excess_splits": {"p5": A.pct(ex, 5), "p50": A.pct(ex, 50), "p95": A.pct(ex, 95)}}
    # separating set
    sep = None
    for j in range(1, len(chosen) + 1):
        s_ = out["splits"].get(f"path:{j}")
        if s_ and s_["verdict"] == "structural":
            sep = {"size": j, "families": chosen[:j], "D": steps[j - 1]["D"]}
            break
    out["separating_set"] = sep
    out["response"] = response_table(emus, info, scale, list(blocks), idx_by_block)
    out["validations"] = validations(data, info, emus, keep, blocks, idx_by_block, scale, sets, out_splits_for_validation(sp), np.random.default_rng([SEED, 54]), nstarts)
    # shrunken ranges (all)
    idx, c = make_set(idx_by_block, sets["all"], scale)
    out["shrunk"] = {str(lam): distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, np.random.default_rng([SEED, 55, int(lam * 100)]), lam=lam, nstarts=nstarts)[0] for lam in (0.25, 0.5, 0.75, 1.0)}
    if sens:
        out["sensitivity"] = sensitivity(data, keep, blocks, idx_by_block, sets, degrees, nstarts, sp)
    return out


def out_splits_for_validation(sp):
    return {"fam:hmf": sp.get("fam:hmf")}


def sensitivity(data, keep, blocks, idx_by_block, sets, degrees, nstarts, sp):
    """S1 to S9: the point distance of the joint set (and the verdict where the base splits can be reused)."""
    res = {}

    def point(emus, scale, bl, k):
        idx, c = make_set(idx_by_block, bl, scale)
        return distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, np.random.default_rng([SEED, 60, k]), nstarts=2 * nstarts)[0]
    emus0, info0 = build_emulators(data, keep, degrees=degrees)
    scale0 = noise_scale(info0)
    k = 0
    for name, kw in (("S1_degree2", dict(degrees={s: 2 for s in SUITES})), ("S1_degree3", dict(degrees={s: 3 for s in SUITES})), ("S2_kernel0.35", dict(h=0.35)), ("S2_kernel0.8", dict(h=0.8))):
        e, i = build_emulators(data, keep, **{"degrees": degrees, **kw})
        res[name] = {"D": point(e, noise_scale(i), sets["all"], k)}
        k += 1
    res["S3_no_emulator_error"] = {"D": point(emus0, noise_scale(info0, with_emulator_error=False), sets["all"], k)}
    k += 1
    for fl in (0.01, 0.05):
        res[f"S4_floor{fl}"] = {"D": point(emus0, noise_scale(info0, floor=fl), sets["all"], k)}
        k += 1
    base = summarize_splits(sp["all"], margin=2.0) if sp.get("all") else None
    res["S5_margin2"] = {"verdict": base["verdict"] if base else None, "D": base["between"]["p50"] if base else None}
    z01 = [b for b in sets["all"] if b[1] in data["meta"]["snapshots"][:2]]
    res["S6_z0_z0.95_only"] = {"D": point(emus0, scale0, z01, k)}
    k += 1
    res["S7_no_bhocc"] = {"D": point(emus0, scale0, [b for b in sets["all"] if b[0] != "bhocc"], k)}
    k += 1
    cols = data["meta"]["columns"]
    keep8 = keep.copy()
    for j, (f, s, b) in enumerate(cols):
        if f in ("gsmf", "qf", "sfms", "bhms", "bhocc", "mzr", "zstar", "size", "fgas") and b < 2:
            keep8[j] = False
    blocks8 = {b: np.array([j for j in v if keep8[j]]) for b, v in idx_by_block.items()}
    blocks8 = {b: v for b, v in blocks8.items() if len(v) >= 3}
    e8, i8 = build_emulators(data, keep8, degrees=degrees)
    res["S8_no_two_lowest_mass_bins"] = {"D": distance(e8["IllustrisTNG"], e8["SIMBA"], *make_set(blocks8, [b for b in sets["all"] if b in blocks8], noise_scale(i8)), np.random.default_rng([SEED, 60, k]), nstarts=2 * nstarts)[0]}
    k += 1
    return res


# ---------------------------------------------------------------- report
def verdicts(res):
    s = res["splits"]
    fam = {f: s["fam:" + f] for f in JOINT_FAMILIES if s.get("fam:" + f)}
    return {"J1": {"verdict": s["all"]["verdict"], "D_point": res["point"]["all"]["D"], "between": s["all"]["between"], "control_p95": s["all"]["control"]["p95"]},
            "J2": {f: v["verdict"] for f, v in fam.items()}, "J3": res.get("J3"), "J4": res.get("separating_set"), "validations": {k: (v.get("passed") if isinstance(v, dict) else None) for k, v in res["validations"].items()}}


def _f(v, d=2):
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.{d}f}"


def _table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def headline(res):
    v, p, s = res["verdicts"], res["point"], res["splits"]
    out = []
    a = s["all"]
    out.append(f"**J1 - joint.** Retuning four parameters per code, IllustrisTNG and SIMBA stay {_f(a['between']['p50'])} noise units apart on all {p['all']['n_outputs']} outputs ({p['all']['n_blocks']} blocks: {len(res['meta']['families']) - 1} families at up to {len(res['meta']['snapshots'])} redshifts; "
               f"5th to 95th percentile of half-sample emulators {_f(a['between']['p5'])} to {_f(a['between']['p95'])}, same-code controls at most {_f(a['control']['p95'])}; at the fiducial parameters {_f(p['all']['D_fiducial'])}). A distance of 1 is the standard deviation of the difference between one run of each code. By the rule fixed in advance the joint verdict is **{a['verdict']}**.")
    fam = [(f, s["fam:" + f], p["fam:" + f]) for f in JOINT_FAMILIES if s.get("fam:" + f)]
    struct = [FAMILY_NAMES[f] for f, x, _ in fam if x["verdict"] == "structural"]
    rem = [FAMILY_NAMES[f] for f, x, _ in fam if x["verdict"] == "removable"]
    out.append(f"**J2 - each alone.** Fitted alone, {len(struct)} of {len(fam)} families are structural" + (": " + ", ".join(struct) if struct else "") + f"; {len(rem)} are removable" + (": " + ", ".join(rem) if rem else "") + ".")
    j3 = res.get("J3")
    if j3:
        out.append(f"**J3 - the cost of agreeing.** With one parameter pair for everything the squared distance is {_f(j3['ratio_point'])} times what it would be if every family were tuned separately (distance {_f(p['all']['D'])} against {_f(j3['D_separate_point'])}; half-sample median ratio {_f(j3['ratio_splits']['p50'])}); a ratio of 1 means no retuning conflict." + (f" The structural joint distance is classed **{j3['mechanism']}**." if j3.get('mechanism') else ""))
    sep = res.get("separating_set")
    if sep:
        out.append(f"**J4 - what separates them.** In forward selection the families come in the order {', '.join(x['family'] for x in res['greedy_path'])}; the first set whose distance is structural is the first {sep['size']} ({', '.join(sep['families'])}, D = {_f(sep['D'])}).")
    else:
        out.append(f"**J4 - what separates them.** In forward selection the families come in the order {', '.join(x['family'] + ' (' + _f(x['D']) + ')' for x in res['greedy_path'])}; no prefix of that order was structural by the rule.")
    val = res["validations"]
    bad = [k for k, x in val.items() if isinstance(x, dict) and x.get("passed") is False]
    out.append("**Validations.** " + ("All five hold." if not bad else f"Not all hold: {', '.join(bad)}; see section 2 and read the corresponding conclusions with that qualification."))
    return out


def deviations(res):
    d = []
    for k, x in res["validations"].items():
        if x is None:
            d.append(f"Validation {k} could not be evaluated.")
    if res["meta"]["n_blocks"] < 10:
        d.append(f"Only {res['meta']['n_blocks']} blocks were eligible.")
    return d


def render(res):
    v, p, s = res["verdicts"], res["point"], res["splits"]
    L = ["# Analysis: can retuning make two feedback models agree on every galaxy observable at once?", "",
         f"Generated by `scripts/analyze_joint_reachability.py` from release {res['version']}; do not edit by hand. The pre-specified protocol is [`PROTOCOL-joint-reachability.md`](PROTOCOL-joint-reachability.md); this page reports what it gave, null results included. Seed {res['parameters']['seed']}.", "", "## Result", ""]
    L += [f"- {x}" for x in headline(res)]
    L += ["", "Distances are in units of the noise scale of each output (the standard deviation of the difference between one run of each code plus the emulators' error); the margin is 1. Everything is for CAMELS resolution (25 Mpc/h, 256^3).", "", "## 1. Data and eligibility", "",
          f"{res['meta']['n_outputs_eligible']} of {res['meta']['n_outputs_total']} outputs are eligible (finite in at least {int(100 * MIN_FINITE_LH)} % of the LH simulations of both codes and in at least {MIN_CV} of the 27 CV simulations of both), in {res['meta']['n_blocks']} blocks. Emulator degrees: IllustrisTNG {res['meta']['degrees']['IllustrisTNG']}, SIMBA {res['meta']['degrees']['SIMBA']}. Median seed noise of the eligible outputs {_f(res['noise']['IllustrisTNG']['median_seed_noise'], 3)} (IllustrisTNG) and {_f(res['noise']['SIMBA']['median_seed_noise'], 3)} (SIMBA); median emulator error {_f(res['noise']['IllustrisTNG']['median_emulator_error'], 3)} and {_f(res['noise']['SIMBA']['median_emulator_error'], 3)}.", ""]
    blocks = res["meta"]["blocks"]
    snaps = res["meta"]["snapshots"]
    rows = []
    for f in FAMILIES:
        r = [f"{f} ({FAMILY_NAMES[f]})"]
        for sn in snaps:
            b = blocks.get(f + "|" + sn)
            r.append(str(len(b["outputs"])) if b else "-")
        rows.append(r)
    L += [_table(["family"] + [f"z = {res['meta']['z'][sn]}" for sn in snaps], rows), "", "Eligible outputs per block (a dash is a block with too few galaxies or too many missing values).", "", "## 2. Validations", ""]
    val = res["validations"]
    L += [_table(["validation", "result", "required", "holds"], [
        ["V1 emulator cross-validation error / seed noise, share of outputs at most 1.5", f"{_f(val['V1']['IllustrisTNG']['fraction_below_1.5'], 2)} (IllustrisTNG), {_f(val['V1']['SIMBA']['fraction_below_1.5'], 2)} (SIMBA); median ratio {_f(val['V1']['IllustrisTNG']['median_ratio'])} and {_f(val['V1']['SIMBA']['median_ratio'])}", ">= 0.8 each", "yes" if val["V1"]["passed"] else "no"],
        ["V2 negative control: halo mass function joint verdict", str(val["V2"]["verdict"]) + (f" (between {_f(val['V2']['summary']['between']['p50'])}, controls {_f(val['V2']['summary']['control']['p95'])})" if val["V2"]["summary"] else ""), "removable", "yes" if val["V2"]["passed"] else "no"],
        ["V3 catalogue SFR density at z = 0 minus the star formation log's SFR density (median, dex)", "not evaluated" if not val["V3"] else f"{_f(val['V3']['IllustrisTNG']['median_difference_dex'], 3)} (IllustrisTNG), {_f(val['V3']['SIMBA']['median_difference_dex'], 3)} (SIMBA)", "|.| <= 0.2", "n/a" if not val["V3"] else ("yes" if val["V3"]["passed"] else "no")],
        ["V4 stellar mass in subhaloes over the mass formed (median)", "not evaluated" if not val["V4"] else f"{_f(val['V4']['IllustrisTNG']['median_ratio'], 3)} (IllustrisTNG), {_f(val['V4']['SIMBA']['median_ratio'], 3)} (SIMBA)", "0.45 to 0.75", "n/a" if not val["V4"] else ("yes" if val["V4"]["passed"] else "no")],
        ["V5 distance with 4 and 12 random starts", f"{_f(val['V5']['D_starts_low'], 3)} and {_f(val['V5']['D_starts_high'], 3)} ({_f(100 * val['V5']['relative_change'], 1)} %)", "< 5 %", "yes" if val["V5"]["passed"] else "no"]]), "",
          "## 3. J1: all observables at once", "",
          _table(["set", "outputs", "D at the fiducial parameters", "D after retuning, all simulations", "between codes, 500-simulation emulators: 5th / median / 95th", "same-code control: median / 95th", "verdict"],
                 [[n, p[n]["n_outputs"], _f(p[n]["D_fiducial"]), _f(p[n]["D"]), "{} / {} / {}".format(*[_f(s[n]["between"][q]) for q in ("p5", "p50", "p95")]), "{} / {}".format(_f(s[n]["control"]["median"]), _f(s[n]["control"]["p95"])), s[n]["verdict"]] for n in ["all"] + [k for k in s if k.startswith("z:")]]), "",
          f"Reachable coordinates of the minimising pair for all outputs (half-range units): IllustrisTNG {', '.join(f'{x:+.2f}' for x in p['all']['a_tng'])}; SIMBA {', '.join(f'{x:+.2f}' for x in p['all']['a_simba'])}. With the search range cut to 25, 50, 75 and 100 % of the half-width the distance is {', '.join(_f(x) for x in res['shrunk'].values())}.", "",
          "## 4. J2: each family alone", "",
          _table(["family", "blocks", "D at the fiducial", "D after retuning", "between: 5th / median / 95th", "control p95", "verdict"], [[f"{f} ({FAMILY_NAMES[f]})", p["fam:" + f]["n_blocks"], _f(p["fam:" + f]["D_fiducial"]), _f(p["fam:" + f]["D"]), "{} / {} / {}".format(*[_f(s["fam:" + f]["between"][q]) for q in ("p5", "p50", "p95")]), _f(s["fam:" + f]["control"]["p95"]), s["fam:" + f]["verdict"]] for f in FAMILIES if s.get("fam:" + f)]), "",
          "## 5. J3 and J4: the cost of agreeing and what separates the codes", ""]
    j3 = res.get("J3")
    if j3:
        L += [f"Squared joint distance over the squared distance with every family tuned separately (weights = share of blocks): {_f(j3['ratio_point'])} (half-sample 5th / median / 95th {_f(j3['ratio_splits']['p5'])} / {_f(j3['ratio_splits']['p50'])} / {_f(j3['ratio_splits']['p95'])}); excess of the squared joint distance: {_f(j3['excess_point'])} (half-sample {_f(j3['excess_splits']['p5'])} / {_f(j3['excess_splits']['p50'])} / {_f(j3['excess_splits']['p95'])}). A ratio of 1 means that one parameter pair serves every family as well as separate pairs would.", ""]
    L += ["Forward selection (families added one at a time, each the one that raises the joint distance most; the order is chosen on all simulations, so the verdicts of the nested sets are descriptive):", "",
          _table(["step", "added family", "D of the set (point)", "between: 5th / median / 95th (50 splits)", "control p95", "verdict"], [[j + 1, st["family"], _f(st["D"]), "{} / {} / {}".format(*[_f(s[f"path:{j + 1}"]["between"][q]) for q in ("p5", "p50", "p95")]), _f(s[f"path:{j + 1}"]["control"]["p95"]), s[f"path:{j + 1}"]["verdict"]] for j, st in enumerate(res["greedy_path"]) if s.get(f"path:{j + 1}")]), "",
          "Joint distance without each family (point estimate; verdict from 50 splits):", "",
          _table(["family left out", "D without it", "between median", "verdict"], [[f, _f(p["drop:" + f]["D"]), _f(s["drop:" + f]["between"]["p50"]), s["drop:" + f]["verdict"]] for f in JOINT_FAMILIES if s.get("drop:" + f)]), "",
          "## 6. J5: redshift", "", _table(["snapshot", "z", "outputs", "D", "verdict"], [[k[2:], res["meta"]["z"][k[2:]], p[k]["n_outputs"], _f(p[k]["D"]), s[k]["verdict"]] for k in s if k.startswith("z:")]), "",
          "## 7. Sensitivity (S1 to S9, point distance of all outputs)", "", _table(["analysis", "D", "verdict"], [[k, _f(x.get("D")), x.get("verdict", "-")] for k, x in res.get("sensitivity", {}).items()]), "",
          "## 8. Deviations from the protocol", ""] + ([f"- {d}" for d in res["deviations"]] or ["- none"]) + ["",
          "## 9. Limitations", "",
          "- Two codes; CAMELS resolution; the reachable set depends on the CAMELS parameter ranges, not the ranges the code authors would accept, and the search reaches the corners of the design where the emulators are least constrained (the controls share that search).",
          "- The distance depends on the choice of outputs and their weights (equal weight per block); the margin of 1 is the scatter between two seeds, a unit and not a physical tolerance.",
          "- Medians of small bins are noisy; the noise scale does not include their non-Gaussian part. The order of the forward selection is chosen on all simulations, so the verdicts of nested sets are descriptive.",
          "- Subfind subhaloes are not galaxies seen on the sky: no aperture, selection or survey effect is modelled.", "",
          "## 10. Reproduce", "", "`python3 scripts/ingest_camels_galaxies.py` (about 35 minutes, needs fsspec and aiohttp) rebuilds `data/ensembles/camels-galaxies.json`; `python3 scripts/analyze_joint_reachability.py` rewrites this file and `data/analysis/joint-reachability.json`; "
          "`python3 scripts/test_joint_reachability.py` checks the machinery on synthetic worlds and that these outputs are not stale.", ""]
    return "\n".join(L)


def assemble(nsplit=200, nsmall=100, npath=50, nstarts=4, data=None, sens=True, workers=4):
    res = run(data=data, nsplit=nsplit, nsmall=nsmall, npath=npath, nstarts=nstarts, sens=sens, workers=workers)
    res["version"] = json.loads((ROOT / "data" / "release.json").read_text())["version"]
    res["protocol"] = "docs/PROTOCOL-joint-reachability.md"
    res["parameters"] = {"seed": SEED, "nsplit": nsplit, "nsmall": nsmall, "npath": npath, "nstarts": nstarts, "margin": MARGIN, "floor": FLOOR, "kernel": A.KERNEL_H, "ridge": A.RIDGE}
    res["verdicts"] = verdicts(res)
    res["deviations"] = deviations(res)
    res["headline"] = headline(res)
    return res


def write_outputs(res):
    (ROOT / "data" / "analysis" / "joint-reachability.json").write_text(json.dumps(res, indent=1, default=lambda o: float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)) + "\n")
    (ROOT / "docs" / "ANALYSIS-joint-reachability.md").write_text(render(res))


def main():
    res = assemble()
    write_outputs(res)
    v = res["verdicts"]
    print(f"joint reachability: J1 {v['J1']['verdict']} (D={v['J1']['D_point']:.2f}); structural alone: {[f for f, x in v['J2'].items() if x == 'structural']}")


if __name__ == "__main__":
    main()
