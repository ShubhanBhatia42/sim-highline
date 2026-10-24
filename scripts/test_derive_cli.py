"""Tests of `sim-highline derive` and `sim-highline compare run.json`: the tool recovers what the synthetic catalogues in tests/derive-cli/ were built with, writes records that pass the project's record checks,
refuses (with the option that settles it) every time a definition is neither stated nor in the file, never writes a file when it refuses, compares with the same rules as the website, and the four derive scripts
still write exactly what they wrote before their code moved (hashes in tests/derive-cli/script-output-hashes.json). A test here fails if the tool starts guessing a definition."""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    import numpy as np
    import pandas as pd  # noqa: F401
    import h5py
except ImportError as e:
    print(f"derive cli: skipped, {e.name} not installed")
    raise SystemExit(0)
import sim_highline as sh
import sim_highline_derive as sd

T = ROOT / "tests" / "derive-cli"
CLI = [sys.executable, str(ROOT / "sim_highline.py")]
BASE = dict(source="MySim", run="L25", imf="chabrier03", baryon_particle_mass=1e6)
SIZE = lambda x: 0.2 * (x - 10) + 0.5          # log10 radius injected by scripts/make_derive_fixtures.py
SUB, CAE, SOAP, EAG = T / "subfind", T / "caesar" / "m50n512_040.hdf5", T / "soap" / "halo_properties_0050.hdf5", T / "eagle" / "eagle-export.csv"
EAGLE_KW = dict(h=0.6777, omega_m=0.307, box_mpc=25.0, units="eagle-database", aperture="30pkpc")
TMP = Path(tempfile.mkdtemp(prefix="derive-cli-"))


def by_relation(payload, suffix=None):
    return {r["relation"]: r for r in payload["records"] if suffix is None or r["id"].split(".")[-2] == suffix}


def pts(rec):
    return rec["representation"]["points"]


def refuses(fmt, cat, *expect, **kw):
    """derive_run must raise UnderSpecified whose message names every string in `expect`."""
    try:
        sd.derive_run(fmt, cat, **{**BASE, **kw})
    except sd.UnderSpecified as e:
        for s in expect:
            assert s in str(e), f"refusal for {fmt} {kw} does not mention {s!r}:\n{e}"
        return e
    raise AssertionError(f"{fmt} with {kw} was accepted but must be refused (missing: {expect})")


def copy_of(src, name):
    dst = TMP / name
    (shutil.copytree if Path(src).is_dir() else shutil.copy)(src, dst)
    return dst


def h5_edit(path, fn):
    files = sorted(Path(path).rglob("*.hdf5")) if Path(path).is_dir() else [Path(path)]
    for f in files:
        with h5py.File(f, "r+") as h:
            fn(h)


# ---- 1. what each format recovers: the laws the fixtures were built with -------------------------------------------------------------------------------------------------------------------------
sub = sd.derive_run("subfind", SUB, **BASE)
r = by_relation(sub)
assert set(r) == {"gsmf", "sfms", "ssfr", "quenched", "size", "shmr", "bh", "zstar", "mzr"}, sorted(r)
box = 25000 / 1000 / 0.6774
n_tot = sum(p["count"] for p in pts(r["gsmf"]))
assert n_tot == 2000, n_tot
assert abs(sum(10 ** p["y"] * 0.2 for p in pts(r["gsmf"])) * box ** 3 - n_tot) / n_tot < 1e-3, "the mass function must integrate back to the galaxy count in the comoving box read from the header"
assert all(abs(p["y"] + 1.7) < 0.2 for p in pts(r["shmr"])), "halo-mass ratio"
assert all(abs(p["y"] - SIZE(p["x"])) < 0.05 for p in pts(r["size"])), "sizes in physical kpc"
assert abs(np.average([p["y"] for p in pts(r["quenched"])], weights=[p["count"] for p in pts(r["quenched"])]) - 0.3) < 0.03, "quenched fraction"
assert abs(pts(r["mzr"])[0]["y"] - (12 + math.log10(0.0074 / 16 / 0.74))) < 1e-3
g = r["gsmf"]
assert g["definitions"] == {"massDefinition": "aperture-2rhalf-stars", "imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "densityFrame": "comoving", "population": "all"}, g["definitions"]
assert all(x["calibration"] == "unknown" for x in sub["records"]), "calibration is not guessed"
assert g["provenance"]["tier"] == "catalog-derived" and g["provenance"]["url"].startswith("https://") and g["provenance"]["checksumSha256"] and g["id"] == "derived.mysim.l25.gsmf.all.z0"
tuned = sd.derive_run("subfind", SUB, **BASE, calibrated_on=["gsmf", "size"])
assert {x["relation"]: x["calibration"] for x in tuned["records"]}["gsmf"] == "target" and {x["relation"]: x["calibration"] for x in tuned["records"]}["shmr"] == "unknown"
assert any("--imf" in f for f in sub.facts) and any("read from" in f for f in sub.facts) and any("units" in f for f in sub.facts)

cae = sd.derive_run("caesar", CAE, **BASE)
r = by_relation(cae)
box = 50 / 0.68
assert abs(sum(10 ** p["y"] * 0.2 for p in pts(r["gsmf"])) * box ** 3 - 2000) < 2, "the box stays comoving at z = 2"
assert all(abs(p["y"] - SIZE(p["x"])) < 0.05 for p in pts(r["size"])), "kpccm/h radii become physical kpc at z = 2"
assert all(abs(p["y"] + 1.7) < 0.2 for p in pts(r["shmr"])) and all(abs(p["y"] + 1) < 1e-3 for p in pts(r["hi-fraction"]))
assert r["gsmf"]["definitions"]["massDefinition"] == "caesar-6dfof-galaxy-total" and r["gsmf"]["epoch"]["snapshot"] == 40 and r["gsmf"]["epoch"]["zRepresentative"] == 2.0

soap = sd.derive_run("soap", SOAP, **BASE, aperture="50kpc")
r = by_relation(soap)
assert abs(sum(10 ** p["y"] * 0.2 for p in pts(r["gsmf"])) * 50.0 ** 3 - 2000) < 2
assert all(abs(p["y"] + 1.7) < 0.2 for p in pts(r["shmr"])) and all(abs(p["y"] - SIZE(p["x"])) < 0.05 for p in pts(r["size"]))
assert r["gsmf"]["definitions"]["massDefinition"] == "aperture-50pkpc" and r["gsmf"]["definitions"]["cosmology"] == {"H0": 68.1, "Om": 0.306}

eag = sd.derive_run("eagle", EAG, **BASE, **EAGLE_KW, distributions=True)
assert sorted({x["epoch"]["zRepresentative"] for x in eag["records"]}) == [0.0, 1.0]
r0 = {x["relation"]: x for x in eag["records"] if x["epoch"]["zRepresentative"] == 0.0 and not x["id"].endswith(".dist.z0")}
assert all(abs(p["y"] + 1.7) < 0.2 for p in pts(r0["shmr"])) and all(abs(p["y"] - SIZE(p["x"])) < 0.05 for p in pts(r0["size"]))
assert r0["gsmf"]["definitions"]["massDefinition"] == "aperture-30pkpc"
dist = [x for x in eag["records"] if x["id"].endswith(".dist.z0")]
assert len(dist) == 1 and dist[0]["run"] == "L25 (per-galaxy distribution)" and "distribution" in dist[0]["representation"] and dist[0]["representation"]["distribution"]["summary"]["thresholds"] == [-11.0, -10.5]
assert not any(x["id"].endswith(".dist.z0") for x in sd.derive_run("eagle", EAG, **BASE, **EAGLE_KW)["records"]), "the distribution record is opt-in"

# ---- 2. the records pass the project's own checks: the tool's validator, the schema, and scripts/validate-curves.mjs (which also recomputes each distribution with compare.js) ------------------------------
for name, p in (("subfind", sub), ("caesar", cae), ("soap", soap), ("eagle", eag)):
    assert sd.validate_records(p["records"]) == [], (name, sd.validate_records(p["records"]))
    out = TMP / f"{name}.json"
    sd.write_payload(p, out)
    assert json.loads(out.read_text())["schemaVersion"] == "1.0.0"
    if shutil.which("node"):
        v = subprocess.run(["node", str(ROOT / "scripts" / "validate-curves.mjs"), str(out)], capture_output=True, text=True, cwd=ROOT)
        assert v.returncode == 0, f"validate-curves rejects the {name} records: {v.stderr[-400:]}"
try:
    import jsonschema
    schema = json.loads((ROOT / "schemas" / "curve-schema.json").read_text())
    for p in (sub, cae, soap, eag):
        jsonschema.validate({"schemaVersion": "1.0.0", "records": p["records"]}, schema)
except ImportError:
    pass
bad = json.loads(json.dumps(sub["records"]))
bad[0]["provenance"]["url"] = "http://example.org"
bad[1]["representation"]["points"][1]["x"] = bad[1]["representation"]["points"][0]["x"]
assert len(sd.validate_records(bad)) >= 2, "the tool's validator must catch a non-https source and a non-increasing x"
if shutil.which("node"):
    (TMP / "bad.json").write_text(json.dumps({"schemaVersion": "1.0.0", "records": bad}))
    assert subprocess.run(["node", str(ROOT / "scripts" / "validate-curves.mjs"), str(TMP / "bad.json")], capture_output=True, cwd=ROOT).returncode != 0

# ---- 3. refusals: each of these catalogues or statements is under-specified, and the tool must say so and say what to add ------------------------------------------------------------------------------------
e = sd.UnderSpecified
try:
    sd.derive_run("subfind", [])
    raise AssertionError("nothing given must be refused")
except e as err:
    assert len(err.problems) >= 4, err.problems       # every problem at once, not the first one
    msg = str(err)
    for flag in ("--catalog", "--source", "--imf", "--baryon-particle-mass"):
        assert flag in msg, flag
    assert "Nothing was written" in msg
refuses("subfind", SUB, "--imf", imf=None)
refuses("subfind", SUB, "--baryon-particle-mass", baryon_particle_mass=None)
refuses("subfind", SUB, "--source", source=None)
refuses("subfind", SUB, "chabrier03", imf="Chabrier")
refuses("subfind", SUB, "H0 / 100", h=67.74)
refuses("subfind", TMP / "does-not-exist", "does not exist")
refuses("nope", SUB, "not one of")
refuses("subfind", SUB, "calibrated-on", calibrated_on=["gsmf", "nonsense"])

# Subfind: the file must say its units and cosmology, or you must
d = copy_of(SUB, "sub-nounits")
h5_edit(d, lambda h: h.__delitem__("Parameters"))
refuses("subfind", d, "--units illustris")
ok = sd.derive_run("subfind", d, **BASE, units="illustris")
assert any("--units illustris" in f for f in ok.facts), "a stated units convention is recorded as stated"
refuses("subfind", d, "units", units="tng")
d = copy_of(SUB, "sub-wrongunits")
h5_edit(d, lambda h: h["Parameters"].attrs.__setitem__("UnitLength_in_cm", 3.085678e24))
refuses("subfind", d, "UnitLength_in_cm")
d = copy_of(SUB, "sub-noh")
h5_edit(d, lambda h: h["Header"].attrs.__delitem__("HubbleParam"))
refuses("subfind", d, "--h")
assert sd.derive_run("subfind", d, **BASE, h=0.6774)["records"][0]["definitions"]["cosmology"]["H0"] == 67.74
refuses("subfind", SUB, "you stated 0.7", h=0.7)
assert sd.derive_run("subfind", SUB, **BASE, h=0.6774), "a statement that agrees with the file is accepted"
d = copy_of(SUB, "sub-nobox")
h5_edit(d, lambda h: h["Header"].attrs.__delitem__("BoxSize"))
refuses("subfind", d, "--box-mpc")
refuses("subfind", SUB, "you stated 30", box_mpc=30.0)
d = copy_of(SUB, "sub-noom")
h5_edit(d, lambda h: h["Header"].attrs.__delitem__("Omega0"))
refuses("subfind", d, "--omega-m")
d = copy_of(SUB, "sub-nonflat")
h5_edit(d, lambda h: h["Header"].attrs.__setitem__("OmegaLambda", 0.5))
refuses("subfind", d, "flat")
d = copy_of(SUB, "sub-nosfr")
h5_edit(d, lambda h: h["Subhalo"].__delitem__("SubhaloSFRinRad"))
refuses("subfind", d, "SubhaloSFRinRad")
d = copy_of(SUB, "sub-noflag")
h5_edit(d, lambda h: h["Subhalo"].__delitem__("SubhaloFlag"))
nf = sd.derive_run("subfind", d, **BASE)
assert "not excluded" in nf["records"][0]["selection"]["warning"], "a missing SubhaloFlag is stated in the record, not hidden"

# CAESAR: Omega_m has no silent default (the script's 0.3 is not applied), nor has h, a unit, a box unit or a halo mass that is not M200crit
d = copy_of(CAE, "noom_040.hdf5")
h5_edit(d, lambda h: h["simulation_attributes"].attrs.__delitem__("omega_matter"))
refuses("caesar", d, "--omega-m")
assert sd.derive_run("caesar", d, **BASE, omega_m=0.3)["records"][0]["definitions"]["cosmology"]["Om"] == 0.3
d = copy_of(CAE, "noh_040.hdf5")
h5_edit(d, lambda h: h["simulation_attributes"].attrs.__delitem__("hubble_constant"))
refuses("caesar", d, "--h")
d = copy_of(CAE, "unit_040.hdf5")
h5_edit(d, lambda h: h["galaxy_data"]["sfr"].attrs.__setitem__("unit", b"Msun/Myr"))
refuses("caesar", d, "refusing to guess")
d = copy_of(CAE, "boxunit_040.hdf5")
h5_edit(d, lambda h: h["simulation_attributes"].attrs.__setitem__("boxsize_units", b"furlong"))
refuses("caesar", d, "not recognised")
d = copy_of(CAE, "m200_040.hdf5")
h5_edit(d, lambda h: h["halo_data"].move("dicts/masses.m200c", "dicts/masses.m200"))
refuses("caesar", d, "M200crit")
d = copy_of(CAE, "mysim.hdf5")
refuses("caesar", d, "--snapshot")
assert sd.derive_run("caesar", d, **BASE, snapshot=40)["records"][0]["epoch"]["snapshot"] == 40
refuses("caesar", CAE, "you stated 0.7", h=0.7)

# SOAP: the aperture is a choice the file cannot make for you; units come from the file's own conversion attributes
refuses("soap", SOAP, "--aperture")
refuses("soap", SOAP, "ExclusiveSphere/100kpc", "30kpc", "50kpc", aperture="100kpc")
refuses("soap", SOAP, "50kpc", aperture="fifty")
d = copy_of(SOAP, "nocosmo_0050.hdf5")
h5_edit(d, lambda h: h.__delitem__("Cosmology"))
refuses("soap", d, "--h", "--omega-m", aperture="50kpc")
assert sd.derive_run("soap", d, **BASE, aperture="50kpc", h=0.681, omega_m=0.306)
d = copy_of(SOAP, "nounits_0050.hdf5")
h5_edit(d, lambda h: h["ExclusiveSphere/50kpc/StellarMass"].attrs.__delitem__("Conversion factor to physical CGS (including cosmological corrections)"))
refuses("soap", d, "refusing to guess units", aperture="50kpc")
d = copy_of(SOAP, "smallbox_0050.hdf5")
h5_edit(d, lambda h: h["Header"].attrs.__setitem__("BoxSize", np.array([5.0, 5.0, 5.0])))
refuses("soap", d, "--box-mpc", aperture="50kpc")
assert sd.derive_run("soap", d, **BASE, aperture="50kpc", box_mpc=5.0)
refuses("soap", SOAP, "you stated 0.7", aperture="50kpc", h=0.7)

# EAGLE table: a table of numbers carries no units, cosmology, box or aperture
refuses("eagle", EAG, "--units eagle-database", **{k: v for k, v in EAGLE_KW.items() if k != "units"})
refuses("eagle", EAG, "--h", **{k: v for k, v in EAGLE_KW.items() if k != "h"})
refuses("eagle", EAG, "--omega-m", **{k: v for k, v in EAGLE_KW.items() if k != "omega_m"})
refuses("eagle", EAG, "--box-mpc", **{k: v for k, v in EAGLE_KW.items() if k != "box_mpc"})
refuses("eagle", EAG, "--aperture 30pkpc", **{k: v for k, v in EAGLE_KW.items() if k != "aperture"})
refuses("eagle", EAG, "30 pkpc", **{**EAGLE_KW, "aperture": "50pkpc"})
try:
    sd.derive_run("eagle", EAG, **{**BASE, "baryon_particle_mass": 1e5}, **EAGLE_KW)
    raise AssertionError("a table that stops above the resolution cut must be refused")
except e as err:
    assert "not complete down to the cut" in str(err)
d = TMP / "eagle-nocol.csv"
d.write_text("\n".join(l for l in EAG.read_text().splitlines()).replace("Mass_Star", "Mstar"))
refuses("eagle", d, "lacks the columns", **EAGLE_KW)

# a file that is not the catalogue it is said to be is a refusal with a message, not a traceback
refuses("caesar", ROOT / "README.md", "could not be read as a caesar catalogue")
d = copy_of(SOAP, "nocentral_0050.hdf5")
h5_edit(d, lambda h: h["InputHalos"].__delitem__("IsCentral"))
refuses("soap", d, "could not be read as a soap catalogue", aperture="50kpc")
d = TMP / "sub-notfile"
(d / "groups_099").mkdir(parents=True)
(d / "groups_099" / "groups_099.hdf5").write_text("this is not an HDF5 file")
refuses("subfind", d, "could not be read as a subfind catalogue")

# a mixture of catalogues with different cosmologies is not one run
d = copy_of(SOAP, "halo_properties_0051.hdf5")
h5_edit(d, lambda h: (h["Cosmology"].attrs.__setitem__("h", [0.7]), h["Header"].attrs.__setitem__("Redshift", [1.0])))
refuses("soap", [SOAP, d], "disagree", aperture="50kpc")

# ---- 4. the command line: exit code 2 and no file on a refusal, 0 and a valid file otherwise -------------------------------------------------------------------------------------------------------------
out = TMP / "cli-run.json"
argv = CLI + ["derive", "--format", "subfind", "--catalog", str(SUB), "--source", "MySim", "--run", "L25", "--baryon-particle-mass", "1e6", "--out", str(out)]
x = subprocess.run(argv, capture_output=True, text=True)
assert x.returncode == 2 and "refusing to guess" in x.stderr and "--imf" in x.stderr and not out.exists(), (x.returncode, x.stderr[-300:])
x = subprocess.run(argv + ["--imf", "chabrier03"], capture_output=True, text=True)
assert x.returncode == 0 and out.exists() and "9 records written" in x.stdout and "stated by you" in x.stdout and "read from" in x.stdout, x.stdout[-500:] + x.stderr[-300:]
assert len(json.loads(out.read_text())["records"]) == 9
x = subprocess.run(argv[:-1] + [str(TMP / "cli-run2.json"), "--imf", "chabrier03", "--compare", "--top", "1"], capture_output=True, text=True)
assert x.returncode == 0 and "gsmf at z = 0" in x.stdout and "sfms at z = 0" in x.stdout and "yours minus theirs" in x.stdout, "derive --compare goes from the catalogue to the comparison in one command: " + x.stdout[-300:] + x.stderr[-300:]
x = subprocess.run(CLI + ["derive", "--format", "eagle", "--catalog", str(EAG), "--source", "S", "--run", "R", "--imf", "kroupa01", "--baryon-particle-mass", "1e6", "--out", str(TMP / "no.json")], capture_output=True, text=True)
assert x.returncode == 2 and not (TMP / "no.json").exists() and all(f in x.stderr for f in ("--units eagle-database", "--h", "--omega-m", "--box-mpc", "--aperture")), x.stderr

# ---- 5. compare run.json: same rules as the website, plain reasons ----------------------------------------------------------------------------------------------------------------------------------------
df = sh.load()
recs = json.loads(out.read_text())["records"]
res = {c["relation"]: c for c in sh.compare_records(recs, ["sfms"], df=df)}["sfms"]["table"]
assert set(res["verdict"]) <= {"comparable", "comparable-with-caveats", "not-comparable"} and {"blocker_list", "caveat_list"} <= set(res.columns) and len(res) >= 5
direct = sh.compare_run([p["x"] for p in pts(recs[1])], [p["y"] for p in pts(recs[1])], "sfms", 0.0, definitions=recs[1]["definitions"], df=df)
assert list(res["record_id"]) == list(direct["record_id"]) and list(res["verdict"]) == list(direct["verdict"]), "compare run.json must give compare_run's verdicts, not its own"
txt = subprocess.run(CLI + ["compare", str(out), "--relation", "sfms", "--relation", "gsmf"], capture_output=True, text=True)
assert txt.returncode == 0 and "sfms at z = 0" in txt.stdout and "gsmf at z = 0" in txt.stdout and "ssfr at z" not in txt.stdout, txt.stderr[-300:]
assert "observations:" in txt.stdout and "simulations:" in txt.stdout and "yours minus theirs" in txt.stdout and "Most common reasons" in txt.stdout
assert "differs" in txt.stdout, "a different population is reported in words"
allrel = subprocess.run(CLI + ["compare", str(out)], capture_output=True, text=True)
assert allrel.returncode == 0 and all(f"{rel} at z = 0" in allrel.stdout for rel in ("gsmf", "sfms", "ssfr", "quenched", "size", "shmr", "bh"))
bad = subprocess.run(CLI + ["compare", str(out), "--relation", "uvlf"], capture_output=True, text=True)
assert bad.returncode != 0 and "no record of relation uvlf" in bad.stderr
bad = subprocess.run(CLI + ["compare", str(out), "--z", "0.1"], capture_output=True, text=True)
assert bad.returncode != 0 and "curve files only" in bad.stderr
(TMP / "notrecords.json").write_text('{"a": 1}')
bad = subprocess.run(CLI + ["compare", str(TMP / "notrecords.json")], capture_output=True, text=True)
assert bad.returncode != 0 and "not a file of records" in bad.stderr

# a missing definition is reported as such, in words, and blocks what the rules say it must block (population is a hard key of sfms and size on the website)
nopop = json.loads(json.dumps(recs))
for rec in nopop:
    rec["definitions"].pop("population", None)
(TMP / "nopop.json").write_text(json.dumps({"schemaVersion": "1.0.0", "records": nopop}))
txt = subprocess.run(CLI + ["compare", str(TMP / "nopop.json"), "--relation", "sfms"], capture_output=True, text=True).stdout
assert "population not documented" in txt and "your records do not state it" in txt and "0 fair to compare" in txt, txt[-900:]
sfms = {c["relation"]: c for c in sh.compare_records(nopop, ["sfms"], df=df)}["sfms"]["table"]
assert (sfms["verdict"] != "comparable").all() and sfms["blocker_list"].apply(lambda b: any(i == "population not documented" for i in b)).all()
reason = sh.plain_reason("population not documented", {}, "MySim L25", sh.rules(df.attrs.get("base")))
assert reason.startswith("population not documented") and "your records do not state it" in reason
assert "the published curve does not state it" in sh.plain_reason("population not documented", {"population": "all"}, "MySim L25", sh.rules(df.attrs.get("base")))

# offsets are yours minus theirs, and a curve compared with its own copy shifted by +0.1 comes back +0.1 (checked on a real record of the dataset, not on this tool's output)
rec = next(r for r in json.loads((ROOT / "data" / "export" / "sim-highline-records.json").read_text())["records"]
           if r["relation"] == "sfms" and r["kind"] == "simulation" and r["representation"]["type"] == "points" and r["rankable"] and len(r["representation"]["points"]) >= 6 and r["definitions"].get("population"))
me = json.loads(json.dumps(rec))
me.update(id="mine.copy", source="Copy", run="shifted")
for p in me["representation"]["points"]:
    p["y"] = round(p["y"] + 0.1, 6)
    p.pop("yLow", None), p.pop("yHigh", None)
me["representation"]["intervalKind"] = "unspecified"
table = sh.compare_records([me], df=df)[0]["table"]
row = table[table["record_id"] == rec["id"]].iloc[0]
assert row["verdict"] in ("comparable", "comparable-with-caveats") and abs(row["median_dy"] - 0.1) < 1e-6 and row["n_bins"] >= 3, row.to_dict()

# ---- 6. the four derive scripts write what they always wrote (sha256 of the output, retrieval date masked) -----------------------------------------------------------------------------------------------
hashes = json.loads((T / "script-output-hashes.json").read_text())
stub_dir = TMP / "stub"
stub_dir.mkdir()
(stub_dir / "eagleSqlTools.py").write_text('''import numpy as np
import pandas as pd


def connect(user, password=None):
    return object()


def execute_query(con, query):
    snap = int(query.split("SnapNum = ")[1].split()[0])
    d = pd.read_csv(%r, comment="#")
    d = d[d["SnapNum"] == snap]
    if not len(d):
        return None
    dt = [("GalaxyID", "i8"), ("SnapNum", "i4"), ("Redshift", "f8"), ("SubGroupNumber", "i4"), ("Mass_Star", "f8"), ("SFR", "f8"), ("Mass_BH", "f8"), ("R_halfmass30", "f8"), ("Group_M_Crit200", "f8")]
    a = np.zeros(len(d), dtype=dt)
    for k, _ in dt:
        a[k] = d[k].to_numpy()
    return a
''' % str(EAG))
for case in hashes["cases"]:
    dst = TMP / ("script-" + case["out"])
    args = [a.replace("{fx}", str(T)) for a in case["args"]]
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / case["script"]), *args, "--out", str(dst)], capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(stub_dir)})
    assert run.returncode == 0, (case["script"], run.stderr[-400:])
    text = re.sub(r'"retrieved": "\d{4}-\d{2}-\d{2}"', '"retrieved": "DATE"', dst.read_text())
    assert hashlib.sha256(text.encode()).hexdigest() == case["sha256"], f"{case['script']} no longer writes what it wrote before its code moved into sim_highline_derive.py (hashes in tests/derive-cli/script-output-hashes.json)"
    assert len(json.loads(text)["records"]) == case["records"]

shutil.rmtree(TMP, ignore_errors=True)
print("derive cli: OK (4 formats recovered, records valid, every under-specified input refused, compare reuses the website rules, 4 scripts unchanged)")
