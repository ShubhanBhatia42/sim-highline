"""A real public catalogue through `sim-highline derive`, and the result next to the stored CAMELS-TNG curves.

The catalogue is the z = 0 Subfind catalogue of one CAMELS-TNG cosmic-variance box (CV_0, 25 Mpc/h on a side) from the public CAMELS server, which needs no account. This script does not download it
(the download is the `curl` line in docs/DERIVE-REAL-CATALOGUE.md); it takes the folder you saved it in (named camels-tng-cv0), and reads it with h5py only.

What it checks, in this order:
1. The file is the one the stored per-box summaries were made from: the hash of the arrays the ingest script reads equals the hash stored in data/ensembles/camels-galaxies.json, and recomputing that
   summary from the file gives the stored values exactly.
2. `derive` runs on it with the definitions stated in STATED (nothing else is assumed), and writes nine records.
3. The numbers `derive` wrote are recomputed from the file by separate plain-numpy code (the number of galaxies above the cut and the five relations that can be compared) and agree to the last digit.
4. The records are compared with the stored same-simulation curves (data/curves/camels-cv-curves.json: the mean over the 27 boxes) by the project's own `compare_records`; each offset is split into
   what the definitions explain (the same box measured both ways) and how far this box lies from the mean of the 27 (the box-to-box scatter, from the stored per-box values).
5. One of the definition differences is tested directly: the stellar-to-halo mass ratio recomputed from the same file with the stellar mass of the whole subhalo instead of the one within twice the half-mass radius.

Usage:
  python3 scripts/derive_real_example.py PATH/camels-tng-cv0            print the report and the markdown table
  python3 scripts/derive_real_example.py PATH/camels-tng-cv0 --write    write tests/derive-cli/camels-tng-cv0-{derived,result}.json
  python3 scripts/derive_real_example.py --table                         print the markdown table from the committed result (what docs/DERIVE-REAL-CATALOGUE.md must contain)
Run it with `python3 -I` or from the repository root; the catalogue is data, never code."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import ingest_camels_galaxies as ing  # noqa: E402
import sim_highline as sh  # noqa: E402
import sim_highline_derive as sd  # noqa: E402

URL = "https://users.flatironinstitute.org/~camels/Sims/IllustrisTNG/CV/CV_0/groups_090.hdf5"
STATED = {"source": "CAMELS-TNG", "run": "CV_0", "imf": "chabrier03", "baryon_particle_mass": 1.89e7}
# initial gas element mass of CAMELS, 1.27e7 Msun/h (Villaescusa-Navarro et al. 2021, section 3), divided by h = 0.6711 as the file states it: 1.89e7 Msun
FAMILY = {"quenched": "qf", "size": "size", "shmr": "shmr", "bh": "bhms", "zstar": "zstar", "mzr": "mzr"}
LABEL = {"quenched": "quenched fraction", "size": "stellar size", "shmr": "stellar-to-halo mass ratio", "bh": "black-hole mass", "zstar": "stellar metallicity", "mzr": "gas metallicity"}
DERIVED = ROOT / "tests" / "derive-cli" / "camels-tng-cv0-derived.json"
RESULT = ROOT / "tests" / "derive-cli" / "camels-tng-cv0-result.json"
CURVES = ROOT / "data" / "curves" / "camels-cv-curves.json"
ENSEMBLE = ROOT / "data" / "ensembles" / "camels-galaxies.json"
MARK = ("<!-- result-table:start -->", "<!-- result-table:end -->")


def read_arrays(path):
    import h5py
    with h5py.File(path, "r") as h:
        hd = h["Header"].attrs
        head = {"z": float(hd["Redshift"]), "h": float(hd["HubbleParam"]), "box": float(hd["BoxSize"])}
        arr, sha = {}, hashlib.sha256()
        for grp, names in ing.ARRAYS.items():
            for n in names:
                arr[n] = h[f"{grp}/{n}"][:]
                sha.update(np.ascontiguousarray(arr[n]).tobytes())
        extra = {k: h[f"Subhalo/{k}"][:] for k in ("SubhaloSFRinRad",)}
    return arr, head, sha.hexdigest(), extra


def file_sha256(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def medians_of_binned(x, y, edges, min_count=10):
    """Plain-numpy median of y per bin of x (the rule the documentation states: bins of 0.2 dex, at least 10 galaxies); returns {bin centre: (median, count)}."""
    out = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (x >= lo) & (x < hi) & np.isfinite(y)
        if int(s.sum()) >= min_count:
            out[round((lo + hi) / 2, 3)] = (round(float(np.percentile(y[s], 50)), 4), int(s.sum()))
    return out


def independent(arr, head, extra, mbar):
    """The numbers derive reports, recomputed from the file without derive's code. Returns the count above the cut and the relations as {x: y}."""
    h, scale = head["h"], 1.0 / (1.0 + head["z"])
    ms_ap = arr["SubhaloMassInRadType"][:, 4] * 1e10 / h
    ms_tot = arr["SubhaloMassType"][:, 4] * 1e10 / h
    cut = 100 * mbar
    ok = (ms_ap >= cut) & (ms_ap > 0)
    lm = np.where(ms_ap > 0, np.log10(np.where(ms_ap > 0, ms_ap, 1.0)), np.nan)
    edges = np.arange(7.0, 12.6, 0.2)
    first = arr["GroupFirstSub"]
    cen = np.zeros(len(ms_ap), bool)
    cen[first[first >= 0]] = True
    m200 = arr["Group_M_Crit200"][arr["SubhaloGrNr"]] * 1e10 / h
    lmh = np.log10(np.where(m200 > 0, m200, np.nan))
    ssfr = np.where(ms_ap > 0, extra["SubhaloSFRinRad"] / np.where(ms_ap > 0, ms_ap, 1.0), 0.0)
    rh = arr["SubhaloHalfmassRadType"][:, 4] * scale / h
    bh = arr["SubhaloBHMass"] * 1e10 / h
    zs = arr["SubhaloStarMetallicity"] / 0.0127
    out = {"n": int(ok.sum())}
    q = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = ok & (lm >= lo) & (lm < hi)
        if int(s.sum()) >= 10:
            q[round((lo + hi) / 2, 3)] = (round(float(np.mean(ssfr[s] < 1e-11)), 4), int(s.sum()))
    out["quenched"] = q
    out["size"] = medians_of_binned(lm[ok], np.log10(np.where(rh > 0, rh, np.nan))[ok], edges)
    c = ok & cen
    shedges = np.arange(10.0, 15.2, 0.2)
    out["shmr"] = medians_of_binned(lmh[c], (lm - lmh)[c], shedges)
    cb = c & (bh > 0)
    out["bh"] = medians_of_binned(lm[cb], np.log10(np.where(cb, bh, np.nan))[cb], edges)
    zok = ok & (zs > 0)
    out["zstar"] = medians_of_binned(lm[zok], np.log10(np.where(zok, zs, np.nan))[zok], edges)
    # the same stellar-to-halo ratio with the stellar mass of the whole subhalo, with the cut applied to that mass
    ok_t = (ms_tot >= cut) & (ms_tot > 0)
    lt = np.where(ms_tot > 0, np.log10(np.where(ms_tot > 0, ms_tot, 1.0)), np.nan)
    ct = ok_t & cen
    out["shmr-total-mass"] = medians_of_binned(lmh[ct], (lt - lmh)[ct], shedges)
    return out


def points_of(record):
    return {round(p["x"], 3): (p["y"], p.get("count")) for p in record["representation"]["points"]}


def split_offsets(payload):
    """For each relation that has a stored CAMELS-TNG curve: what `compare` says, and the offset split into the definition part and the box part. All medians over the points of the overlap."""
    ens = json.loads(ENSEMBLE.read_text())
    box = ens["suites"]["IllustrisTNG"]["CV"]["CV_0"]["snaps"]["090"]["values"]
    curves = {r["id"]: r for r in json.loads(CURVES.read_text())["records"]}
    compared = {o["relation"]: o for o in sh.compare_records(payload["records"], relations=list(FAMILY))}
    rows = []
    for rel, fam in FAMILY.items():
        rec = next(r for r in payload["records"] if r["relation"] == rel)
        cid = f"camels-cv.tng.{rel}.z0"
        table = compared[rel]["table"]
        row = table[table["record_id"] == cid].iloc[0]
        entry = {"relation": rel, "label": LABEL[rel], "verdict": row["verdict"], "storedId": cid, "differences": [c.split(" (")[0] for c in list(row["blocker_list"]) + list(row["caveat_list"])]}
        entry["differenceText"] = list(row["blocker_list"]) + list(row["caveat_list"])
        if row["verdict"] == "not-comparable":
            entry.update({"nShared": None, "derivedMinusMean": None, "definitionPart": None, "boxPart": None, "boxScatter": None})
            rows.append(entry)
            continue
        dp = rec["representation"]["points"]
        dx, dy = np.array([p["x"] for p in dp]), np.array([p["y"] for p in dp])
        mp = curves[cid]["representation"]["points"]
        mx, my = np.array([p["x"] for p in mp]), np.array([p["y"] for p in mp])
        sd_ = np.array([(p["yHigh"] - p["yLow"]) / 2 for p in mp])
        edges = ens["m200ShmrEdges"] if rel == "shmr" else ens["mstarEdges"]
        cx = [round((a + b) / 2, 4) for a, b in zip(edges[:-1], edges[1:])]
        stored = {x: v for x, v in zip(cx, box[fam]) if v is not None}
        cxs = np.array([round(x, 4) for x in mx])
        have = np.array([float(x) in stored for x in cxs])
        c = np.array([stored[float(x)] for x in cxs[have]])
        sel = (dx >= mx[0]) & (dx <= mx[-1])
        m_i, s_i = np.interp(dx[sel], mx, my), np.interp(dx[sel], mx, sd_)
        c_i = np.interp(dx[sel], mx[have], c)
        total = float(np.median(dy[sel] - m_i))
        assert abs(total - row["median_dy"]) < 5e-4 and int(sel.sum()) == int(row["n_bins"]), (rel, total, row["median_dy"], int(sel.sum()), row["n_bins"])
        entry.update({"nShared": int(sel.sum()), "derivedMinusMean": round(total, 3), "definitionPart": round(float(np.median(dy[sel] - c_i)), 3),
                      "boxPart": round(float(np.median(c_i - m_i)), 3), "boxScatter": round(float(np.mean(s_i)), 3), "unit": rec["axes"]["yUnit"]})
        rows.append(entry)
    return rows


def run(folder):
    folder = Path(folder)
    assert folder.name == "camels-tng-cv0", "save the catalogue in a folder named camels-tng-cv0 (the folder's name is part of the record's notes, which the committed result reproduces)"
    path = folder / "groups_090.hdf5"
    arr, head, arrays_sha, extra = read_arrays(path)
    ens = json.loads(ENSEMBLE.read_text())
    stored = ens["suites"]["IllustrisTNG"]["CV"]["CV_0"]["snaps"]["090"]
    summary = ing.summarize(arr, head["z"], head["h"], head["box"])
    result = {"catalogue": {"url": URL, "bytes": path.stat().st_size, "sha256": file_sha256(path), "arraysSha256": arrays_sha,
                            "arraysMatchStored": arrays_sha == stored["arrays_sha256"], "perBoxSummaryMatchesStored": summary == stored["values"]}}
    payload = sd.derive_run("subfind", str(folder), **STATED)
    for r in payload["records"]:
        r["provenance"]["retrieved"] = "date of the run"
    result["derive"] = {"stated": STATED, "format": "subfind", "records": [r["id"] for r in payload["records"]], "report": list(payload.report),
                        "notes": next(r for r in payload["records"] if r["relation"] == "gsmf")["notes"]}
    ind = independent(arr, head, extra, STATED["baryon_particle_mass"])
    checks = {"galaxiesAboveCut": ind["n"]}
    for rel in ("quenched", "size", "shmr", "bh", "zstar"):
        rec = next(r for r in payload["records"] if r["relation"] == rel)
        got = {round(p["x"], 3): (p["y"], p["count"]) for p in rec["representation"]["points"]}
        checks[rel] = {"points": len(got), "agree": got == ind[rel]}
    result["independentRecomputation"] = checks
    result["comparison"] = split_offsets(payload)
    # the direct test of the mass definition on the stellar-to-halo ratio
    own = {round(p["x"], 3): p["y"] for p in next(r for r in payload["records"] if r["relation"] == "shmr")["representation"]["points"]}
    tot = {x: v[0] for x, v in ind["shmr-total-mass"].items()}
    shared = sorted(set(own) & set(tot))
    curve = next(r for r in json.loads(CURVES.read_text())["records"] if r["id"] == "camels-cv.tng.shmr.z0")["representation"]["points"]
    mx, my = np.array([p["x"] for p in curve]), np.array([p["y"] for p in curve])
    tx = np.array([x for x in shared if mx[0] <= x <= mx[-1]])
    result["massDefinitionTest"] = {"relation": "shmr", "points": len(tx),
                                    "apertureMinusTotal": round(float(np.median([own[x] - tot[x] for x in tx])), 3),
                                    "totalMinusMean": round(float(np.median([tot[x] - np.interp(x, mx, my) for x in tx])), 3),
                                    "apertureMinusMean": round(float(np.median([own[x] - np.interp(x, mx, my) for x in tx])), 3)}
    return payload, result


def fmt(v, signed=True):
    return "" if v is None else (f"{v:+.2f}" if signed else f"{v:.2f}")


def table(result):
    """The markdown table of docs/DERIVE-REAL-CATALOGUE.md, from the committed result."""
    lines = ["| Relation | What `compare` says | Offset: derived box minus the stored 27-box mean (median over the shared points; unit of the relation) | of which: the definitions (the same box measured both ways) | of which: this box against the mean of the 27 boxes | Scatter between the 27 boxes (1 SD) | Definitions that differ |",
             "|---|---|---|---|---|---|---|"]
    for r in result["comparison"]:
        if r["verdict"] == "not-comparable":
            lines.append(f"| {r['label']} | not comparable | not given | not given | not given | not given | " + "; ".join(r["differenceText"]).replace("|", "/") + " |")
            continue
        u = {"log10(Msun)": "dex", "log10(kpc)": "dex", "fraction": "fraction", "dex": "dex"}[r["unit"]]
        what = "comparable with caveats"
        lines.append(f"| {r['label']} | {what} | {fmt(r['derivedMinusMean'])} {u} | {fmt(r['definitionPart'])} | {fmt(r['boxPart'])} | {fmt(r['boxScatter'], False)} | " + "; ".join(r["differences"]) + " |")
    return "\n".join(lines)


def facts(result):
    """The checked facts as bullet lines, from the committed result."""
    c, i, m = result["catalogue"], result["independentRecomputation"], result["massDefinitionTest"]
    agree = [k for k in ("quenched", "size", "shmr", "bh", "zstar") if i[k]["agree"]]
    return "\n".join([
        f"- The file is {c['bytes']:,} bytes, SHA-256 `{c['sha256']}`. The hash of the arrays the ingest script reads from it, and the per-box summary computed from them, equal the values stored in `data/ensembles/camels-galaxies.json` for this box: {'yes' if c['arraysMatchStored'] and c['perBoxSummaryMatchesStored'] else 'NO'}.",
        f"- `derive` kept {i['galaxiesAboveCut']} galaxies above the resolution cut (100 baryon particle masses = 1.89e9 Msun of stellar mass within twice the half-mass radius).",
        f"- Separate plain-numpy code, written from the documented definitions and reading the same file, reproduces every point and count of {len(agree)} of the 5 relations that can be compared ({', '.join(agree)}): {'all agree to the last digit' if len(agree) == 5 else 'NOT ALL AGREE'}.",
        f"- Stellar-to-halo mass ratio recomputed with the stellar mass of the whole subhalo instead of the mass within twice the half-mass radius (cut and bins unchanged, {m['points']} shared points): the aperture version lies {m['apertureMinusTotal']:+.3f} dex from it, and the whole-subhalo version lies {m['totalMinusMean']:+.3f} dex from the stored 27-box mean (the offset of the aperture version is {m['apertureMinusMean']:+.3f} dex).",
    ])


def block(result):
    return table(result) + "\n\n" + facts(result)


def main(argv):
    if argv and argv[0] == "--table":
        print(block(json.loads(RESULT.read_text())))
        return 0
    if not argv:
        print(__doc__)
        return 2
    payload, result = run(argv[0])
    print(json.dumps({k: v for k, v in result.items() if k != "comparison"}, indent=1, ensure_ascii=False)[:3000])
    print(block(result))
    if "--write" in argv:
        DERIVED.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
        RESULT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {DERIVED.name} and {RESULT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
