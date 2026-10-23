"""How much does a model's published output change with resolution? An internal check on the dataset's own records.

Implements docs/PROTOCOL-resolution.md section by section; every departure is reported as a deviation in the generated docs/ANALYSIS-resolution.md. Reads data/curves/*.json (nothing is added to them), data/raw/2509.07960.yml
(the supplementary COLIBRE ladders), data/ensembles/camels-galaxies.json and data/analysis/joint-reachability.json (read only; the noise functions of analyze_joint_reachability.py are called unchanged). Writes
data/analysis/resolution.json and docs/ANALYSIS-resolution.md. Deterministic: no random numbers are used. Usage: python3 scripts/analyze_resolution.py"""
import glob
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_joint_reachability as J

ROOT = Path(__file__).resolve().parent.parent
MARGIN = J.MARGIN                 # protocol section 4: the margin of the joint-reachability study
DZ_EPOCH = 0.1                    # protocol 2.2 rule 3
DZ_SNAP = 0.15                    # protocol 3, reference grid
MIN_PTS = 3
DIG_DEFAULT = 0.02
MIN_PARTICLES = 100               # the reduction of scripts/ingest_colibre_gsmf.py
PROTOCOL = "docs/PROTOCOL-resolution.md"

# relation -> (CAMELS family, kind of x, bin index of the output for rho); protocol section 3
FAMILY = {"gsmf": ("gsmf", "mass"), "quenched": ("qf", "mass"), "ssfr": ("sfms", "mass"), "mzr": ("mzr", "mass"), "zstar": ("zstar", "mass"), "size": ("size", "mass"), "bh": ("bhms", "mass"),
          "shmr": ("shmr", "halo"), "sfrd": ("rho", "z1"), "smd": ("rho", "z0")}
NAMES = {"gsmf": "stellar mass function", "qf": "quenched fraction", "sfms": "star-forming main sequence", "bhms": "black hole mass at fixed M*", "mzr": "gas metallicity at fixed M*", "zstar": "stellar metallicity at fixed M*",
         "size": "stellar half-mass radius at fixed M*", "shmr": "stellar-to-halo mass ratio", "rho": "stellar mass and SFR density"}

# (name, id regex, group of the rung token, groups blanked to make the stem, rung order coarse to fine, token -> rung map, tier, box, parameters, evidence)
EV_TNG = "record warning: 'Parameter change with respect to the fiducial TNG model, from the paper's variation table: resolution only'; one shared initial-condition realization; 25 Mpc/h box"
EV_COL = "run strings give the box (L025); model-variants.json: 'subgrid parameters recalibrated to the same data at each resolution ... weak convergence'"
LADDERS = [
    ("tng-l25n", r"^pillepich18\.tng-l25n(128|256|512)\.fiducial\.sfrd$", 1, [1], ["128", "256", "512"], {}, "A", "same", "unchanged", EV_TNG),
    ("illustris-l25n", r"^pillepich18\.illustris-model-l25n(128|256|512)\.fiducial\.sfrd$", 1, [1], ["128", "256", "512"], {}, "A", "same", "unchanged", EV_TNG),
    ("colibre-l025-gsmf", r"^chaikin26\.colibre\.l025m(7|6|5)\.gsmf\.(z.+)$", 1, [1], ["7", "6", "5"], {}, "A", "same", "recalibrated", EV_COL),
    ("flamingo-l1", r"^schaye23\.flamingo-l1_m(10|9|8)\.(.+)$", 1, [1], ["10", "9", "8"], {}, "A", "same", "recalibrated", "record warnings: 'L1_m8: 1 cGpc box'; model-variants.json: 'subgrid parameters recalibrated by the authors to the same data'"),
    ("thesan", r"^kannan22\.thesan\.(sfrd|uvlf)\.t(1|2)(\.z\d+)?$", 2, [2], ["2", "1"], {}, "A", "same", "not stated", "registry data/simulations.json lists one THESAN box (95.5 cMpc); the records do not state the parameters"),
    ("colibre-boxes", r"^schaye25\.colibre\.(sfrd|ssfr|shmr)\.m(5|6|7)-l(025|050|100|200|400)(\.z0)?$", 2, [2, 3], ["7", "6", "5"], {}, "B", "differs", "recalibrated", "run strings: L400, L200, L025"),
    ("colibre-quenched", r"^chaikin26\.colibre\.quenched\.m(7|6|5)\.(z.+)$", 1, [1], ["7", "6", "5"], {}, "B", "differs", "recalibrated", "run strings: L400m7, L200m6, '(L025, L050 or L100)m5'"),
    ("colibre-mzr", r"^sharda26\.colibre-(m5--l025|m6|m7)\.mzr\.(z.+)$", 1, [1], ["m7", "m6", "m5--l025"], {}, "B", "not stated", "recalibrated", "the box is named for m5 only"),
    ("eagle-furlong15", r"^furlong15\.eagle-(ref|recal)\.(.+)$", 1, [1], ["ref", "recal"], {}, "B", "differs", "not stated", "run strings: Ref-L100N1504, Recal-L025N0752"),
    ("eagle-schaye15", r"^schaye15\.eagle-(ref|recal)\.(.+)$", 1, [1], ["ref", "recal"], {}, "B", "differs", "not stated", "run strings: Ref-L100N1504, Recal-L025N0752"),
    ("eagle-crain17", r"^crain17\.eagle\.hi-fraction\.(ref|recal)\.(z.+)$", 1, [1], ["ref", "recal"], {}, "B", "differs", "not stated", "run strings: Ref-L100N1504, Recal-L025N0752"),
    ("eagle-lagos15", r"^lagos15\.eagle\.h2-fraction\.(refl100n1504|recall025n0752)\.gk11\.z0$", 1, [1], ["refl100n1504", "recall025n0752"], {}, "B", "differs", "not stated", "run strings: Ref-L100N1504, Recal-L025N0752"),
    ("eagle-mzr", r"^sharda26\.eagle-(m6--l100n1504|m5--l025n0752)\.mzr\.(z.+)$", 1, [1], ["m6--l100n1504", "m5--l025n0752"], {}, "B", "differs", "not stated", "run strings: m6 (L100N1504), m5 (L025N0752)"),
    ("tng-donnari21", r"^donnari21\.tng(300|50)\.(quenched-.+)$", 1, [1], ["300", "50"], {}, "B", "differs", "not stated", "run names TNG300-1, TNG50-1"),
    ("tng-mzr", r"^sharda26\.illustristng-tng(300|50)\.mzr\.(z.+)$", 1, [1], ["300", "50"], {}, "B", "differs", "not stated", "run names TNG300, TNG50"),
    ("magneticum", r"^magneticum\.box(0mr|2hr|2bhr|3uhr|4uhr)\.(.+)$", 1, [1], ["mr", "hr", "uhr"], {"0mr": "mr", "2hr": "hr", "2bhr": "hr", "3uhr": "uhr", "4uhr": "uhr"}, "B", "differs", "not stated", "run names Box0/mr, Box2/hr, Box2b/hr, Box3/uhr, Box4/uhr"),
    ("illustris-sparre15", r"^sparre15\.illustris-(lowres|1)\.(.+)$", 1, [1], ["lowres", "1"], {}, "B", "not stated", "not stated", "the 'low resolution' run is not named in the record"),
]
SUPP_LADDERS = [(f"colibre-{box}-gsmf", rf"^supp\.colibre\.{box}m({'|'.join(r)})\.gsmf\.(z.+)$", 1, [1], r, {}, "A", "same", "recalibrated", f"{box.upper()} in the run key of the public file; recalibrated as for L025")
                for box, r in (("l050", ["7", "6", "5"]), ("l100", ["7", "6", "5"]), ("l200", ["7", "6"]))]
DEFS_EXCEPTION = {"thesan": "dustCorrection"}      # protocol 2.2 rule 5: the one free-text difference that is allowed
EPOCH_RX = re.compile(r"\.z\d+(?:\.\d+)?(?=\.|$)")
NOT_BUILT = [
    ("FIREbox, FIRE-2, Romulus25, BlueTides, ASTRID, SPHINX20, FLARES", "one resolution only in the dataset"),
    ("Horizon-AGN and NewHorizon", "registered as separate families; the records do not state that the model is unchanged"),
    ("NIHAO zoom suite and NIHAO-UHD", "different galaxy samples and definitions"),
    ("DARWIN-1 (box) and DARWIN-2 (selected zoom-ins)", "different galaxy samples and different ids"),
    ("SIMBA m100n1024 and hires (Glowacki+20)", "parametric records, not evaluated"),
    ("EAGLE colour counts (Ref-L0025N0376, Ref-L0100N1504, Recal-L0025N0752)", "one point per record, no curve"),
    ("THESAN-SDAO-2", "a different dark matter model, not a resolution"),
    ("TNG100 against TNG50 or TNG300; Illustris-2 and -3", "no record pairs them with equal definitions"),
]
SOURCES = [
    ("IllustrisTNG data pages", "'In order to access any Illustris[TNG] data, you need to first Login.'", False),
    ("EAGLE public database", "'Access to both the database and particle data require only a single account, which you can register for below.'", False),
    ("FLAMINGO", "the page links to a separate data portal and lists lightcone particle data and maps; no credential-free galaxy catalogue was found", False),
    ("THESAN", "the project page has no data statement", False),
    ("COLIBRE paper data (2509.07960.yml)", "served without credentials; already in data/raw; the L050, L100 and L200 ladders are read as a supplementary set", True),
]


# ---------------------------------------------------------------- records
def load_records(root=ROOT):
    recs = {}
    for f in sorted(glob.glob(str(Path(root) / "data" / "curves" / "*.json"))):
        for r in json.loads(Path(f).read_text())["records"]:
            if r["kind"] == "simulation" and r["representation"]["type"] == "points":
                recs[r["id"]] = r
    return recs


def curve(rec):
    p = sorted(rec["representation"]["points"], key=lambda q: q["x"])
    return np.array([q["x"] for q in p], float), np.array([q["y"] for q in p], float)


def digitization(rec):
    u = rec["provenance"].get("digitizationUncertaintyDex")
    if u is not None:
        return float(u)
    return DIG_DEFAULT if rec["provenance"]["tier"] == "digitized-figure" else 0.0


def y_kind(rec):
    return "dex" if "log" in rec["axes"]["yUnit"] else "fraction"


# ---------------------------------------------------------------- supplementary COLIBRE ladders
def supplementary_records(path=None):
    """Mass functions of COLIBRE L050, L100 and L200 from the public file with the reduction of scripts/ingest_colibre_gsmf.py, as records of the dataset's own shape."""
    import yaml
    path = Path(path or ROOT / "data" / "raw" / "2509.07960.yml")
    raw = path.read_bytes()
    data = yaml.safe_load(raw)
    mpart = {"m5": 2.3e5, "m6": 1.84e6, "m7": 1.47e7}
    out = {}
    for box, rungs in (("l050", ("m5", "m6", "m7")), ("l100", ("m5", "m6", "m7")), ("l200", ("m6", "m7"))):
        for rung in rungs:
            key = f"COLIBRE_{box.upper()}{rung}"
            for ztag, block in ((data.get(key) or {}).get("gsmf_raw") or {}).items():
                z = float(ztag[1:])
                x, y, n = (np.asarray(block.get(k, []), dtype=float) for k in ("log10_bin_centers", "log10_gsmf_values", "bin_counts"))
                keep = (n >= 1) & (x - 0.1 >= np.log10(MIN_PARTICLES * mpart[rung]))
                pts = [{"x": float(xv), "y": float(yv)} for xv, yv in zip(x[keep], y[keep])]
                if len(pts) < 2:
                    continue
                rid = f"supp.colibre.{box}{rung}.gsmf.z{z:g}"
                out[rid] = {"id": rid, "source": "COLIBRE", "run": f"{rung} ({box.upper()})", "kind": "simulation", "relation": "gsmf", "epoch": {"zRepresentative": z},
                            "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy number density per dex (raw, no Eddington bias)", "yUnit": "log10(cMpc^-3 dex^-1)"},
                            "definitions": {"imf": "chabrier03", "population": "all"}, "provenance": {"tier": "official-table"}, "representation": {"type": "points", "points": pts}}
    return out, hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------- pairs
def stem_of(i, m, blank):
    s = i
    for g in sorted(blank, reverse=True):
        s = s[:m.start(g)] + "*" + s[m.end(g):]
    return s


def enumerate_pairs(recs, ladders=LADDERS):
    """Epoch-pairs by the inclusion rule of protocol 2.2; the ones that fail a rule are returned with the reason (never silently dropped)."""
    built, refused = [], []
    for name, rx, rg, blank, order, rmap, tier, box, params, ev in ladders:
        stems = defaultdict(lambda: defaultdict(list))
        for i, r in recs.items():
            m = re.match(rx, i)
            if m:
                tok = "-".join(m.group(g) for g in blank)
                rung = rmap.get(m.group(rg), m.group(rg))
                stems[stem_of(i, m, blank)][rung].append((tok, r))
        for stem, byr in sorted(stems.items()):
            rungs = [x for x in order if x in byr]
            if len(rungs) < 2:
                continue
            steps = [(rungs[k], rungs[k + 1], "adjacent") for k in range(len(rungs) - 1) if order.index(rungs[k + 1]) - order.index(rungs[k]) == 1]
            if len(order) >= 3 and rungs[0] == order[0] and rungs[-1] == order[-1] and (rungs[0], rungs[-1], "adjacent") not in steps:
                steps.append((rungs[0], rungs[-1], "span"))
            for ra, rb, kind in steps:
                for ta, a in byr[ra]:
                    for tb, b in byr[rb]:
                        rec = {"ladder": name, "kind": kind, "rung_a": ra, "rung_b": rb, "tok_a": ta, "tok_b": tb, "a": a["id"], "b": b["id"], "relation": a["relation"], "stem": EPOCH_RX.sub("", stem),
                               "z_a": a["epoch"]["zRepresentative"], "z_b": b["epoch"]["zRepresentative"]}
                        why = None
                        if a["relation"] != b["relation"]:
                            why = "relation differs"
                        elif abs(rec["z_a"] - rec["z_b"]) > DZ_EPOCH + 1e-9:
                            why = f"epochs {rec['z_a']:g} and {rec['z_b']:g} are not comparable"
                        elif a["axes"] != b["axes"]:
                            why = "axes differ"
                        else:
                            da, db = dict(a.get("definitions") or {}), dict(b.get("definitions") or {})
                            if name in DEFS_EXCEPTION:
                                da.pop(DEFS_EXCEPTION[name], None)
                                db.pop(DEFS_EXCEPTION[name], None)
                            if da != db:
                                why = "definitions differ"
                        if why:
                            refused.append({**rec, "reason": why})
                        else:
                            built.append(rec)
    return built, refused


def ladder_info(name, ladders):
    for L in ladders:
        if L[0] == name:
            return {"tier": L[6], "box": L[7], "parameters": L[8], "evidence": L[9], "order": L[4]}
    raise KeyError(name)


# ---------------------------------------------------------------- the reference (protocol section 3)
class Reference:
    """The noise scale of the joint-reachability study, by (family, snapshot, bin). `outputs[(family, snapshot)] = {bin: s}`, `centres[family]` the bin centres, `z[snapshot]`."""

    def __init__(self, outputs, centres, z, y0):
        self.outputs, self.centres, self.z, self.y0 = outputs, centres, z, y0

    def snapshot_for(self, zrep):
        best = None
        for sn, z in self.z.items():
            dz = abs(zrep - z)
            if dz <= DZ_SNAP + 1e-9 and (best is None or (dz, z) < (best[1], best[2])):
                best = (sn, dz, z)
        return (best[0], best[1]) if best else (None, None)

    def points(self, relation, snap, lo, hi):
        """Evaluation points (x, s) inside [lo, hi] for this relation at this snapshot (a mass-binned relation) or at every snapshot redshift (sfrd, smd)."""
        fam, kind = FAMILY.get(relation, (None, None))
        if fam is None:
            return np.array([]), np.array([])
        xs, ss = [], []
        if kind in ("mass", "halo"):
            for b, s in sorted(self.outputs.get((fam, snap), {}).items()):
                c = self.centres[fam][b]
                if lo - 1e-9 <= c <= hi + 1e-9:
                    xs.append(c)
                    ss.append(s)
        else:
            b = 1 if kind == "z1" else 0
            for sn, z in sorted(self.z.items(), key=lambda kv: kv[1]):
                o = self.outputs.get((fam, sn), {})
                if b in o and lo - 1e-9 <= z <= hi + 1e-9:
                    xs.append(z)
                    ss.append(o[b])
        return np.array(xs), np.array(ss)


def build_reference():
    data = J.load_galaxies()
    keep, blocks, _ = J.eligibility(data)
    saved = json.loads((ROOT / "data" / "analysis" / "joint-reachability.json").read_text())
    emus, info = J.build_emulators(data, keep, degrees=saved["meta"]["degrees"])
    s = J.noise_scale(info)
    cols = data["meta"]["columns"]
    outputs = defaultdict(dict)
    for j, (f, sn, b) in enumerate(cols):
        if keep[j] and f != "hmf":
            outputs[(f, sn)][b] = float(s[j])
    g = json.loads((ROOT / "data" / "ensembles" / "camels-galaxies.json").read_text())
    mid = lambda e: [(e[i] + e[i + 1]) / 2 for i in range(len(e) - 1)]
    centres = {f: mid(g["mstarEdges"]) for f in ("gsmf", "qf", "sfms", "bhms", "mzr", "zstar", "size", "fgas")}
    centres["shmr"] = mid(g["m200ShmrEdges"])
    y0 = float(np.median(s[keep]))
    check = {}
    for suite in J.SUITES:
        mine = float(np.median(info[suite]["seed_noise"][keep]))
        stored = saved["noise"][suite]["median_seed_noise"]
        check[suite] = {"median_seed_noise": mine, "stored": stored, "match": abs(mine - stored) < 1e-9}
    return Reference(dict(outputs), centres, {k: float(v) for k, v in data["meta"]["z"].items()}, y0), check, saved


# ---------------------------------------------------------------- one epoch-pair
def own_grid(a, b):
    """Shift on the own-point grid: the coarser curve's points in the common range (the finer curve's if the coarser has fewer than 3). Returns (x, d, lo, hi)."""
    (xa, ya), (xb, yb) = curve(a), curve(b)
    lo, hi = max(xa[0], xb[0]), min(xa[-1], xb[-1])
    if hi < lo:
        return np.array([]), np.array([]), lo, hi
    for (x1, y1), (x2, y2), fine_second in (((xa, ya), (xb, yb), True), ((xb, yb), (xa, ya), False)):
        m = (x1 >= lo) & (x1 <= hi)
        if m.sum() >= MIN_PTS:
            x = x1[m]
            d = np.interp(x, x2, y2) - y1[m] if fine_second else y1[m] - np.interp(x, x2, y2)
            return x, d, lo, hi
    return np.array([]), np.array([]), lo, hi


def fine_grid_shift(a, b, x):
    (xa, ya), (xb, yb) = curve(a), curve(b)
    return np.interp(x, xb, yb) - np.interp(x, xa, ya)


def epoch_curve(pair, recs, ref):
    a, b = recs[pair["a"]], recs[pair["b"]]
    x, d, lo, hi = own_grid(a, b)
    delta = float(np.hypot(digitization(a), digitization(b)))
    out = {"a": pair["a"], "b": pair["b"], "z": pair["z_a"], "range": [float(lo), float(hi)], "n_own": int(len(x)), "y_kind": y_kind(a), "digitization": delta}
    if len(x):
        out.update({"rms": float(np.sqrt(np.mean(d ** 2))), "mean": float(np.mean(d)), "max_abs": float(np.max(np.abs(d)))})
        # the other direction of the grid (sensitivity): the finer curve's own points, if there are enough
        (xa, _), (xb, _) = curve(a), curve(b)
        mb = (xb >= lo) & (xb <= hi)
        out["rms_fine_grid"] = float(np.sqrt(np.mean(fine_grid_shift(a, b, xb[mb]) ** 2))) if mb.sum() >= MIN_PTS else None
        out["yard_m2"] = float(np.mean((d / ref.y0) ** 2))
        out["yard_dm2"] = float(np.mean((delta / ref.y0) ** 2))
    rel = pair["relation"]
    snap, dz = ref.snapshot_for(pair["z_a"]) if FAMILY.get(rel, (None, None))[1] in ("mass", "halo") else (None, None)
    out["snapshot"], out["snapshot_dz"] = snap, dz
    out["_grid"] = (x, d)
    return out


def reference_values(ec, pair, recs, ref):
    """m2 and dm2 of the epoch-curve on the CAMELS reference grid, or None when it has fewer than 3 points there."""
    a, b = recs[pair["a"]], recs[pair["b"]]
    lo, hi = ec["range"]
    xs, ss = ref.points(pair["relation"], ec["snapshot"], lo, hi)
    if len(xs) < MIN_PTS:
        return None
    (xa, ya), (xb, yb) = curve(a), curve(b)
    d = np.interp(xs, xb, yb) - np.interp(xs, xa, ya)
    return {"n_ref": int(len(xs)), "m2": float(np.mean((d / ss) ** 2)), "dm2": float(np.mean((ec["digitization"] / ss) ** 2)), "rms_ref": float(np.sqrt(np.mean(d ** 2)))}


# ---------------------------------------------------------------- units
def unit_stat(epcs, zmax=None):
    """R, R_c over the counted epoch-curves of a unit (reference ones if any, else all with the yardstick)."""
    use = [e for e in epcs if zmax is None or e["z"] <= zmax]
    refs = [e for e in use if e.get("ref")]
    if refs:
        basis, m2, dm2 = "reference", [e["ref"]["m2"] for e in refs], [e["ref"]["dm2"] for e in refs]
    else:
        yard = [e for e in use if e["n_own"] >= MIN_PTS]
        basis, m2, dm2 = "yardstick", [e["yard_m2"] for e in yard], [e["yard_dm2"] for e in yard]
    if not m2:
        return {"basis": None, "n_curves": 0, "R": None, "Rc": None}
    R2, D2 = float(np.mean(m2)), float(np.mean(dm2))
    return {"basis": basis, "n_curves": len(m2), "R": float(np.sqrt(R2)), "Rc": float(np.sqrt(max(0.0, R2 - D2)))}


def label(st, tier, margin=MARGIN):
    if st["R"] is None:
        return "cannot tell", "too few points"
    if tier == "A":
        if st["R"] < margin:
            return "converged", ""
        if st["Rc"] > margin:
            return "resolution-dependent", ""
        return "cannot tell", "digitization noise decides"
    if st["R"] < margin:
        return "converged", "box also differs or not stated"
    return "cannot tell", "box also differs or not stated"


def build_units(pairs, recs, ref, ladders):
    by = defaultdict(list)
    for p in pairs:
        by[(p["ladder"], p["kind"], p["rung_a"], p["rung_b"], p["tok_a"], p["tok_b"], p["relation"], p["stem"])].append(p)
    units = []
    for key, ps in sorted(by.items()):
        ladder, kind, ra, rb, ta, tb, relation, stem = key
        info = ladder_info(ladder, ladders)
        ecs = []
        for p in sorted(ps, key=lambda q: q["z_a"]):
            e = epoch_curve(p, recs, ref)
            e["_pair"] = p
            ecs.append(e)
        # reference epoch-curves: one per snapshot (the closest in redshift); sfrd and smd are evaluated at every snapshot redshift
        fam, xkind = FAMILY.get(relation, (None, None))
        if fam is not None and xkind in ("mass", "halo"):
            best = {}
            for e in ecs:
                if e["snapshot"] is not None and (e["snapshot"] not in best or (e["snapshot_dz"], e["z"]) < (best[e["snapshot"]]["snapshot_dz"], best[e["snapshot"]]["z"])):
                    best[e["snapshot"]] = e
            chosen = list(best.values())
        elif fam is not None:
            chosen = ecs[:1]
        else:
            chosen = []
        for e in ecs:
            e["ref"] = reference_values(e, e["_pair"], recs, ref) if any(e is c for c in chosen) else None
        st = unit_stat(ecs)
        lab, qual = label(st, info["tier"])
        own = [e for e in ecs if e["n_own"] >= MIN_PTS]
        u = {"id": f"{ladder}|{kind}|{ra}>{rb}|{ta}>{tb}|{relation}|{stem}", "ladder": ladder, "kind": kind, "rung_a": ra, "rung_b": rb, "token_a": ta, "token_b": tb, "relation": relation, "stem": stem,
             "tier": info["tier"], "box": info["box"], "parameters": info["parameters"], "family": fam, "y_kind": ecs[0]["y_kind"],
             "n_epoch_pairs": len(ecs), "n_epoch_curves_own": len(own), "label": lab, "qualifier": qual, "basis": st["basis"], "R": st["R"], "Rc": st["Rc"], "n_curves_counted": st["n_curves"],
             "rms_dex": float(np.sqrt(np.mean([e["rms"] ** 2 for e in own]))) if own else None, "mean_dex": float(np.mean([e["mean"] for e in own])) if own else None,
             "max_abs_dex": float(max(e["max_abs"] for e in own)) if own else None, "rms_dex_fine_grid": (float(np.sqrt(np.mean([e["rms_fine_grid"] ** 2 for e in own if e["rms_fine_grid"] is not None]))) if any(e["rms_fine_grid"] is not None for e in own) else None),
             "sens": {}}
        for m in (0.5, 2.0):
            u["sens"][f"label_margin_{m:g}"] = label(st, info["tier"], m)[0]
        st3 = unit_stat(ecs, zmax=2.0)
        u["sens"]["label_z_le_2"] = label(st3, info["tier"])[0]
        u["sens"]["R_z_le_2"] = st3["R"]
        u["epochs"] = [{"z": e["z"], "a": e["a"], "b": e["b"], "snapshot": e["snapshot"], "range": e["range"], "n_own": e["n_own"], "rms": e.get("rms"), "mean": e.get("mean"), "max_abs": e.get("max_abs"),
                        "reference": e["ref"], "yard_m2": e.get("yard_m2")} for e in ecs]
        units.append(u)
    return units


# ---------------------------------------------------------------- outcomes
def p1(units):
    A = [u for u in units if u["tier"] == "A" and u["kind"] == "adjacent"]
    tot = defaultdict(int)
    per = defaultdict(lambda: defaultdict(int))
    for u in A:
        tot[u["label"]] += 1
        per[u["ladder"]][u["label"]] += 1
    return {"n_units": len(A), "n_on_reference": sum(1 for u in A if u["basis"] == "reference"), "total": dict(tot), "per_ladder": {k: dict(v) for k, v in per.items()},
            "reference_only": dict(defaultdict(int, {l: sum(1 for u in A if u["basis"] == "reference" and u["label"] == l) for l in ("converged", "resolution-dependent", "cannot tell")}))}


def rel_label(u):
    """The relation, with the variant for the FLAMINGO relations that have several (size apertures, active or passive)."""
    return u["relation"] + (" " + u["stem"].split(".")[-1] if u["ladder"] == "flamingo-l1" and u["relation"] in ("size", "ssfr", "quenched") else "")


def p2(units, saved):
    rows = []
    for u in units:
        if u["tier"] == "A" and u["kind"] == "adjacent" and u["basis"] == "reference" and u["family"]:
            f = u["family"]
            pt = saved["point"].get(f"fam:{f}")
            if not pt:
                continue
            ref_field = "D_fiducial" if u["parameters"] == "unchanged" else "D"
            d_ref = pt[ref_field]
            rows.append({"unit": u["id"], "ladder": u["ladder"], "relation": u["relation"], "relation_label": rel_label(u), "family": f, "rungs": f"{u['rung_a']}>{u['rung_b']}", "parameters": u["parameters"], "Rc": u["Rc"], "R": u["R"],
                         "D": pt["D"], "D_fiducial": pt["D_fiducial"], "compared_with": ref_field, "ratio": u["Rc"] / d_ref, "ratio_D": u["Rc"] / pt["D"], "ratio_D_fiducial": u["Rc"] / pt["D_fiducial"]})
    r = [x["ratio"] for x in rows]
    return {"n": len(rows), "n_ratio_at_least_1": int(sum(1 for v in r if v >= 1.0)), "median_ratio": float(np.median(r)) if r else None, "rows": rows}


def steps(units):
    """For each three-rung ladder, relation and variant: R_c of the finer step over R_c of the coarser step (below 1: the step shrinks). Only where each step is a single unit."""
    by = defaultdict(lambda: defaultdict(list))
    for u in units:
        if u["kind"] == "adjacent" and u["Rc"] is not None:
            by[(u["ladder"], u["relation"], u["stem"])][(u["rung_a"], u["rung_b"])].append(u)
    out = []
    for (ladder, relation, stem), d in by.items():
        order = next(L[4] for L in LADDERS + SUPP_LADDERS if L[0] == ladder)
        if len(order) < 3:
            continue
        s1, s2 = d.get((order[0], order[1]), []), d.get((order[1], order[2]), [])
        if len(s1) == 1 and len(s2) == 1:
            a, b = s1[0], s2[0]
            out.append({"ladder": ladder, "relation": relation, "stem": stem, "coarse_step": f"{order[0]}>{order[1]}", "fine_step": f"{order[1]}>{order[2]}", "Rc_coarse": a["Rc"], "Rc_fine": b["Rc"],
                        "ratio": (b["Rc"] / a["Rc"]) if a["Rc"] > 0 else None, "basis": [a["basis"], b["basis"]], "tier": a["tier"]})
    return sorted(out, key=lambda r: (r["ladder"], r["relation"], r["stem"]))


# ---------------------------------------------------------------- run
def run(recs=None, ref=None, saved=None, supp=None):
    recs = recs or load_records()
    check = None
    if ref is None:
        ref, check, saved = build_reference()
    built, refused = enumerate_pairs(recs)
    units = build_units(built, recs, ref, LADDERS)
    res = {"meta": {"n_records_considered": len(recs), "y0": ref.y0, "margin": MARGIN, "min_points": MIN_PTS, "dz_epoch": DZ_EPOCH, "dz_snapshot": DZ_SNAP, "snapshots": ref.z}, "checks": {}}
    res["checks"]["C1"] = {"passed": bool(check and all(v["match"] for v in check.values())), "detail": check}
    ladders = []
    for L in LADDERS:
        bp = [p for p in built if p["ladder"] == L[0]]
        rf = [p for p in refused if p["ladder"] == L[0]]
        us = [u for u in units if u["ladder"] == L[0]]
        ladders.append({"name": L[0], "tier": L[6], "box": L[7], "parameters": L[8], "evidence": L[9], "rungs": L[4], "n_epoch_pairs_built": len(bp), "n_epoch_pairs_refused": len(rf), "n_units": len(us),
                        "relations": sorted({p["relation"] for p in bp}), "n_adjacent_units": sum(1 for u in us if u["kind"] == "adjacent")})
    res["ladders"], res["units"], res["refused"] = ladders, units, [{k: v for k, v in r.items() if k in ("ladder", "a", "b", "relation", "reason")} for r in refused]
    res["P1"], res["P2"] = p1(units), p2(units, saved)
    res["steps"] = steps(units)
    named = []
    for lad in ("tng-l25n", "illustris-l25n"):
        for u in units:
            if u["ladder"] == lad and u["kind"] == "adjacent" and u["rung_a"] == "256":
                named.append({**{k: u[k] for k in ("id", "ladder", "label", "R", "Rc", "basis", "rms_dex", "mean_dex", "max_abs_dex")}, "name": f"{u['ladder']}: {u['rung_a']} > {u['rung_b']}, {u['relation']}"})
    res["camels_resolution_step"] = named
    # supplementary
    if supp is None:
        supp, digest = supplementary_records()
    else:
        digest = None
    sb, sr = enumerate_pairs(supp, SUPP_LADDERS)
    su = build_units(sb, supp, ref, SUPP_LADDERS)
    res["supplementary"] = {"units": su, "refused": [{k: v for k, v in r.items() if k in ("ladder", "a", "b", "reason")} for r in sr], "n_epoch_pairs": len(sb), "sha256": digest}
    stored = sorted({r["provenance"].get("checksumSha256") for r in recs.values() if r["id"].startswith("chaikin26.colibre.l025m")})
    res["checks"]["C2"] = {"passed": digest is None or stored == [digest], "file_sha256": digest, "record_checksums": stored}
    # sensitivity
    A = [u for u in units if u["tier"] == "A" and u["kind"] == "adjacent"]
    res["sensitivity"] = {"S1_fine_grid_rms_dex": [{"unit": u["id"], "rms_dex": u["rms_dex"], "rms_dex_fine_grid": u["rms_dex_fine_grid"]} for u in A],
                          "S2_label_counts": {m: dict(defaultdict(int, {l: sum(1 for u in A if u["sens"][f"label_margin_{m}"] == l) for l in ("converged", "resolution-dependent", "cannot tell")})) for m in ("0.5", "2")},
                          "S3_label_counts_z_le_2": dict(defaultdict(int, {l: sum(1 for u in A if u["sens"]["label_z_le_2"] == l) for l in ("converged", "resolution-dependent", "cannot tell")}))}
    res["not_built"] = [{"what": w, "why": y} for w, y in NOT_BUILT]
    res["sources"] = [{"source": s, "statement": t, "usable": ok} for s, t, ok in SOURCES]
    return res


def fmt(v, d=2):
    return "-" if v is None else f"{v:.{d}f}"


def headline(res):
    P1, P2 = res["P1"], res["P2"]
    A = [u for u in res["units"] if u["tier"] == "A" and u["kind"] == "adjacent"]
    n_ladders = len({u["ladder"] for u in A})
    L = [f"**Pairs.** {sum(l['n_epoch_pairs_built'] for l in res['ladders'])} epoch-pairs of the same model at two resolutions with equal definitions and a comparable epoch could be built from the dataset, in {len(res['units'])} units (ladder, step, relation) in {sum(1 for l in res['ladders'] if l['n_units'])} ladders; "
         f"{len(A)} adjacent-step units in {n_ladders} ladders (five were registered) have a box stated to be the same (tier A), where the shift can be read as resolution. Another {res['supplementary']['n_epoch_pairs']} epoch-pairs of COLIBRE in other boxes come from the public file (supplementary)."]
    t = P1["total"]
    L.append(f"**P1.** Of the {P1['n_units']} tier A adjacent-step units, {t.get('converged', 0)} are converged (shift below one noise unit), {t.get('resolution-dependent', 0)} resolution-dependent and {t.get('cannot tell', 0)} cannot be told; {P1['n_on_reference']} rest on the CAMELS noise scale, the others on the typical-noise yardstick.")
    if P2["n"]:
        L.append(f"**P2.** For the {P2['n']} units with a counterpart in the joint-reachability study, the resolution shift is at least as large as the TNG-SIMBA distance of that observable in {P2['n_ratio_at_least_1']}; the median ratio of shift to distance is {fmt(P2['median_ratio'])}.")
    else:
        L.append("**P2.** No tier A unit could be put in noise units against a counterpart family.")
    return L


EXTRA_DEVIATIONS = []


def deviations(res):
    d = []
    if not res["checks"]["C1"]["passed"]:
        d.append("Check C1 failed: the rebuilt noise scale does not reproduce the stored seed noise, so the noise-unit columns must not be used.")
    if not res["checks"]["C2"]["passed"]:
        d.append("Check C2 failed: the checksum of the public COLIBRE file differs from the one in the dataset's records.")
    return d + list(EXTRA_DEVIATIONS)


def _table(head, rows):
    return ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


UNIT_HEAD = ["ladder", "relation", "rungs (coarse > fine)", "step", "epoch-pairs", "noise basis", "R", "R_c", "rms shift", "mean shift", "largest", "label"]


def unit_row(u):
    rungs = f"{u['rung_a']} > {u['rung_b']}" + (f" ({u['token_a']} > {u['token_b']})" if u["ladder"] == "magneticum" else "")
    return [u["ladder"], rel_label(u), rungs, u["kind"], u["n_epoch_pairs"], u["basis"] or "-", fmt(u["R"]), fmt(u["Rc"]), fmt(u["rms_dex"], 3), fmt(u["mean_dex"], 3), fmt(u["max_abs_dex"], 3),
            u["label"] + (f" ({u['qualifier']})" if u["qualifier"] else "")]


def render(res):
    P1, P2, S = res["P1"], res["P2"], res["supplementary"]
    A = [u for u in res["units"] if u["tier"] == "A"]
    B = [u for u in res["units"] if u["tier"] == "B"]
    L = ["# Resolution: how much a model's published output changes with it", "",
         f"Generated by `scripts/analyze_resolution.py` from release {res['version']}; do not edit by hand. The pre-specified protocol is [`PROTOCOL-resolution.md`](PROTOCOL-resolution.md) (committed before any shift was computed); this page reports what it gave. "
         "Internal check: no outside expert has reviewed it. It compares published curves of one model at two resolutions, taken from the dataset's own records; it does not test CAMELS, IllustrisTNG or SIMBA at a second resolution.", "",
         "## 1. Answers", ""] + [f"* {h}" for h in res["headline"]] + ["",
         "A noise unit is the standard deviation of the difference between one run of each of the two CAMELS codes (the unit of the joint-reachability distances). R is the root-mean-square shift between the two resolutions in that unit, R_c the same with the digitization noise removed in quadrature. "
         "Dex is a factor of 10 in the quantity (0.1 dex is a factor of 1.26); the quenched fraction is a fraction, and its shift is in fraction. The columns 'rms shift', 'mean shift' and 'largest' are in dex (or fraction), finer minus coarser.", "",
         "## 2. What could be built", ""]
    L += _table(["ladder", "tier", "box", "parameters", "rungs (coarse to fine)", "epoch-pairs built", "refused", "units", "relations"],
                [[l["name"], l["tier"], l["box"], l["parameters"], ", ".join(l["rungs"]), l["n_epoch_pairs_built"], l["n_epoch_pairs_refused"], l["n_units"], ", ".join(l["relations"])] for l in res["ladders"]])
    L += ["", "Tier A: the records or the registry state that the box is the same. Tier B: the box, the sample or the run differs or is not stated, so a shift cannot be attributed to resolution. "
          "Parameters: *unchanged* (the record says resolution only), *recalibrated* (the authors recalibrate at each resolution: weak convergence), *not stated*.", ""]
    if res["refused"]:
        L += ["Epoch-pairs refused by the inclusion rule:", ""] + [f"* `{r['a']}` and `{r['b']}`: {r['reason']}" for r in res["refused"][:40]] + [""]
    L += ["Examined and not built:", ""] + [f"* {n['what']}: {n['why']}." for n in res["not_built"]] + ["", "Other public sources of one model at two resolutions (checked on 2026-10-23, without any account or key):", ""] + \
         [f"* {s['source']}: {s['statement']}. {'Used.' if s['usable'] else 'Not used.'}" for s in res["sources"]] + [""]
    L += ["## 3. Reference noise and checks", "",
          f"The noise scale is that of the joint-reachability study, rebuilt with its own functions. The typical scale (the median over its 186 eligible outputs) is {fmt(res['meta']['y0'], 3)} and is used as the yardstick where an observable has no counterpart. "
          f"Check C1 (the rebuilt seed noise equals the stored one): {'passed' if res['checks']['C1']['passed'] else 'FAILED'}. Check C2 (the public COLIBRE file is the one the dataset's records were made from): {'passed' if res['checks']['C2']['passed'] else 'FAILED'}.", ""]
    L += ["## 4. P1: tier A units by label", ""]
    L += _table(["ladder", "converged", "resolution-dependent", "cannot tell"], [[k, v.get("converged", 0), v.get("resolution-dependent", 0), v.get("cannot tell", 0)] for k, v in sorted(P1["per_ladder"].items())] +
                [["**all**", P1["total"].get("converged", 0), P1["total"].get("resolution-dependent", 0), P1["total"].get("cannot tell", 0)]])
    L += ["", "Adjacent steps only; the span steps are in the next table.", "", "## 5. Tier A units", ""]
    L += _table(UNIT_HEAD, [unit_row(u) for u in A])
    L += ["", "## 6. P2: the resolution shift against the TNG-SIMBA distance", ""]
    if P2["rows"]:
        L += _table(["ladder", "relation", "rungs", "parameters", "R_c", "TNG-SIMBA D (retuned)", "D at fiducial", "compared with", "R_c / D"],
                    [[r["ladder"], r.get("relation_label", r["relation"]), r["rungs"], r["parameters"], fmt(r["Rc"]), fmt(r["D"]), fmt(r["D_fiducial"]), r["compared_with"], fmt(r["ratio"])] for r in P2["rows"]])
        L += ["", f"{P2['n_ratio_at_least_1']} of {P2['n']} units have a ratio of at least 1; the median ratio is {fmt(P2['median_ratio'])}. The distance is taken at the fiducial parameters for a ladder whose parameters are unchanged, retuned (the minimum over both codes' four parameters) for the others."]
    else:
        L += ["No unit qualified."]
    L += ["", "## 7. The step that starts at CAMELS resolution", ""]
    if res["camels_resolution_step"]:
        L += ["The TNG and Illustris models in the 25 Mpc/h box with 256^3 elements (n256) are at CAMELS resolution; n512 has eight times the mass resolution.", ""]
        L += _table(["unit", "label", "R", "R_c", "rms shift (dex)", "mean shift (dex)", "largest (dex)"], [[u.get("name", u["id"]), u["label"], fmt(u["R"]), fmt(u["Rc"]), fmt(u["rms_dex"], 3), fmt(u["mean_dex"], 3), fmt(u["max_abs_dex"], 3)] for u in res["camels_resolution_step"]])
    L += ["", "## 8. Does the step shrink?", ""]
    if res["steps"]:
        L += ["Ratio of R_c of the finer step to that of the coarser step in three-rung ladders (below 1: the step shrinks).", ""]
        L += _table(["ladder", "relation", "variant", "coarse step R_c", "fine step R_c", "ratio", "tier"], [[s["ladder"], s["relation"], s["stem"], fmt(s["Rc_coarse"]), fmt(s["Rc_fine"]), fmt(s["ratio"]), s["tier"]] for s in res["steps"]])
    L += ["", "## 9. Tier B (box, sample or run differs or is not stated)", ""]
    byl = defaultdict(lambda: defaultdict(int))
    for u in B:
        if u["kind"] == "adjacent":
            byl[u["ladder"]][u["label"]] += 1
    L += _table(["ladder", "converged (box also differs)", "cannot tell"], [[k, v.get("converged", 0), v.get("cannot tell", 0)] for k, v in sorted(byl.items())])
    L += ["", "Every tier B unit is in `data/analysis/resolution.json`. The largest rms shifts among them (dex, or fraction for the quenched fraction):", ""]
    big = sorted([u for u in B if u["kind"] == "adjacent" and u["rms_dex"] is not None], key=lambda u: -u["rms_dex"])[:12]
    L += _table(UNIT_HEAD, [unit_row(u) for u in big])
    L += ["", "## 10. Supplementary: COLIBRE in other boxes (public file, not in the dataset)", ""]
    L += _table(UNIT_HEAD, [unit_row(u) for u in S["units"]])
    L += ["", "## 11. Sensitivity (reported, not used to choose)", "",
          f"* Label counts of the tier A adjacent units at the margin 0.5: {res['sensitivity']['S2_label_counts']['0.5']}; at the margin 2: {res['sensitivity']['S2_label_counts']['2']}.",
          f"* Without the epochs at z > 2: {res['sensitivity']['S3_label_counts_z_le_2']}.",
          "* The rms shift on the finer curve's own points in place of the coarser's is in `data/analysis/resolution.json` (`sensitivity.S1_fine_grid_rms_dex`).", "",
          "## 12. Deviations from the protocol", ""] + ([f"* {d}" for d in res["deviations"]] if res["deviations"] else ["None."]) + ["",
          "## 13. What this cannot say", "",
          "* It is not a convergence test of CAMELS: CAMELS is not run at a second resolution here, and SIMBA has no evaluable pair in the dataset. The shifts are those of other models, from their papers.",
          "* Each pair compares two curves of one paper, so the galaxy finder, aperture and mass definition are that paper's. Different papers use different ones; nothing here compares across papers, and the noise unit from CAMELS Subfind catalogues is only a yardstick for them.",
          "* Most curves keep only what lies above the authors' resolution limit, so the shifts below that limit, where resolution matters most, are not in the data and the numbers here understate the effect there.",
          "* Where the authors recalibrate at each resolution, a small shift reflects that recalibration.",
          "* Epochs and relations within a ladder are correlated; the counts are counts of reported rows, not independent tests.", "",
          "## 14. Reproduce", "", "`python3 scripts/analyze_resolution.py` rewrites this file and `data/analysis/resolution.json` (a few seconds; deterministic); `python3 scripts/test_resolution.py` checks the machinery on synthetic records and that the saved output is not stale.", ""]
    return "\n".join(L)


def to_plain(o):
    return json.loads(json.dumps(o, default=lambda x: float(x) if isinstance(x, np.floating) else int(x) if isinstance(x, np.integer) else bool(x) if isinstance(x, np.bool_) else str(x)))


def assemble(**kw):
    res = run(**kw)
    res["version"] = json.loads((ROOT / "data" / "release.json").read_text())["version"]
    res["protocol"] = PROTOCOL
    res["parameters"] = {"margin": MARGIN, "dz_epoch": DZ_EPOCH, "dz_snapshot": DZ_SNAP, "min_points": MIN_PTS, "digitization_default": DIG_DEFAULT, "min_particles_supplementary": MIN_PARTICLES}
    res["deviations"] = deviations(res)
    res["headline"] = headline(res)
    return to_plain(res)


def write_outputs(res):
    (ROOT / "data" / "analysis" / "resolution.json").write_text(json.dumps(res, indent=1) + "\n")
    (ROOT / "docs" / "ANALYSIS-resolution.md").write_text(render(res))


REWORDED = "The table formatting of the report was corrected after the run (unit names with the pipe character broke one table; a variant column was added to the comparison table); no number was recomputed, and the first output is in the version history."


def rerender():
    """Rewrites the text of the report from the saved numbers (no analysis is run): the readable names are added and the headline and the deviations are recomputed; the numbers are not touched."""
    res = json.loads((ROOT / "data" / "analysis" / "resolution.json").read_text())
    by_id = {u["id"]: u for u in res["units"]}
    for r in res["P2"]["rows"]:
        r["relation_label"] = rel_label(by_id[r["unit"]])
    for n in res["camels_resolution_step"]:
        u = by_id[n["id"]]
        n["name"] = f"{u['ladder']}: {u['rung_a']} > {u['rung_b']}, {u['relation']}"
    res["deviations"] = [d for d in deviations(res) if d != REWORDED] + [REWORDED]
    res["headline"] = headline(res)
    write_outputs(res)
    print("resolution: report text rewritten from the saved numbers")


def main():
    if "--rerender" in sys.argv:
        return rerender()
    res = assemble()
    write_outputs(res)
    P1 = res["P1"]
    print(f"resolution: {sum(l['n_epoch_pairs_built'] for l in res['ladders'])} epoch-pairs, {len(res['units'])} units; tier A adjacent {P1['n_units']}: {P1['total']}; P2 {res['P2']['n_ratio_at_least_1']}/{res['P2']['n']}")


if __name__ == "__main__":
    main()
