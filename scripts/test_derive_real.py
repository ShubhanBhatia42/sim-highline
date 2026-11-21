"""Tests for the real-catalogue example of `sim-highline derive` (docs/DERIVE-REAL-CATALOGUE.md, scripts/derive_real_example.py, tests/derive-cli/camels-tng-cv0-*.json).

Offline: the committed records are valid; the checks recorded in the result hold; the offsets are those that `compare` and the stored CAMELS curves give today (so a change of rules or curves fails here and the
page has to be regenerated); the page contains exactly the generated table and its sentences about the numbers are true of them.
With SIMHL_CAMELS_CV0 set to the folder `camels-tng-cv0` (holding the downloaded groups_090.hdf5): the whole run is repeated on the file and must give the committed records and result again."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import derive_real_example as ex  # noqa: E402
import sim_highline_derive as sd  # noqa: E402

payload = json.loads(ex.DERIVED.read_text())
result = json.loads(ex.RESULT.read_text())
doc = (ROOT / "docs" / "DERIVE-REAL-CATALOGUE.md").read_text()

# ---- 1. the committed records are valid, the project's own validator accepts them, and they are what the stated command writes ----
assert sd.validate_records(payload["records"]) == [], sd.validate_records(payload["records"])
v = subprocess.run(["node", str(ROOT / "scripts" / "validate-curves.mjs"), str(ex.DERIVED)], capture_output=True, text=True, cwd=ROOT)
assert v.returncode == 0, "validate-curves rejects the committed records: " + v.stderr[-400:]
assert [r["id"] for r in payload["records"]] == result["derive"]["records"] and len(payload["records"]) == 9
assert result["derive"]["stated"] == ex.STATED, "the stated values in the result are the ones the script uses"
assert all(r["provenance"]["checksumSha256"] == result["catalogue"]["sha256"] for r in payload["records"]), "every record carries the hash of the catalogue file"
assert all(r["calibration"] == "unknown" and r["provenance"]["tier"] == "catalog-derived" for r in payload["records"])

# ---- 2. the checks recorded in the result ----
cat, ind = result["catalogue"], result["independentRecomputation"]
ens = json.loads(ex.ENSEMBLE.read_text())["suites"]["IllustrisTNG"]["CV"]["CV_0"]["snaps"]["090"]
assert cat["arraysMatchStored"] and cat["perBoxSummaryMatchesStored"] and cat["arraysSha256"] == ens["arrays_sha256"] and cat["bytes"] == ens["file_bytes"], "the file is the one the stored per-box summary was made from"
assert ind["galaxiesAboveCut"] == 304 and all(ind[k]["agree"] and ind[k]["points"] >= 6 for k in ("quenched", "size", "shmr", "bh", "zstar")), ind
counts = [p["count"] for r in payload["records"] if r["relation"] in ("quenched", "size", "shmr", "bh", "zstar") for p in r["representation"]["points"]]
assert min(counts) == 10 and max(counts) == 55, (min(counts), max(counts))
assert "1.89e+07 Msun (stated by you)" in result["derive"]["notes"] and "imf = chabrier03 (stated by you" in result["derive"]["notes"], "what was stated and what was read is in the notes"
assert result["derive"]["report"][0].startswith("z = 0 (snapshot 90), camels-tng-cv0: 304 galaxies above the cut") and "e-16" not in result["derive"]["report"][0], result["derive"]["report"]   # the header's z = 2.2e-16 is printed as 0

# ---- 3. the offsets are what compare and the stored curves give now ----
rows = ex.split_offsets(payload)
assert rows == result["comparison"], "the comparison changed (rules or stored curves): rerun scripts/derive_real_example.py on the catalogue and update the page\n" + json.dumps(rows)[:600]
by = {r["relation"]: r for r in rows}
assert [r["verdict"] for r in rows if r["relation"] != "mzr"] == ["comparable-with-caveats"] * 5 and by["mzr"]["verdict"] == "not-comparable"
assert any("metallicityQuantity: gas-O/H vs gas-metal-mass-fraction" in d for d in by["mzr"]["differences"]) and by["mzr"]["derivedMinusMean"] is None, "different quantities: no offset is given"
assert all("massDefinition: aperture-2rhalf-stars vs total-bound-subhalo" in by[k]["differences"] for k in ("quenched", "size", "shmr", "bh", "zstar"))
assert "bhMassMethod: intrinsic vs intrinsic-sum-of-bh-particles" in by["bh"]["differences"] and "population: centrals vs bh-hosts" in by["bh"]["differences"]

# ---- 4. the sentences of the page that put numbers to the table ----
ratio = {k: abs(by[k]["derivedMinusMean"]) / by[k]["boxScatter"] for k in ("quenched", "size", "shmr", "bh", "zstar")}
assert 2.5 <= ratio["shmr"] <= 3.5 and by["shmr"]["derivedMinusMean"] < 0 and abs(by["shmr"]["derivedMinusMean"] + 0.11) < 0.006 and abs(by["shmr"]["boxScatter"] - 0.04) < 0.005, ratio   # "0.11 dex below ... about three times the scatter (0.04 dex)"
m = result["massDefinitionTest"]
assert abs(m["totalMinusMean"]) < 0.01 and m["apertureMinusTotal"] < -0.1, m                                 # "brings it to within 0.01 dex"
assert 0.25 <= ratio["quenched"] <= 0.4 and 0.8 <= ratio["size"] <= 1.2, ratio                               # "about a third" / "about the same"
assert 2.2 <= ratio["zstar"] <= 2.8 and 1.5 <= ratio["bh"] <= 1.9, ratio                                      # "two and a half times" / "1.7 times"
assert all(abs(r["boxPart"]) <= 0.011 + 1e-9 and abs(r["boxPart"]) < r["boxScatter"] for r in rows if r["boxPart"] is not None), rows   # "0.011 or less ... smaller than the scatter"
curves = {r["id"]: r for r in json.loads(ex.CURVES.read_text())["records"]}
for k in ("quenched", "size", "bh", "zstar"):
    first_stored = curves[f"camels-cv.tng.{k}.z0"]["representation"]["points"][0]["x"]
    first_derived = next(r for r in payload["records"] if r["relation"] == k)["representation"]["points"][0]["x"]
    assert abs(first_derived - 9.3) < 1e-9 and abs(first_stored - 9.125) < 1e-9, (k, first_derived, first_stored)   # "10^9.3 where the stored ones start at 10^9.1"

# ---- 5. the page holds exactly the generated block, and says what it must ----
a, b = ex.MARK
assert a in doc and b in doc, "the page needs the result-table markers"
inside = doc.split(a, 1)[1].split(b, 1)[0]
assert inside.strip() == ex.block(result).strip(), "the page's table is not the generated one: run python3 scripts/derive_real_example.py --table and paste it between the markers"
for needle in ("curl -fLO https://users.flatironinstitute.org/~camels/Sims/IllustrisTNG/CV/CV_0/groups_090.hdf5", "--baryon-particle-mass 1.89e7", "One box, one snapshot, one code", "What this does not show",
               "No outside person has run it", "same person from the same documentation"):
    assert needle in doc, needle

# ---- 6. with the downloaded file: the whole run again ----
real = os.environ.get("SIMHL_CAMELS_CV0")
if real:
    p2, r2 = ex.run(real)
    assert r2 == result, "the run on the file differs from the committed result"
    assert p2 == payload, "the records written from the file differ from the committed ones"
    print("on the real file: records and result identical to the committed ones")
else:
    print("(SIMHL_CAMELS_CV0 is not set: the run on the downloaded file was not repeated; the committed result was checked)")
print(f"real-catalogue example tests passed: {len(payload['records'])} records, {ind['galaxiesAboveCut']} galaxies above the cut, "
      f"{sum(1 for r in rows if r['verdict'] != 'not-comparable')} comparisons, mass-definition test {m['apertureMinusTotal']:+.3f} dex")
