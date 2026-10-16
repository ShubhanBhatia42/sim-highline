"""Export of everything the Retune page needs, as one JSON file (data/retune/retune.json): the emulators of the joint-reachability study collapsed to polynomials in the four astrophysical coordinates at the fiducial
cosmology (a few thousand coefficients), the noise scale of every output, the block structure, the reachability results of `data/analysis/joint-reachability.json`, and the published curves of the dataset that can be drawn
next to the emulated ones (one record per source, same relation and epoch, definitions attached). Deterministic: the emulators are refitted with the code of the analysis. Usage: python3 scripts/export_retune_data.py"""
import itertools
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_joint_reachability as J
import analyze_model_form as A

ROOT = Path(__file__).resolve().parent.parent
PARAMS = [
    {"id": "ASN1", "label": "A_SN1", "base": 4, "range": "x0.25 to x4", "TNG": "galactic wind energy per unit star formation", "SIMBA": "wind mass loading factor"},
    {"id": "AAGN1", "label": "A_AGN1", "base": 4, "range": "x0.25 to x4", "TNG": "kinetic-mode black hole feedback energy", "SIMBA": "momentum flux of quasar and jet-mode feedback"},
    {"id": "ASN2", "label": "A_SN2", "base": 2, "range": "x0.5 to x2", "TNG": "galactic wind speed", "SIMBA": "wind speed"},
    {"id": "AAGN2", "label": "A_AGN2", "base": 2, "range": "x0.5 to x2", "TNG": "burstiness of kinetic-mode feedback", "SIMBA": "jet speed"},
]
# what each family is, how it is drawn, and how a published record of the same relation is converted to it
FAMILY_META = {
    "gsmf": {"title": "Stellar mass function", "x": "log M* [Msun]", "y": "log number density [cMpc^-3 dex^-1]", "relation": "gsmf", "kind": "line"},
    "qf": {"title": "Quenched fraction", "x": "log M* [Msun]", "y": "fraction with sSFR < 1e-11 / yr", "relation": "quenched", "kind": "line"},
    "sfms": {"title": "Specific SFR of star-forming galaxies", "x": "log M* [Msun]", "y": "log sSFR [1/yr] (median)", "relation": "sfms", "kind": "line", "convert": "log sSFR = log SFR - log M*"},
    "bhms": {"title": "Black hole mass", "x": "log M* [Msun]", "y": "log M_BH [Msun] (median)", "relation": "bh", "kind": "line"},
    "bhocc": {"title": "Black hole occupation", "x": "log M* [Msun]", "y": "fraction with a black hole", "relation": None, "kind": "line"},
    "mzr": {"title": "Gas metallicity", "x": "log M* [Msun]", "y": "log Z_gas / 0.0127 (SFR-weighted, median)", "relation": "mzr", "kind": "line", "only_axis": "metal mass fraction"},
    "zstar": {"title": "Stellar metallicity", "x": "log M* [Msun]", "y": "log Z* / 0.0127 (median)", "relation": "zstar", "kind": "line", "only_axis": "stellar metallicity"},
    "size": {"title": "Stellar half-mass radius", "x": "log M* [Msun]", "y": "log R_1/2 [kpc, physical] (median)", "relation": "size", "kind": "line", "only_axis": "3D stellar half-mass"},
    "fgas": {"title": "Gas fraction inside 2 R_1/2", "x": "log M* [Msun]", "y": "M_gas / (M_gas + M*) (median)", "relation": None, "kind": "line"},
    "shmr": {"title": "Stellar-to-halo mass ratio (centrals)", "x": "log M200c [Msun]", "y": "log M* / M200c (median)", "relation": "shmr", "kind": "line"},
    "rho": {"title": "Cosmic densities", "x": "", "y": "log10 per cMpc^3", "relation": None, "kind": "points", "labels": ["stellar mass (Msun)", "SFR (Msun/yr)"]},
    "hmf": {"title": "Halo mass function (control)", "x": "log M200c [Msun]", "y": "log number density [cMpc^-3 dex^-1]", "relation": None, "kind": "line"},
}
ZOOM = {"FIRE-2", "NIHAO zoom suite", "NewHorizon", "Romulus25", "THESAN-zoom"}
VARIANT = re.compile(r"variation|low[- ]?res|double|single|per galaxy|hybrid|noAGN|full SUBFIND|2 R_half|rTNG|secondary|individual|Recal-|central|quenched|L025|L050|m5|m7|Box0|Box2b|Box3|Box4|\bfit\b", re.I)


def quad_terms(degree):
    t = [()] + [(j,) for j in range(6)] + [c for c in itertools.combinations_with_replacement(range(6), 2)]
    if degree >= 3:
        t += list(itertools.combinations_with_replacement(range(6), 3))
    return t


def collapse(emu):
    """Coefficients of the polynomial in the four astrophysical coordinates at x1 = x2 = 0: the terms that contain a cosmological coordinate vanish."""
    terms = quad_terms(emu.degree)
    keep = [i for i, t in enumerate(terms) if all(j >= 2 for j in t)]
    return [[j - 2 for j in terms[i]] for i in keep], emu.coef[keep, :]


def bin_centres(d, fam):
    if fam in ("shmr",):
        e = d["m200ShmrEdges"]
    elif fam == "hmf":
        e = d["m200HmfEdges"]
    elif fam == "rho":
        return [0, 1]
    else:
        e = d["mstarEdges"]
    return [round((a + b) / 2, 4) for a, b in zip(e[:-1], e[1:])]


def overlays(raw, snapshots):
    """For every family with a counterpart in the dataset and every snapshot: one curve per source (fiducial-like, no zoom samples), converted to the family's axes where that is a plain subtraction."""
    recs = []
    for f in sorted((ROOT / "data" / "curves").glob("*.json")):
        recs += json.loads(f.read_text())["records"]
    out = []
    for fam, meta in FAMILY_META.items():
        rel = meta.get("relation")
        if not rel:
            continue
        for snap, z in snapshots.items():
            cand = [r for r in recs if r["relation"] == rel and r["representation"]["type"] == "points" and r["kind"] in ("simulation", "observation") and r["source"] not in ZOOM
                    and abs(r["epoch"]["zRepresentative"] - z) <= 0.3 and not VARIANT.search(r.get("run") or "")]
            if "only_axis" in meta:
                cand = [r for r in cand if meta["only_axis"].lower() in (r["axes"].get("yDefinition", "") + " " + r["axes"].get("xDefinition", "")).lower() or fam == "size" and "half-mass" in r["axes"].get("yDefinition", "").lower() and "projected" not in r["axes"].get("yDefinition", "").lower()]
            best = {}
            for r in cand:
                k = (r["source"], r["kind"])
                if k not in best or abs(r["epoch"]["zRepresentative"] - z) < abs(best[k]["epoch"]["zRepresentative"] - z):
                    best[k] = r
            for (src, kind), r in sorted(best.items()):
                pts = [(p["x"], p["y"]) for p in r["representation"]["points"]]
                if fam == "sfms":
                    # a star formation rate (log Msun/yr: every value above -6) becomes a specific rate by subtracting log M*; a specific rate (log 1/yr, every value below -6) is kept
                    ys_ = sorted(y for _, y in pts)
                    if ys_[len(ys_) // 2] > -6:
                        pts = [(x, y - x) for x, y in pts]
                xs = [x for x, _ in pts]
                if not xs or max(xs) < 9.0 or min(xs) > 11.6:
                    continue
                out.append({"family": fam, "snapshot": snap, "label": r.get("run") or src, "source": src, "kind": kind, "tier": r["provenance"]["tier"], "z": r["epoch"]["zRepresentative"], "id": r["id"],
                            "x": [round(x, 3) for x, _ in pts], "y": [round(y, 4) for _, y in pts], "xDef": r["axes"].get("xDefinition"), "yDef": r["axes"].get("yDefinition"), "mass": r["definitions"].get("massDefinition"), "imf": r["definitions"].get("imf")})
    return out


NATIVE_UNIT = {"gsmf": "dex", "qf": "fraction", "sfms": "dex", "bhms": "dex", "bhocc": "fraction", "mzr": "dex", "zstar": "dex", "size": "dex", "fgas": "fraction", "shmr": "dex", "rho": "dex"}


def native_table(emus, keep, blocks, scale, point):
    """The distances of the study in the units of the observables (descriptive; the registered distances are in noise units): for every joint family the rms difference between the two codes' emulated outputs, equal weight per block, at the fiducial parameters,
    at the best setting for that family alone and at the best joint setting, and the size of one noise unit (rms of the noise scale over the family's outputs)."""
    co = {s: collapse(emus[s]) for s in J.SUITES}

    def predict(s, a, js):
        terms, coef = co[s]
        feats = np.array([np.prod([a[i] for i in t]) if t else 1.0 for t in terms])
        return feats @ coef[:, js]

    def rms(fam, aT, aS):
        ms = []
        for b, js in blocks.items():
            if b[0] != fam:
                continue
            d = predict("IllustrisTNG", aT, js) - predict("SIMBA", aS, js)
            ms.append(float(np.mean(d[np.isfinite(d)] ** 2)))
        return float(np.sqrt(np.mean(ms))) if ms else None

    zero = [0.0] * 4
    rows = {}
    for f in NATIVE_UNIT:
        js = [j for b, v in blocks.items() if b[0] == f for j in v]
        if not js:
            continue
        alone, joint = point.get("fam:" + f), point["all"]
        rows[f] = {"unit": NATIVE_UNIT[f], "fiducial": rms(f, zero, zero), "alone": rms(f, alone["a_tng"], alone["a_simba"]) if alone else None, "joint": rms(f, joint["a_tng"], joint["a_simba"]),
                   "noise_unit": float(np.sqrt(np.mean(scale[js] ** 2)))}
    return rows


def export(data=None, analysis=None, path=None, with_overlays=True):
    raw = json.loads((ROOT / "data" / "ensembles" / "camels-galaxies.json").read_text()) if data is None else None
    data = data or J.load_galaxies()
    keep, blocks, _ = J.eligibility(data)
    emus, info = J.build_emulators(data, keep)
    scale = J.noise_scale(info)
    cols = data["meta"]["columns"]
    snaps = data["meta"]["z"]
    out = {"version": json.loads((ROOT / "data" / "release.json").read_text())["version"], "params": PARAMS, "snapshots": [{"id": s, "z": snaps[s]} for s in data["meta"]["snapshots"]],
           "families": {f: {**FAMILY_META[f], "x_centres": bin_centres(raw, f) if raw else list(range(10)), "joint": f != "hmf"} for f in J.FAMILIES}, "family_names": J.FAMILY_NAMES,
           "outputs": [{"f": cols[j][0], "s": cols[j][1], "b": int(cols[j][2])} for j in range(len(cols)) if keep[j]], "blocks": {}, "codes": {}}
    index = {j: i for i, j in enumerate(np.where(keep)[0])}
    for b, v in blocks.items():
        out["blocks"]["|".join(b)] = [index[j] for j in v]
    for suite in J.SUITES:
        terms, coef = collapse(emus[suite])
        c = coef[:, keep]
        out["codes"][suite] = {"degree": emus[suite].degree, "terms": terms, "coef": [[None if not np.isfinite(v) else float(f"{v:.6g}") for v in row] for row in c],
                               "seed": [float(f"{v:.5g}") for v in info[suite]["seed_noise"][keep]], "emulator_error": [float(f"{v:.5g}") for v in info[suite]["emulator_error"][keep]],
                               "fiducial_cv": [None if not np.isfinite(v) else float(f"{v:.5g}") for v in info[suite]["cv_mean"][keep]]}
    out["scale"] = [float(f"{v:.5g}") for v in scale[keep]]
    out["floor"] = J.FLOOR
    out["margin"] = J.MARGIN
    out["analysis"] = analysis
    out["native"] = native_table(emus, keep, blocks, scale, analysis["point"]) if analysis else None
    if with_overlays and raw:
        out["overlays"] = overlays(raw, {s: snaps[s] for s in data["meta"]["snapshots"]})
    p = Path(path or ROOT / "data" / "retune" / "retune.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    return out


def analysis_summary():
    p = ROOT / "data" / "analysis" / "joint-reachability.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text())
    keep = ("D", "D_corrected", "D_fiducial", "a_tng", "a_simba", "n_outputs", "n_blocks")
    return {"verdicts": r["verdicts"], "point": {k: {x: v.get(x) for x in keep} for k, v in r["point"].items()},
            "splits": {k: {x: v.get(x) for x in ("verdict", "between", "between_raw", "control")} for k, v in r["splits"].items() if k.startswith(("all", "fam:", "z:"))},
            "greedy_path": r["greedy_path"], "separating_set": r["separating_set"], "decomposition": r["decomposition"][:12], "J3": r.get("J3")}


def main():
    out = export(analysis=analysis_summary())
    p = ROOT / "data" / "retune" / "retune.json"
    print(f"{p}: {p.stat().st_size / 1e3:.0f} kB, {len(out['outputs'])} outputs, {len(out.get('overlays', []))} overlay curves")


if __name__ == "__main__":
    main()
