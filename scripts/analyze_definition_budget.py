"""Definition budget: do simulations that share documented definitions agree better?

For each relation and epoch, every pair of records from different suites is classified from the
documented definitions alone (no correction is applied to any curve):
  matched     all hard and soft keys documented and equal
  differing   hard keys equal, at least one soft key documented and different
  unknown     at least one key undocumented in either record
The statistic is the median over pairs of the per-pair median |delta y| on the overlapping x range
(linear interpolation inside each record's own range, never extrapolated, no gap wider than MAX_GAP).
Significance: suite-level label permutation. Uncertainty: bootstrap over suites.
"""
import glob, json, itertools, random, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED, NPERM, NBOOT = 20261010, 2000, 1000
STEP, MAX_GAP, MIN_PTS = 0.1, 0.6, 5
UNSET = {None, "unspecified", "heterogeneous"}
EPOCHS = [(0, 0.2), (1, 0.3), (2, 0.3), (4, 0.4), (6, 0.5)]
RELATIONS = ["gsmf", "mzr", "sfms", "shmr", "size", "zstar", "bh"]
IGNORE_SOFT = {"cosmology"}

def rules():
    src = (ROOT / "compare.js").read_text()
    block = re.search(r"const RULES=\{(.*?)\n\};", src, re.S).group(1)
    out = {}
    for m in re.finditer(r"(\"?[\w-]+\"?):\{hard:\[(.*?)\],soft:\[(.*?)\]\}", block):
        keys = lambda s: [k.strip().strip('"') for k in s.split(",") if k.strip()]
        out[m.group(1).strip('"')] = (keys(m.group(2)), keys(m.group(3)))
    return out

def load():
    recs = []
    for f in sorted(glob.glob(str(ROOT / "data/curves/*.json"))):
        recs += json.load(open(f))["records"]
    return recs

def usable(r, rel, z0, tol):
    if r["kind"] != "simulation" or r["relation"] != rel: return False
    z = r["epoch"].get("zRepresentative")
    if z is None or abs(z - z0) > tol: return False
    if r["representation"].get("type") != "points" or "variation" in r["run"]: return False
    pts = r["representation"]["points"]
    return len(pts) >= 3 and all(isinstance(p.get("x"), (int, float)) for p in pts)

def curve(r):
    pts = sorted((p["x"], p["y"]) for p in r["representation"]["points"] if isinstance(p.get("y"), (int, float)))
    return pts

def at(pts, x):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return None if x1 - x0 > MAX_GAP else y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y0
    return None

def pair_delta(a, b):
    ca, cb = curve(a), curve(b)
    lo, hi = max(ca[0][0], cb[0][0]), min(ca[-1][0], cb[-1][0])
    if hi - lo < STEP * (MIN_PTS - 1): return None
    ds, x = [], lo
    while x <= hi + 1e-9:
        ya, yb = at(ca, x), at(cb, x)
        if ya is not None and yb is not None: ds.append(abs(ya - yb))
        x += STEP
    return st.median(ds) if len(ds) >= MIN_PTS else None

def classify(a, b, hard, soft):
    da, db = a["definitions"], b["definitions"]
    for k in hard:
        if da.get(k) in UNSET or db.get(k) in UNSET: return "unknown"
        if da.get(k) != db.get(k): return "mismatch"
    diff = unk = False
    for k in soft:
        if k in IGNORE_SOFT: continue
        if da.get(k) in UNSET or db.get(k) in UNSET: unk = True
        elif da.get(k) != db.get(k): diff = True
    return "unknown" if unk else "differing" if diff else "matched"

def med(v): return st.median(v) if v else None

def stat(pairs, label_of=None):
    m = [d for s, t, d, c in pairs if (label_of(s, t) if label_of else c) == "matched"]
    d = [d for s, t, d_, c in pairs for d in [d_] if (label_of(s, t) if label_of else c) == "differing"]
    return (med(d) - med(m)) if m and d else None

SENS_KEYS = {"massDefinition", "haloMassDefinition", "sfrTimescaleMyr", "sizeDefinition", "dustCorrection", "gasDefinition", "jDefinition", "sigmaDefinition"}
SENS_SKIP_RELATIONS = {"quenched"}
IGN_DEF = {"cosmology", "imfBasis"}

def run_base(run):
    return re.split(r"[\s(,]", run.strip(), maxsplit=1)[0]

def sensitivity(recs):
    sim = [r for r in recs if r["kind"] == "simulation" and r["representation"].get("type") == "points" and len(r["representation"]["points"]) >= 5]
    groups = {}
    for r in sim:
        groups.setdefault((r["source"], r["relation"], round(r["epoch"]["zRepresentative"], 2)), []).append(r)
    rows = []
    for (src, rel, z), rs in groups.items():
        for a, b in itertools.combinations(rs, 2):
            A = {k: v for k, v in a["definitions"].items() if k not in IGN_DEF}
            B = {k: v for k, v in b["definitions"].items() if k not in IGN_DEF}
            diff = [k for k in set(A) | set(B) if A.get(k) != B.get(k)]
            if rel in SENS_SKIP_RELATIONS or len(diff) != 1 or diff[0] not in SENS_KEYS: continue
            key = diff[0]
            if a["axes"]["xUnit"] != b["axes"]["xUnit"] or a["axes"]["yUnit"] != b["axes"]["yUnit"]: continue
            if key != "sfrTimescaleMyr" and run_base(a["run"]) != run_base(b["run"]): continue
            ca, cb = curve(a), curve(b)
            lo, hi = max(ca[0][0], cb[0][0]), min(ca[-1][0], cb[-1][0])
            ds, x = [], lo
            while x <= hi + 1e-9:
                ya, yb = at(ca, x), at(cb, x)
                if ya is not None and yb is not None: ds.append(yb - ya)
                x += STEP
            if len(ds) < MIN_PTS: continue
            va, vb, sign = str(A.get(key)), str(B.get(key)), 1
            if va > vb: a, b, va, vb, sign = b, a, vb, va, -1
            rows.append({"source": src, "relation": rel, "z": z, "key": key, "from": A.get(key) if sign == 1 else B.get(key), "to": B.get(key) if sign == 1 else A.get(key),
                         "idFrom": a["id"], "idTo": b["id"], "median_dy": sign * med(ds), "max_abs_dy": max(abs(d) for d in ds), "bins": len(ds),
                         "xRange": [round(lo, 2), round(hi, 2)]})
    rows.sort(key=lambda r: (r["relation"], r["key"], r["source"], str(r["from"]), r["z"]))
    agg = {}
    for r in rows:
        agg.setdefault((r["source"], r["relation"], r["key"], str(r["from"]), str(r["to"])), []).append(r)
    summary = [{"source": k[0], "relation": k[1], "key": k[2], "from": k[3], "to": k[4], "epochs": len(v),
                "zRange": [min(x["z"] for x in v), max(x["z"] for x in v)], "median_dy": med([x["median_dy"] for x in v]),
                "medianRange": [min(x["median_dy"] for x in v), max(x["median_dy"] for x in v)], "max_abs_dy": max(x["max_abs_dy"] for x in v)}
               for k, v in sorted(agg.items())]
    return {"pairs": rows, "summary": summary}

def analyse(recs, rules_by_rel, rankable_only):
    rng = random.Random(SEED)
    out = []
    for rel in RELATIONS:
        hard, soft = rules_by_rel[rel]
        for z0, tol in EPOCHS:
            rr = [r for r in recs if usable(r, rel, z0, tol) and (r["rankable"] or not rankable_only)]
            ax = {(r["axes"]["xUnit"], r["axes"]["yUnit"]) for r in rr}
            if len(ax) > 1:
                top = max(sorted(ax), key=lambda a: sum((r["axes"]["xUnit"], r["axes"]["yUnit"]) == a for r in rr))
                rr = [r for r in rr if (r["axes"]["xUnit"], r["axes"]["yUnit"]) == top]
            suites = sorted({r["source"] for r in rr})
            if len(suites) < 3: continue
            pairs = []
            for a, b in itertools.combinations(rr, 2):
                if a["source"] == b["source"]: continue
                d = pair_delta(a, b)
                if d is None: continue
                pairs.append((a["source"], b["source"], d, classify(a, b, hard, soft)))
            cnt = {c: sum(p[3] == c for p in pairs) for c in ("matched", "differing", "unknown", "mismatch")}
            row = {"relation": rel, "z": z0, "suites": suites, "records": len(rr), "pairs": len(pairs), "counts": cnt,
                   "median_abs_dy": {c: med([p[2] for p in pairs if p[3] == c]) for c in cnt}}
            row["documented_fraction"] = round(sum(1 for r in rr for k in hard + [k for k in soft if k not in IGNORE_SOFT]
                                                   if r["definitions"].get(k) not in UNSET) /
                                               max(1, sum(1 for r in rr for k in hard + [k for k in soft if k not in IGNORE_SOFT])), 3)
            obs = stat(pairs)
            row["excess_differing_minus_matched"] = obs
            if obs is not None and cnt["matched"] >= 3 and cnt["differing"] >= 3:
                idx = [(i, j) for i, j in itertools.combinations(range(len(rr)), 2) if rr[i]["source"] != rr[j]["source"] and pair_delta(rr[i], rr[j]) is not None]
                deltas = [pair_delta(rr[i], rr[j]) for i, j in idx]
                defs = [r["definitions"] for r in rr]
                ge = 0
                for _ in range(NPERM):
                    perm = defs[:]
                    rng.shuffle(perm)
                    m, d = [], []
                    for (i, j), dl in zip(idx, deltas):
                        c = classify({"definitions": perm[i]}, {"definitions": perm[j]}, hard, soft)
                        if c == "matched": m.append(dl)
                        elif c == "differing": d.append(dl)
                    if m and d and med(d) - med(m) >= obs: ge += 1
                row["p_permutation"] = round((ge + 1) / (NPERM + 1), 4)
                boots = []
                for _ in range(NBOOT):
                    pick = [rng.choice(suites) for _ in suites]
                    w = {}
                    for s in pick: w[s] = w.get(s, 0) + 1
                    bp = []
                    for s, t, d, c in pairs:
                        for _ in range(w.get(s, 0) * w.get(t, 0)): bp.append((s, t, d, c))
                    v = stat(bp)
                    if v is not None: boots.append(v)
                if len(boots) > 100:
                    boots.sort()
                    row["ci95_excess"] = [round(boots[int(.025 * len(boots))], 4), round(boots[int(.975 * len(boots))], 4)]
            out.append(row)
    return out

def main():
    recs, rb = load(), rules()
    result = {"method": __doc__.strip(), "parameters": {"seed": SEED, "permutations": NPERM, "bootstrap": NBOOT,
              "gridStepDex": STEP, "maxGapDex": MAX_GAP, "minGridPoints": MIN_PTS, "epochs": EPOCHS, "ignoredSoftKeys": sorted(IGNORE_SOFT)},
              "allRecords": analyse(recs, rb, False), "rankableOnly": analyse(recs, rb, True), "sensitivity": sensitivity(recs)}
    def rnd(o):
        if isinstance(o, float): return round(o, 4)
        if isinstance(o, dict): return {k: rnd(v) for k, v in o.items()}
        if isinstance(o, list): return [rnd(v) for v in o]
        return o
    tot = {c: sum(r["counts"][c] for r in result["allRecords"]) for c in ("matched", "differing", "unknown", "mismatch")}
    tested = [r for r in result["allRecords"] if r.get("p_permutation") is not None]
    result["summary"] = {"pairs": sum(tot.values()), "byClass": tot, "testsRun": len(tested),
                         "testsBelow0.05": sum(r["p_permutation"] < 0.05 for r in tested),
                         "expectedBelow0.05UnderNull": round(0.05 * len(tested), 2),
                         "bonferroniSignificant": sum(r["p_permutation"] * len(tested) < 0.05 for r in tested)}
    path = ROOT / "data/analysis/definition-budget.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(rnd(result), indent=1) + "\n")
    report(result)
    print('== definition sensitivity:', len(result['sensitivity']['pairs']), 'within-run pairs,', len(result['sensitivity']['summary']), 'groups')
    for r in result['sensitivity']['summary']: print(f"{r['source']:13} {r['relation']:6} {r['key']:17} {str(r['from'])[:26]:26} -> {str(r['to'])[:26]:26} epochs={r['epochs']:2} median={r['median_dy']:+.2f} range=[{r['medianRange'][0]:+.2f},{r['medianRange'][1]:+.2f}] max={r['max_abs_dy']:.2f}")
    for key in ("allRecords", "rankableOnly"):
        print("==", key)
        for r in result[key]:
            c = r["counts"]; m = r["median_abs_dy"]
            f = lambda v: "  -  " if v is None else f"{v:5.2f}"
            print(f"{r['relation']:5} z{r['z']} suites={len(r['suites'])} pairs={r['pairs']:3} m/d/u/x={c['matched']}/{c['differing']}/{c['unknown']}/{c['mismatch']} "
                  f"|dy| m={f(m['matched'])} d={f(m['differing'])} u={f(m['unknown'])} excess={f(r['excess_differing_minus_matched'])} p={r.get('p_permutation')} ci={r.get('ci95_excess')} doc={r['documented_fraction']}")

def report(result):
    t = result["summary"]; n = t["pairs"]; c = t["byClass"]
    pc = lambda k: f"{100 * c[k] / n:.0f}%"
    lines = ["# Definition budget", "",
             "Generated by `scripts/analyze_definition_budget.py` from `data/curves/`; do not edit by hand. Numbers: `data/analysis/definition-budget.json`.", "",
             "## Question", "",
             "How much of the disagreement between simulations at fixed stellar mass (or halo mass) can be attributed to differences in documented definitions, as opposed to physics or numerics? No curve is corrected; pairs of records from different suites are classified from the documented definitions alone and their offsets compared.", "",
             "## What the data allow", "",
             f"Of {n} usable cross-suite record pairs (7 relations, 5 epochs), {pc('matched')} have every documented key equal (matched), {pc('differing')} differ in a documented soft key, {pc('unknown')} cannot be classified because a definition is undocumented in at least one record, and {pc('mismatch')} differ in a hard key (for example different size definitions) and are not comparable at all.", "",
             f"Of {t['testsRun']} epoch-by-relation permutation tests with enough matched and differing pairs, {t['testsBelow0.05']} have p < 0.05; {t['expectedBelow0.05UnderNull']} would be expected by chance alone. After Bonferroni correction {t['bonferroniSignificant']} remain. The honest reading is that the present records neither show nor rule out a definitional contribution; the binding constraint is documentation, not physics.", "",
             "## By relation and epoch (all simulation records)", "",
             "| relation | z | suites | pairs (matched / differing / unknown / not comparable) | median abs dy: matched | differing | unknown | excess | p |",
             "|---|---|---|---|---|---|---|---|---|"]
    f = lambda v: "-" if v is None else f"{v:.2f}"
    for r in result["allRecords"]:
        k, m = r["counts"], r["median_abs_dy"]
        lines.append(f"| {r['relation']} | {r['z']} | {len(r['suites'])} | {r['pairs']} ({k['matched']} / {k['differing']} / {k['unknown']} / {k['mismatch']}) | {f(m['matched'])} | {f(m['differing'])} | {f(m['unknown'])} | {f(r['excess_differing_minus_matched'])} | {r.get('p_permutation', '-')} |")
    lines += ["", "Units: dex in the relation's y axis (log10). excess = median(differing) - median(matched).", "",
              "## Definition sensitivity measured inside single runs", "",
             "Where one simulation run is published under two definitions of one quantity (and nothing else differs in the record), the offset between the two curves is a purely definitional effect. Population splits (active versus passive) and model variations are excluded. Offsets are median (to minus from) over the shared x range, in y units; the range is over epochs.", "",
             "| simulation | relation | what changes | from | to | epochs | median | range of medians | largest local offset |", "|---|---|---|---|---|---|---|---|---|"]
    for r in result["sensitivity"]["summary"]:
        lines.append(f"| {r['source']} | {r['relation']} | {r['key']} | {str(r['from'])[:48]} | {str(r['to'])[:48]} | {r['epochs']} (z {r['zRange'][0]:g}-{r['zRange'][1]:g}) | {r['median_dy']:+.2f} | {r['medianRange'][0]:+.2f} to {r['medianRange'][1]:+.2f} | {r['max_abs_dy']:.2f} |")
    lines += ["",
             "## Method", "", result["method"], "",
              "## Limits", "",
              "- Records within one suite are not independent; pairs are formed between different suites only, and the permutation shuffles definitions across records.",
              "- Digitized records are included (they are never rankable); the rankable-only run in the JSON is the robustness check and is far smaller.",
              "- Cosmology differences are ignored: values are h-free as published.",
              "- Only documented keys count. An undocumented definition is not assumed equal to anything.",
              "- Choosing the matched class from the repository's own comparability rules (`compare.js`) means the answer depends on those rules; they are conventions, not measurements.",
              "- A definition label is not a definition: for example `aperture-30pkpc` versus `aperture-50pkpc` are different apertures but `unspecified` hides everything.", ""]
    (ROOT / "docs/ANALYSIS-definition-budget.md").write_text("\n".join(lines))

if __name__ == "__main__":
    main()
