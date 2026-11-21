"""Tests of data/curves/camels-cv-curves.json (scripts/camels_cv_curves.py): every point is recomputed from the per-box values saved in data/ensembles/camels-galaxies*.json with separate code (plain Python, no numpy);
a bin is kept exactly when at least 14 of the 27 boxes have a value; the boxes all have the fiducial parameters; each record states every definition the comparison rules look at; the relations that must not be here
(the stellar mass function, which the pre-registered harmonization study would pick up as a new simulation source, and the star formation rate density, which the model-form study uses) are not; the checksums are those of the boxes used."""
import hashlib
import json
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
recs = json.loads((ROOT / "data" / "curves" / "camels-cv-curves.json").read_text())["records"]
ens = {"IllustrisTNG": json.loads((ROOT / "data" / "ensembles" / "camels-galaxies.json").read_text()), "Astrid": json.loads((ROOT / "data" / "ensembles" / "camels-galaxies-astrid.json").read_text())}
ens["SIMBA"] = ens["IllustrisTNG"]
SUITE = {"CAMELS-TNG": "IllustrisTNG", "CAMELS-SIMBA": "SIMBA", "CAMELS-Astrid": "Astrid"}
FAMILY = {"bh": "bhms", "shmr": "shmr", "size": "size", "zstar": "zstar", "mzr": "mzr", "quenched": "qf"}
SNAP = {0: "090", 0.95: "062", 2.15: "042", 3: "032", 4: "024"}
rules = json.loads(subprocess.run(["node", "-e", "const vm=require('vm'),fs=require('fs');const c={globalThis:{}};vm.runInNewContext(fs.readFileSync('compare.js','utf8'),c);console.log(JSON.stringify(c.globalThis.SimHighlineCompare.RULES))"],
                                  cwd=ROOT, capture_output=True, text=True, check=True).stdout)

assert recs, "no records"
assert len({r["id"] for r in recs}) == len(recs), "ids are unique"
assert {r["source"] for r in recs} == set(SUITE), {r["source"] for r in recs}
assert {r["relation"] for r in recs} == set(FAMILY), {r["relation"] for r in recs}
assert not {r["relation"] for r in recs} & {"gsmf", "sfrd", "smd", "hmf", "ssfr"}, "a relation that must not be here"
assert all(r["id"].startswith("camels-cv.") and r["kind"] == "simulation" and r["provenance"]["tier"] == "catalog-derived" and r["rankable"] for r in recs)

points_checked = 0
for r in recs:
    suite, fam, z = SUITE[r["source"]], FAMILY[r["relation"]], r["epoch"]["zRepresentative"]
    E = ens[suite]; snap = SNAP[z]
    boxes = E["suites"][suite]["CV"]
    assert len(boxes) == 27
    # the cosmic-variance boxes differ only in the random seed
    params = {json.dumps({k: v for k, v in b["params"].items()}, sort_keys=True) for b in boxes.values()}
    assert len(params) == 1, f"{suite}: the 27 boxes do not all have the fiducial parameters: {params}"
    names = sorted(boxes, key=lambda k: int(k.split("_")[1]))
    used = [n for n in names if boxes[n].get("snaps", {}).get(snap, {}).get("values")]
    edges = E["m200ShmrEdges"] if fam == "shmr" else E["mstarEdges"]
    centres = [round((a + b) / 2, 4) for a, b in zip(edges[:-1], edges[1:])]
    expect = {}
    for j, x in enumerate(centres):
        col = [boxes[n]["snaps"][snap]["values"][fam][j] for n in used]
        col = [v for v in col if v is not None]
        if len(col) >= 14:
            m, s = statistics.fmean(col), statistics.stdev(col)
            lo, hi = m - s, m + s
            if r["axes"]["yUnit"] == "fraction":
                lo, hi = max(0.0, lo), min(1.0, hi)
            expect[x] = (round(m, 4), round(lo, 4), round(hi, 4))
    got = {p["x"]: (p["y"], p["yLow"], p["yHigh"]) for p in r["representation"]["points"]}
    assert set(got) == set(expect), f"{r['id']}: bins {sorted(got)} against {sorted(expect)}"
    for x, v in got.items():
        assert all(abs(a - b) < 1.5e-4 for a, b in zip(v, expect[x])), f"{r['id']} x={x}: {v} against {expect[x]}"
        assert v[1] <= v[0] <= v[2], f"{r['id']} x={x}: the band must contain the mean"
        points_checked += 1
    sha = hashlib.sha256()
    for n in used:
        sha.update(boxes[n]["snaps"][snap]["arrays_sha256"].encode())
    assert r["provenance"]["checksumSha256"] == sha.hexdigest(), f"{r['id']}: checksum"
    # every definition the comparison rules look at is stated, and none is "unspecified"
    for k in rules[r["relation"]]["hard"] + rules[r["relation"]]["soft"]:
        assert r["definitions"].get(k) not in (None, "", "unspecified"), f"{r['id']}: definition {k} is not stated"
    assert r["axes"]["yUnit"] != "fraction" or all(0 <= p["yLow"] <= p["yHigh"] <= 1 for p in r["representation"]["points"]), f"{r['id']}: fractions stay in [0, 1]"
    if r["relation"] == "mzr":
        assert "Zsun" in r["axes"]["yDefinition"] and r["definitions"]["metallicityQuantity"] == "gas-metal-mass-fraction", f"{r['id']}: not the metal mass fraction of the Explorer's log Z/Zsun relation"
    # the stated range of boxes in the warning is the number actually used
    assert f"Mean over {len(used)} boxes" in r["selection"]["warning"], f"{r['id']}: the warning names the number of boxes"
assert points_checked >= 500, points_checked
# the mixed record counts: three sources, six relations, five snapshots at most
per = {}
for r in recs:
    per.setdefault(r["source"], set()).add((r["relation"], r["epoch"]["zRepresentative"]))
assert all(len(v) >= 25 for v in per.values()), {k: len(v) for k, v in per.items()}
print(f"CAMELS cosmic-variance curves: {len(recs)} records, {points_checked} points recomputed from the per-box values; 27 boxes with the fiducial parameters; definitions stated; checksums match")
