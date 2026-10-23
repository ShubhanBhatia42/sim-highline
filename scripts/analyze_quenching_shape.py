"""Does the shape of the star-formation distribution separate IllustrisTNG and SIMBA? The fifth study.

Implements docs/PROTOCOL-quenching-shape.md section by section; every departure is reported as a deviation in the generated docs/ANALYSIS-quenching-shape.md. Reuses the estimators of scripts/analyze_joint_reachability.py (module J) unchanged:
emulators, noise scale, distance, matched-size splits, verdict rule, emulator-variance correction. Reads data/ensembles/camels-galaxies.json (the joint set of the earlier study) and data/ensembles/camels-distshape.json (written by
scripts/ingest_camels_distshape.py). Writes data/analysis/quenching-shape.json and docs/ANALYSIS-quenching-shape.md. Nothing here changes a stored record."""
import json
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_joint_reachability as J
import analyze_model_form as A

warnings.filterwarnings("ignore", category=RuntimeWarning, message="(Mean of empty slice|All-NaN slice|Degrees of freedom|invalid value)")
ROOT = Path(__file__).resolve().parent.parent
SEED = 20261023
SHAPE = ["gv", "sfw"]
WIDE = "gvwide"
NAMES = {"gv": "green-valley fraction", "sfw": "width of the star-forming sequence", "gvwide": "green-valley fraction, window from -11.5"}
MSTAR_BINNED = ("gsmf", "qf", "sfms", "bhms", "bhocc", "mzr", "zstar", "size", "fgas") + tuple(SHAPE) + (WIDE,)
NSPLIT = 100
ADD_MIN = 0.1       # protocol section 4: the 95th percentile of the paired difference below this means "adds nothing detectable"
V3_MIN_GAL = 30
V3_MAX_SHARE = 0.25
RANK = {"removable": 0, "unresolved": 1, "structural": 2}
SENS = {"S2:gv": "gv alone", "S2:sfw": "sfw alone", "S3:wide": "lower threshold -11.5 (gvwide) with sfw", "S1:shape": "shape without the two lowest mass bins", "S1:sf2": "sf2 without the two lowest mass bins",
        "S1:sf2+shape": "sf2+shape without the two lowest mass bins", "S1:joint": "joint without the two lowest mass bins", "S1:joint+shape": "joint+shape without the two lowest mass bins"}


# ---------------------------------------------------------------- data
def load(path_shape=None, path_s4=None):
    """The merged dataset in the structure of J.load_galaxies: the columns of the earlier study followed by those of the shape ingest. The bin counts of the shape ingest (not outputs) are kept separately for validation V3."""
    base = J.load_galaxies(path_s4)
    sh = json.loads(Path(path_shape or ROOT / "data" / "ensembles" / "camels-distshape.json").read_text())
    snaps = list(sh["snapshots"])
    cols_new = [(f, s, b) for s in snaps for f in sh["families"] for b in range(sh["familyBins"][f])]
    out = {"meta": {**base["meta"], "columns": base["meta"]["columns"] + cols_new, "families": base["meta"]["families"] + sh["families"], "shape_snapshots": snaps}, "suites": {}, "counts": {}}
    for suite in J.SUITES:
        out["suites"][suite], out["counts"][suite] = {}, {}
        for sset in ("LH", "CV"):
            b = base["suites"][suite][sset]
            sims = sh["suites"][suite][sset]
            if set(sims) != set(b["names"]):
                raise SystemExit(f"{suite} {sset}: the simulations of the two ensembles differ")
            Y2 = np.full((len(b["names"]), len(cols_new)), np.nan)
            cnt = {(c, s): np.full((len(b["names"]), 10), np.nan) for c in sh["counts"] for s in snaps}
            for i, n in enumerate(b["names"]):
                if not np.allclose(A.to_x(sims[n]["params"]), b["X"][i]):
                    raise SystemExit(f"{suite} {n}: parameters differ between the two ensembles")
                for s in snaps:
                    sn = sims[n]["snaps"].get(s)
                    if not (sn and "values" in sn):
                        continue
                    for c in sh["counts"]:
                        cnt[(c, s)][i] = sn["values"][c]
                    for j, (f, s2, bb) in enumerate(cols_new):
                        if s2 == s and sn["values"][f][bb] is not None:
                            Y2[i, j] = sn["values"][f][bb]
            out["suites"][suite][sset] = {"X": b["X"], "Y": np.hstack([b["Y"], Y2]), "names": b["names"]}
            if sset == "CV":
                out["counts"][suite] = cnt
    return out


def block_order(blocks, snaps):
    fam = J.FAMILIES + SHAPE + [WIDE]
    return sorted(blocks, key=lambda b: (fam.index(b[0]), snaps.index(b[1])))


# ---------------------------------------------------------------- the paired comparison of protocol section 4
def paired(sp, big, base, summ):
    """Protocol section 4 with amendment A1. In split k the raw between-code distances of set `big` and of set `base` differ by delta_k (both sets have the same number of splits, and split k of both uses the same halves); the two same-code
    controls of the same split differ by c_k (their mean). Adding outputs raises the raw distance a little even when the codes are identical, so the quantity judged is the excess e_k = delta_k - c_k.
    Rule: `adds separation` if the 5th percentile of e exceeds 0 and the verdict of `big` is at least as strong as that of `base`; `adds nothing detectable` if the 95th percentile of e is below ADD_MIN; otherwise `unresolved`.
    The unadjusted differences (between and each control) are reported beside it."""
    a, b = sp[big], sp[base]
    if len(a["between_raw"]) != len(b["between_raw"]):
        raise ValueError("the paired sets must have the same number of splits")
    d = np.array(a["between_raw"]) - np.array(b["between_raw"])
    ctl = {suite: np.array(a["control_raw_" + suite]) - np.array(b["control_raw_" + suite]) for suite in J.SUITES}
    e = d - 0.5 * (ctl["IllustrisTNG"] + ctl["SIMBA"])
    q = lambda v: {"p5": A.pct(v, 5), "p50": A.pct(v, 50), "p95": A.pct(v, 95)}
    stronger = RANK[summ[big]["verdict"]] >= RANK[summ[base]["verdict"]]
    if A.pct(e, 5) > 0 and stronger:
        verdict = "adds separation"
    elif A.pct(e, 95) < ADD_MIN:
        verdict = "adds nothing detectable"
    else:
        verdict = "unresolved"
    return {"big": big, "base": base, "n": int(d.size), "excess": q(e), "between": q(d), "control": {s: q(ctl[s]) for s in J.SUITES}, "verdict_big": summ[big]["verdict"], "verdict_base": summ[base]["verdict"], "verdict": verdict,
            "both_conditions": bool(A.pct(e, 5) > 0 and A.pct(e, 95) < ADD_MIN)}


# ---------------------------------------------------------------- run
def run(data, nsplit=NSPLIT, nstarts=4, workers=4, sens=True):
    cols = data["meta"]["columns"]
    snaps = data["meta"]["snapshots"]
    keep, blocks, detail = J.eligibility(data)
    keep_primary = keep & np.array([c[0] != WIDE for c in cols])  # the degree is chosen on the outputs of the study, not on those of a sensitivity analysis
    idx_by_block = {b: np.array(v) for b, v in blocks.items()}
    ordered = block_order(blocks, snaps)
    S = lambda fams: [b for b in ordered if b[0] in fams]
    emus, info = J.build_emulators(data, keep_primary)
    degrees = {s: info[s]["degree"] for s in J.SUITES}
    scale = J.noise_scale(info)
    shape_b, sf2_b, joint_b, hmf_b = S(SHAPE), S(("qf", "sfms")), S(J.JOINT_FAMILIES), S(("hmf",))
    sets = {"shape": shape_b, "sf2": sf2_b, "sf2+shape": sf2_b + shape_b, "joint": joint_b, "joint+shape": joint_b + shape_b, "hmf": hmf_b}
    sens_sets = {}
    if sens:
        sens_sets = {"S2:gv": S(("gv",)), "S2:sfw": S(("sfw",)), "S3:wide": S((WIDE, "sfw"))}
        reduced = {}
        for b, v in idx_by_block.items():
            if b[0] in MSTAR_BINNED:
                w = np.array([j for j in v if cols[j][2] >= 2])
                if len(w) >= min(2, len(v)):
                    reduced[(b[0] + "@s1", b[1])] = w
        idx_all = {**idx_by_block, **reduced}
        to_s1 = lambda bl: [(b[0] + "@s1", b[1]) if (b[0] + "@s1", b[1]) in reduced else b for b in bl if b[0] not in MSTAR_BINNED or (b[0] + "@s1", b[1]) in reduced]
        for name in ("shape", "sf2", "sf2+shape", "joint", "joint+shape"):
            sens_sets["S1:" + name] = to_s1(sets[name])
    else:
        idx_all = idx_by_block
    all_sets = {**sets, **sens_sets}
    all_sets = {k: v for k, v in all_sets.items() if v}
    out = {"meta": {"snapshots": snaps, "z": data["meta"]["z"], "n_outputs_total": len(cols), "n_outputs_eligible": int(keep.sum()), "n_blocks": len(blocks), "degrees": degrees, "margin": J.MARGIN, "floor": J.FLOOR,
                    "blocks": {"|".join(b): {"family": b[0], "snapshot": b[1], "z": data["meta"]["z"][b[1]], "outputs": [int(cols[j][2]) for j in v]} for b, v in idx_by_block.items()},
                    "sets": {k: ["|".join(b) for b in v] for k, v in all_sets.items()}}}
    out["noise"] = {suite: {"median_seed_noise": float(np.nanmedian(info[suite]["seed_noise"][keep_primary])), "median_emulator_error": float(np.nanmedian(info[suite]["emulator_error"][keep_primary])),
                            "mean_cv_ratio_deg2": info[suite]["mean_cv_ratio_deg2"], "mean_cv_ratio_deg3": info[suite]["mean_cv_ratio_deg3"]} for suite in J.SUITES}
    # point distances on all simulations (2 x nstarts random starts)
    rp = np.random.default_rng([SEED, 51])
    pts, point_min = {}, {}
    for name, bl in all_sets.items():
        idx, c = J.make_set(idx_all, bl, scale)
        d, a = J.distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, rp, nstarts=2 * nstarts)
        pts[name] = {"D": d, "D_fiducial": J.fiducial_distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c), "n_outputs": int(len(idx)), "n_blocks": len(bl), "a_tng": [float(v) for v in a[:4]], "a_simba": [float(v) for v in a[4:]]}
        point_min[name] = (a[:4].copy(), a[4:].copy())
    out["point"] = pts
    counts = {name: nsplit for name in all_sets}   # equal counts: split k of every set uses the same halves, which is what the paired comparison needs
    sp = J.reach_splits(data, degrees, scale, idx_all, all_sets, counts, nstarts, workers=workers, point_min=point_min)
    summ = {name: J.summarize_splits(r) for name, r in sp.items()}
    out["splits"] = summ
    for name in pts:
        pv = sp.get(name, {}).get("point_var") or []
        if pv:
            vt, vs = float(np.median([x[0] for x in pv])), float(np.median([x[1] for x in pv]))
            pts[name]["emulator_variance_full"] = (vt + vs) / 2.0
            pts[name]["D_corrected"] = J.corrected(pts[name]["D"], pts[name]["emulator_variance_full"])
    out["paired"] = {"Q2": paired(sp, "sf2+shape", "sf2", summ), "Q3": paired(sp, "joint+shape", "joint", summ)}
    if sens:
        out["paired_sensitivity"] = {"S1:Q2": paired(sp, "S1:sf2+shape", "S1:sf2", summ) if "S1:sf2+shape" in sp and "S1:sf2" in sp else None,
                                     "S1:Q3": paired(sp, "S1:joint+shape", "S1:joint", summ) if "S1:joint+shape" in sp and "S1:joint" in sp else None}
    out["verdicts"] = {"Q1": summ["shape"]["verdict"], "Q2": out["paired"]["Q2"]["verdict"], "Q3": out["paired"]["Q3"]["verdict"]}
    out["decomposition"] = {name: J.decomposition(emus, idx_all, scale, all_sets[name], *point_min[name]) for name in ("shape", "sf2+shape", "joint+shape")}
    out["response"] = J.response_table(emus, info, scale, shape_b, idx_all)
    out["cv_means"] = cv_means(data, shape_b, idx_by_block, cols)
    out["validations"] = validations(data, info, keep_primary, idx_all, scale, all_sets, shape_b, summ, emus, nstarts, cols)
    return out


def cv_means(data, shape_b, idx_by_block, cols):
    """Mean and standard deviation over the 27 fiducial-parameter simulations of every shape output (descriptive: the numbers the emulators are built around)."""
    res = {}
    for suite in J.SUITES:
        Y = data["suites"][suite]["CV"]["Y"]
        res[suite] = {"|".join(b): {"bins": [int(cols[j][2]) for j in idx_by_block[b]], "mean": [float(np.nanmean(Y[:, j])) for j in idx_by_block[b]], "sd": [float(np.nanstd(Y[:, j], ddof=1)) for j in idx_by_block[b]]} for b in shape_b}
    return res


def validations(data, info, keep, idx_all, scale, sets, shape_b, summ, emus, nstarts, cols):
    v = {}
    shape_cols = np.zeros(len(cols), bool)
    for b in shape_b:
        shape_cols[idx_all[b]] = True
    v["V1"] = {}
    for suite in J.SUITES:
        ratio = (info[suite]["cv_rmse"] / np.maximum(info[suite]["seed_noise"], J.FLOOR))[shape_cols]
        v["V1"][suite] = {"fraction_below_1.5": float(np.nanmean(ratio <= 1.5)), "median_ratio": float(np.nanmedian(ratio)), "max_ratio": float(np.nanmax(ratio)), "n_outputs": int(shape_cols.sum())}
    v["V1"]["passed"] = bool(all(v["V1"][s]["fraction_below_1.5"] >= 0.8 for s in J.SUITES))
    hm = summ.get("hmf")
    v["V2"] = {"verdict": hm["verdict"] if hm else None, "summary": hm, "passed": bool(hm and hm["verdict"] == "removable")}
    low, tot = 0, 0
    per_code = {s: [0, 0] for s in J.SUITES}
    detail = []
    for b in shape_b:
        fam, snap = b
        for j in idx_all[b]:
            bin_ = cols[j][2]
            cname = "ngal" if fam == "gv" else "nsf"
            ns = {s: float(np.nanmedian(data["counts"][s][(cname, snap)][:, bin_])) for s in J.SUITES}
            is_low = any(n < V3_MIN_GAL for n in ns.values())
            low += is_low
            tot += 1
            for s in J.SUITES:
                per_code[s][0] += ns[s] < V3_MIN_GAL
                per_code[s][1] += 1
            detail.append({"block": "|".join(b), "bin": int(bin_), "median_count": ns, "low": bool(is_low)})
    v["V3"] = {"share_below_30": low / tot if tot else None, "per_code": {s: per_code[s][0] / per_code[s][1] for s in J.SUITES}, "n_outputs": tot, "passed": bool(tot and low / tot <= V3_MAX_SHARE), "detail": detail}
    idx, c = J.make_set(idx_all, sets["shape"], scale)
    d4, _ = J.distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, np.random.default_rng([SEED, 71]), nstarts=4)
    d8, _ = J.distance(emus["IllustrisTNG"], emus["SIMBA"], idx, c, np.random.default_rng([SEED, 72]), nstarts=8)
    v["V4"] = {"D_starts_4": d4, "D_starts_8": d8, "relative_change": float(abs(d4 - d8) / max(d8, 1e-12)), "passed": bool(abs(d4 - d8) / max(d8, 1e-12) < 0.05)}
    return v


# ---------------------------------------------------------------- report
def _f(v, d=2):
    return J._f(v, d)


def answer_q1(res):
    s, p = res["splits"]["shape"], res["point"]["shape"]
    word = {"structural": "**structural**: no retuning within the CAMELS ranges brings the two codes together on these outputs",
            "removable": "**removable**: retuning within the CAMELS ranges brings the two codes within one noise unit on these outputs",
            "unresolved": "**unresolved**: the distance is neither clearly above the noise nor clearly below the margin"}[s["verdict"]]
    return (f"**Q1 - shape alone.** The green-valley fraction and the width of the star-forming sequence (blocks: {p['n_blocks']}, outputs: {p['n_outputs']}) are {word}. Half-sample between-code distance, emulator error removed: median {_f(s['between']['p50'])} noise units "
            f"(5th to 95th percentile {_f(s['between']['p5'])} to {_f(s['between']['p95'])}); same-code controls at most {_f(s['control']['p95'])}; margin {_f(J.MARGIN, 0)}. On all simulations: {_f(p.get('D_corrected'))} corrected, {_f(p['D'])} uncorrected, {_f(p['D_fiducial'])} at the fiducial parameters.")


def answer_paired(res, key, label, base_name, big_name):
    q = res["paired"][key]
    d, c, x = q["between"], q["control"], q["excess"]
    word = {"adds separation": "**adds separation**: the two codes are further apart when the shape outputs are included, by more than the same-code controls rise and more than the split-to-split spread",
            "adds nothing detectable": f"**adds nothing detectable**: the rise beyond what the same-code controls show is below {_f(ADD_MIN, 1)} noise units even at its largest",
            "unresolved": "is **unresolved**: the change is neither clearly positive nor clearly negligible"}[q["verdict"]]
    both = " (both conditions of the rule hold; the first listed, adds separation, is reported)" if q.get("both_conditions") else ""
    return (f"**{label}.** Adding the shape outputs to {base_name} {word}{both}. {base_name} alone is {q['verdict_base']}; with the shape outputs it is {q['verdict_big']}. Excess of the change of the raw between-code distance over the mean change of the two same-code controls, split by split: median {_f(x['p50'], 3)}, "
            f"5th to 95th percentile {_f(x['p5'], 3)} to {_f(x['p95'], 3)} noise units (n = {q['n']} splits). The unadjusted change of the between-code distance: median {_f(d['p50'], 3)} ({_f(d['p5'], 3)} to {_f(d['p95'], 3)}); of the controls: IllustrisTNG {_f(c['IllustrisTNG']['p50'], 3)} ({_f(c['IllustrisTNG']['p5'], 3)} to {_f(c['IllustrisTNG']['p95'], 3)}), "
            f"SIMBA {_f(c['SIMBA']['p50'], 3)} ({_f(c['SIMBA']['p5'], 3)} to {_f(c['SIMBA']['p95'], 3)}).")


def headline(res):
    out = [answer_q1(res), answer_paired(res, "Q2", "Q2 - shape beyond the usual two", "the quenched fraction and the star-forming main sequence", "sf2+shape"),
           answer_paired(res, "Q3", "Q3 - shape in the joint set", "the joint set of the earlier study", "joint+shape")]
    val = res["validations"]
    bad = [k for k, x in val.items() if isinstance(x, dict) and x.get("passed") is False]
    out.append("**Validations.** " + ("All four hold." if not bad else f"Not all hold: {', '.join(bad)}; read the conclusions above with the qualification stated in section 2."))
    return out


def deviations(res, s4=None):
    d = []
    deg = res["meta"]["degrees"]
    d.append(f"Emulator degrees were chosen on all eligible outputs of the earlier study together with the eligible shape outputs (protocol section 4 says \"degree chosen by cross-validation\" without naming the outputs): IllustrisTNG {deg['IllustrisTNG']}, SIMBA {deg['SIMBA']}"
             + (f"; the earlier study chose {s4['degrees']['IllustrisTNG']} and {s4['degrees']['SIMBA']}." if s4 else "."))
    d.append("Sensitivity S3 (lower threshold) was computed from the same arrays during the same ingest (family `gvwide`), not by a second ingest, and not used to choose anything.")
    d.append("Sensitivity S1 removes the two lowest mass bins from every mass-binned family in the sets it is applied to (the same rule as the earlier study's S8), not only from the shape families.")
    d.append(f"{res['parameters']['nsplit']} random splits per set, as the protocol states; the earlier study used 200 for its joint set. The split streams are the earlier study's (same seed, as the estimators are reused unchanged).")
    d.append("Two simulations per code and set (LH_0 and CV_0, the first snapshot) were printed when the ingest was tested; no distance, emulator or verdict was computed before this run.")
    for k, x in res["validations"].items():
        if x is None:
            d.append(f"Validation {k} could not be evaluated.")
    if s4 and res.get("consistency"):
        c = res["consistency"]
        if not c["same_blocks"]:
            d.append("The joint set of this run does not have the same blocks as the earlier study's: " + c["note"])
    return d


def render(res):
    p, s, val = res["point"], res["splits"], res["validations"]
    L = ["# Analysis: does the shape of the star-formation distribution separate IllustrisTNG and SIMBA?", "",
         f"Generated by `scripts/analyze_quenching_shape.py` from release {res['version']}; do not edit by hand. The pre-specified protocol is [`PROTOCOL-quenching-shape.md`](PROTOCOL-quenching-shape.md) (committed before the data were ingested); this page reports what it gave, null results included. Seed {res['parameters']['seed']}. Internal: no outside expert has reviewed this study.", "",
         "## Result", ""]
    L += [f"- {x}" for x in headline(res)]
    L += ["", "Distances are in units of the noise scale of each output (the standard deviation of the difference between one run of each code plus the emulators' error); the margin is 1. Everything is for CAMELS resolution (25 Mpc/h, 256^3), instantaneous star formation rates of Subfind subhaloes, and the four astrophysical parameters per code that CAMELS varies.", "",
          "## 1. Data and eligibility", ""]
    blocks = res["meta"]["blocks"]
    snaps = [x for x in res["meta"]["snapshots"] if any(b["snapshot"] == x and b["family"] in SHAPE for b in blocks.values())]
    rows = []
    for f in SHAPE + [WIDE]:
        r = [f"{f} ({NAMES[f]})"]
        for sn in snaps:
            b = blocks.get(f + "|" + sn)
            r.append(str(len(b["outputs"])) if b else "-")
        rows.append(r)
    L += [f"{res['meta']['n_outputs_eligible']} of {res['meta']['n_outputs_total']} outputs (the earlier study's and the shape ones together) are eligible, in {res['meta']['n_blocks']} blocks. Emulator degrees: IllustrisTNG {res['meta']['degrees']['IllustrisTNG']}, SIMBA {res['meta']['degrees']['SIMBA']}. "
          f"Median seed noise of the eligible outputs {_f(res['noise']['IllustrisTNG']['median_seed_noise'], 3)} (IllustrisTNG) and {_f(res['noise']['SIMBA']['median_seed_noise'], 3)} (SIMBA); median emulator error {_f(res['noise']['IllustrisTNG']['median_emulator_error'], 3)} and {_f(res['noise']['SIMBA']['median_emulator_error'], 3)}.", "",
          J._table(["family"] + [f"z = {res['meta']['z'][sn]}" for sn in snaps], rows), "", "Eligible outputs per block (a dash is a block with too few galaxies or too many missing values). `gvwide` is the sensitivity S3 variant.", ""]
    if res.get("consistency"):
        c = res["consistency"]
        L += [f"The joint set of this run has {c['n_blocks_here']} blocks; the earlier study's has {c['n_blocks_s4']}" + (" (the same blocks)." if c["same_blocks"] else " (not the same: see the deviations).") + f" Its verdict here is **{c['verdict_here']}** (earlier study: {c['verdict_s4']}).", ""]
    v3 = val["V3"]
    L += ["## 2. Validations", "",
          J._table(["validation", "result", "required", "holds"], [
              ["V1 emulator cross-validation error / seed noise of the shape outputs, share at most 1.5", f"{_f(val['V1']['IllustrisTNG']['fraction_below_1.5'])} (IllustrisTNG), {_f(val['V1']['SIMBA']['fraction_below_1.5'])} (SIMBA); median ratio {_f(val['V1']['IllustrisTNG']['median_ratio'])} and {_f(val['V1']['SIMBA']['median_ratio'])}", ">= 0.8 each", "yes" if val["V1"]["passed"] else "no"],
              ["V2 negative control: halo mass function", str(val["V2"]["verdict"]) + (f" (between {_f(val['V2']['summary']['between']['p50'])}, controls {_f(val['V2']['summary']['control']['p95'])})" if val["V2"]["summary"] else ""), "removable", "yes" if val["V2"]["passed"] else "no"],
              ["V3 share of shape outputs resting on fewer than 30 galaxies per bin in the median fiducial simulation (either code)", f"{_f(100 * v3['share_below_30'], 0)} % ({_f(100 * v3['per_code']['IllustrisTNG'], 0)} % IllustrisTNG, {_f(100 * v3['per_code']['SIMBA'], 0)} % SIMBA)", "<= 25 %", "yes" if v3["passed"] else "no (the shape verdict is resolution-limited)"],
              ["V4 point distance of the shape set with 4 and 8 random starts", f"{_f(val['V4']['D_starts_4'], 3)} and {_f(val['V4']['D_starts_8'], 3)} ({_f(100 * val['V4']['relative_change'], 1)} %)", "< 5 %", "yes" if val["V4"]["passed"] else "no"]]), "",
          "## 3. The sets", "",
          J._table(["set", "outputs", "D at the fiducial", "D retuned, all simulations (uncorrected / corrected)", "half-sample between, corrected: 5th / median / 95th", "same-code control p95", "verdict"],
                   [[n, p[n]["n_outputs"], _f(p[n]["D_fiducial"]), f"{_f(p[n]['D'])} / {_f(p[n].get('D_corrected'))}", "{} / {} / {}".format(*[_f(s[n]["between"][q]) for q in ("p5", "p50", "p95")]), _f(s[n]["control"]["p95"]), s[n]["verdict"]] for n in ("shape", "sf2", "sf2+shape", "joint", "joint+shape", "hmf") if n in s]), "",
          "Reachable coordinates of the minimising pair for the shape set (half-range units): IllustrisTNG " + ", ".join(f"{x:+.2f}" for x in p["shape"]["a_tng"]) + "; SIMBA " + ", ".join(f"{x:+.2f}" for x in p["shape"]["a_simba"]) + " (a coordinate of 1 is the edge of the CAMELS range, where the emulators are least constrained).", "",
          "## 4. Q2 and Q3: what the shape adds", ""]
    for key, label in (("Q2", "Q2: sf2+shape against sf2"), ("Q3", "Q3: joint+shape against joint")):
        q = res["paired"][key]
        L += [f"**{label}.** Verdicts: {q['base']} {q['verdict_base']}, {q['big']} {q['verdict_big']}. Excess over the controls' change, in the same {q['n']} splits: 5th / median / 95th percentile {_f(q['excess']['p5'], 3)} / {_f(q['excess']['p50'], 3)} / {_f(q['excess']['p95'], 3)}. Unadjusted change of the between-code distance: {_f(q['between']['p5'], 3)} / {_f(q['between']['p50'], 3)} / {_f(q['between']['p95'], 3)}. "
              f"Unadjusted change of the same-code controls: IllustrisTNG {_f(q['control']['IllustrisTNG']['p5'], 3)} / {_f(q['control']['IllustrisTNG']['p50'], 3)} / {_f(q['control']['IllustrisTNG']['p95'], 3)}; SIMBA {_f(q['control']['SIMBA']['p5'], 3)} / {_f(q['control']['SIMBA']['p50'], 3)} / {_f(q['control']['SIMBA']['p95'], 3)}. Rule result: **{q['verdict']}**.", ""]
    L += ["## 5. Where the shape distance comes from (at the minimising pair; share of the weighted sum of squares; rms difference of the block in noise units)", ""]
    for name in ("shape", "sf2+shape"):
        L += [f"**{name}**", "", J._table(["block", "outputs", "share", "rms difference"], [[f"{x['family']} at z = {res['meta']['z'][x['snapshot']]}", x["n_outputs"], f"{100 * x['share']:.1f} %", _f(x["rms_noise_units"])] for x in res["decomposition"][name][:8]]), ""]
    L += ["## 6. What the fiducial simulations look like", "",
          "Mean over the 27 fiducial-parameter simulations (standard deviation between seeds in brackets) of the shape outputs at the first snapshot, by mass bin (bin centres in log10 M*/Msun):", ""]
    z0 = snaps[0]
    for f in SHAPE:
        key = f + "|" + z0
        if key not in res["cv_means"]["IllustrisTNG"]:
            continue
        bins = res["cv_means"]["IllustrisTNG"][key]["bins"]
        rows = []
        for suite in J.SUITES:
            m = res["cv_means"][suite].get(key)
            rows.append([suite] + ([f"{m['mean'][bins.index(b)]:.3f} ({m['sd'][bins.index(b)]:.3f})" if b in m["bins"] else "-" for b in bins] if m else []))
        L += [f"{NAMES[f]} (`{f}`) at z = {res['meta']['z'][z0]}", "", J._table(["code"] + [f"{9.125 + 0.25 * b:.2f}" for b in bins], rows), ""]
    L += ["## 7. Sensitivity analyses (reported, not used to choose)", "",
          J._table(["analysis", "outputs", "D retuned (uncorrected)", "between, corrected: 5th / median / 95th", "same-code control p95", "verdict"],
                   [[f"{k}: {SENS[k]}", p[k]["n_outputs"], _f(p[k]["D"]), "{} / {} / {}".format(*[_f(s[k]["between"][q]) for q in ("p5", "p50", "p95")]), _f(s[k]["control"]["p95"]), s[k]["verdict"]] for k in SENS if k in s]), ""]
    ps = res.get("paired_sensitivity") or {}
    for key, label in (("S1:Q2", "Q2 without the two lowest mass bins"), ("S1:Q3", "Q3 without the two lowest mass bins")):
        q = ps.get(key)
        if q:
            L += [f"{label}: excess over the controls' change, 5th / median / 95th {_f(q['excess']['p5'], 3)} / {_f(q['excess']['p50'], 3)} / {_f(q['excess']['p95'], 3)} noise units; rule result {q['verdict']}.", ""]
    L += ["## 8. Deviations from the protocol and implementation choices", ""] + [f"- {d}" for d in res["deviations"]] + ["",
          "## 9. Limitations", "",
          "Those of the protocol (section 9) apply and are not repeated in full here: two codes at CAMELS resolution; instantaneous star formation rates and zero-SFR galaxies counted as quenched; the choice of two summaries of a distribution that has more; estimators calibrated on a different block layout. A result of \"adds nothing detectable\" means that this method, with these 25 Mpc/h boxes and these two summaries, did not detect more separation, not that none exists.", "",
          "## 10. Reproduce", "",
          "`python3 scripts/ingest_camels_distshape.py` (about 10 minutes, needs fsspec and aiohttp) rebuilds `data/ensembles/camels-distshape.json`; `python3 scripts/analyze_quenching_shape.py` rewrites this file and `data/analysis/quenching-shape.json`; `python3 scripts/test_quenching_shape.py` checks the machinery on synthetic worlds and that these outputs are not stale.", ""]
    return "\n".join(L)


def to_plain(o):
    return json.loads(json.dumps(o, default=lambda x: float(x) if isinstance(x, np.floating) else int(x) if isinstance(x, np.integer) else bool(x) if isinstance(x, np.bool_) else str(x)))


def assemble(data=None, nsplit=NSPLIT, nstarts=4, workers=4, sens=True):
    data = data or load()
    res = run(data, nsplit=nsplit, nstarts=nstarts, workers=workers, sens=sens)
    res["version"] = json.loads((ROOT / "data" / "release.json").read_text())["version"]
    res["protocol"] = "docs/PROTOCOL-quenching-shape.md"
    res["parameters"] = {"seed": SEED, "nsplit": nsplit, "nstarts": nstarts, "margin": J.MARGIN, "floor": J.FLOOR, "kernel": A.KERNEL_H, "ridge": A.RIDGE, "add_min": ADD_MIN}
    s4_path = ROOT / "data" / "analysis" / "joint-reachability.json"
    s4 = json.loads(s4_path.read_text()) if s4_path.exists() else None
    if s4:
        joint_here = sorted(b for b in res["meta"]["sets"]["joint"])
        joint_s4 = sorted(k for k, b in s4["meta"]["blocks"].items() if b["family"] != "hmf")
        res["consistency"] = {"n_blocks_here": len(joint_here), "n_blocks_s4": len(joint_s4), "same_blocks": joint_here == joint_s4, "verdict_here": res["splits"]["joint"]["verdict"], "verdict_s4": s4["splits"]["all"]["verdict"],
                              "note": f"here only {sorted(set(joint_here) - set(joint_s4))}, there only {sorted(set(joint_s4) - set(joint_here))}"}
    res["deviations"] = deviations(res, s4["meta"] if s4 else None)
    res["headline"] = headline(res)
    return to_plain(res)


def write_outputs(res):
    (ROOT / "data" / "analysis" / "quenching-shape.json").write_text(json.dumps(res, indent=1) + "\n")
    (ROOT / "docs" / "ANALYSIS-quenching-shape.md").write_text(render(res))


def main():
    res = assemble()
    write_outputs(res)
    v = res["verdicts"]
    print(f"quenching shape: Q1 {v['Q1']}; Q2 {v['Q2']}; Q3 {v['Q3']}")


if __name__ == "__main__":
    main()
