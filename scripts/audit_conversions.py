"""What has been changed in the data, counted from the data themselves.

Writes data/analysis/conversions-audit.json and docs/DATA-CHANGES.md.

Two parts:
  1. Counts from the records' own text (the warning, notes and axis definitions each record carries): exact re-expressions of the plotted numbers, and the one h conversion this project made itself. These need nothing else and are checked by `--check`.
  2. What the third-party comparison-data compilation (VELOCIraptor/SWIFT) did to the 173 observation curves it supplies, read from its per-dataset conversion scripts. This needs a clone of that repository at the commit the records name: `python3 scripts/audit_conversions.py /path/to/velociraptor-comparison-data`. Without a clone the committed numbers are kept.

Usage: python3 scripts/audit_conversions.py [clone] | --check"""
import glob
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "analysis" / "conversions-audit.json"
DOC = ROOT / "docs" / "DATA-CHANGES.md"

# (key, plain label, pattern over the record's own text). Each is an exact re-expression of what the source plots.
EXACT = [
    ("timeToRedshift", "cosmic time on the x axis turned into redshift (flat LCDM age relation)", r"each time is converted to redshift"),
    ("log1pz", "an x axis of log10(1+z) turned into redshift", r"axis is log10\(1\+z\)"),
    ("perGyr", "a specific star formation rate per Gyr turned into per year", r"Gyr\^-1[^.]{0,40}converted|converted from /Gyr|axis in Gyr\^-1, converted"),
    ("ratio", "a stellar-to-halo (or stellar-to-baryon) mass ratio built or rescaled from the plotted quantities", r"converted (here )?by (subtracting|adding)|converted from the plotted ratio|Plotted M\* converted to the M\*/M"),
    ("perDex", "a density per unit mass ratio turned into per dex", r"the record converts to per dex|converted from per-dM"),
    ("uvUnits", "a UV luminosity or density turned into absolute magnitude or per magnitude", r"51\.595|per dex to per magnitude|log10\(0\.4\)"),
    ("errorsToLog", "published linear error bars turned into dex", r"(errors?|sigma|uncertaint\w*)[^.]{0,80}converted to log"),
    ("gasFractionTransform", "a gas fraction f turned into gas-to-stellar mass ratio, log10(f/(1-f))", r"log10\(f/\(1-f\)\)"),
    ("displayOffset", "a display offset the figure added to each redshift taken out again", r"offset was added back"),
]
OWN_H = ("hDensities", r"densities converted with h=([0-9]+\.?[0-9]*)")


def record_text(r):
    return " ".join([str(r["selection"].get("warning", "")), str(r.get("notes", "")), json.dumps(r["axes"])])


def load_records():
    out = []
    for f in sorted(glob.glob(str(ROOT / "data" / "curves" / "*.json"))):
        out += json.load(open(f))["records"]
    return out


def count_records(records):
    exact = {}
    for key, label, pat in EXACT:
        hits = [r for r in records if re.search(pat, record_text(r), re.I)]
        exact[key] = {"label": label, "records": len(hits), "bySource": dict(Counter(r["source"] for r in hits).most_common(8))}
    hits = [r for r in records if re.search(OWN_H[1], record_text(r), re.I)]
    h = {"records": len(hits), "sources": sorted({r["source"] for r in hits}), "h": sorted({re.search(OWN_H[1], record_text(r)).group(1) for r in hits})}
    fills = json.load(open(ROOT / "data" / "definition-fills.json"))
    filled = sum(1 for r in records if r["provenance"].get("definitionFills"))
    corr = [l for l in (ROOT / "docs" / "CORRECTIONS.md").read_text().splitlines() if l.startswith("| ") and not l.startswith("| release") and not l.startswith("|---")]
    cmp_js = (ROOT / "compare.js").read_text()
    imf = {k: float(v) for k, v in re.findall(r"(\w+):(-?[0-9.]+)", re.search(r"const IMF_DEX=\{(.*?)\}", cmp_js).group(1))}
    return {"records": len(records), "exactReexpressions": exact, "ownHConversion": h,
            "definitionFills": {"rules": len(fills["fills"]), "records": filled, "papersReadWithoutResult": len({x["arxiv"] for x in fills["readWithoutResult"]})},
            "correctionsLogged": len(corr), "onScreenImfOffsetsDex": {"kroupa01": imf["kroupa01"], "chabrier03": imf["chabrier03"], "salpeter55": imf["salpeter55"]}}


def audit_compilation(clone, records):
    """Classify the observation curves taken from the comparison-data compilation by what its conversion script applies."""
    base = Path(clone) / "data"
    scripts = glob.glob(str(base / "*" / "conversion" / "*.py"))
    cosmo = (Path(clone) / "cosmology.py").read_text()
    factors = {k: float(v) for k, v in re.findall(r"(kroupa_to_chabrier_mass|salpeter_to_chabrier_mass)\s*=\s*([0-9.]+)", cosmo)}
    outmap = {}
    for p in scripts:
        t = open(p).read()
        for m in re.finditer(r"output_filename\s*=\s*(?:f?\"([^\"]+)\"|f?'([^']+)')", t):
            outmap.setdefault(os.path.basename(os.path.dirname(os.path.dirname(p))) + "/" + (m.group(1) or m.group(2)), []).append(p)

    def find(sm):
        d, bn = sm.split("/")[1], os.path.basename(sm)
        if d + "/" + bn in outmap:
            return outmap[d + "/" + bn][0]
        pref = re.match(r"[A-Za-z]+\d{4}", bn)
        c = [p for p in scripts if "/" + d + "/" in p and pref and pref.group(0).lower() in os.path.basename(p).lower()]
        return c[0] if c else None

    tally = Counter(); imf_sets = {}
    for r in records:
        pr = r["provenance"]
        if "velociraptor" not in str(pr.get("compilation", "")).lower():
            continue
        tally["records"] += 1
        p = find(pr["sourceMember"])
        if not p:
            tally["notTraced"] += 1
            continue
        t = open(p).read()
        imf = re.search(r"(kroupa|salpeter)_to_chabrier", t)
        h = bool(re.search(r"h_sim|h_obs|cosmology\.h", t)) and not re.search(r"no h-?correction", t, re.I)
        tally["hCorrected"] += h
        if imf:
            tally["imfConverted"] += 1
            imf_sets.setdefault(os.path.basename(p), {"from": imf.group(1).capitalize(), "records": 0, "recordImf": Counter()})
            imf_sets[os.path.basename(p)]["records"] += 1
            imf_sets[os.path.basename(p)]["recordImf"][str(r["definitions"].get("imf"))] += 1
        if not h and not imf:
            tally["noConversion"] += 1
    return {"repo": "https://github.com/calvin-sykes/velociraptor-comparison-data", "commit": next((r["provenance"]["compilation"].split("@")[-1].strip() for r in records if "velociraptor" in str(r["provenance"].get("compilation", "")).lower()), None),
            "cosmology": "Planck15", "factors": factors, "records": tally["records"], "hCorrected": tally["hCorrected"], "imfConverted": tally["imfConverted"], "noConversion": tally["noConversion"], "notTraced": tally["notTraced"],
            "imfConvertedDatasets": {k.replace("convert", "").replace(".py", ""): {"from": v["from"], "records": v["records"], "recordImf": dict(v["recordImf"])} for k, v in sorted(imf_sets.items())}}


def render(a):
    ex, c, h, f = a["exactReexpressions"], a["compilation"], a["ownHConversion"], a["definitionFills"]
    off = a["onScreenImfOffsetsDex"]
    sal, kro = off["chabrier03"] - off["salpeter55"], off["chabrier03"] - off["kroupa01"]  # dex added to a stellar mass to express it in a Chabrier IMF
    L = ["# What has been changed in the data, and what has not", "",
         "Generated by `scripts/audit_conversions.py`; do not edit by hand. The numbers are counted from the records themselves and from the conversion scripts of the one compilation we ingest.", "",
         "## The short answer", "",
         f"**The simulation curves are stored as their authors published them.** Nothing has been corrected for the initial mass function (IMF), the stellar-mass aperture, which galaxies are counted, dust or the cosmology: where two curves differ in those, the difference is recorded and flagged, not removed. What we did change is only the way numbers are written (sections 1 and 2) and the fixes in section 5; the observation curves that came through a compilation carry that compilation's own conversions (section 3). Each change is also written in the warning of every record it touches.", "",
         "## 1. Same numbers, written in the axis units we use (exact, no physics)", "",
         "Where a paper plots an equivalent axis, the record converts it exactly and says so in its warning. Counts are records whose own text states the conversion.", "",
         "| what | records | mainly |", "|---|---|---|"]
    for k, v in ex.items():
        L.append(f"| {v['label']} | {v['records']} | {', '.join(v['bySource'])} |")
    L += ["", "## 2. The one cosmology conversion we made ourselves", "",
          f"{h['records']} curves ({', '.join(h['sources'])}): the released mass functions are densities in units that carry h, converted with h = {', '.join(h['h'])} (the simulation's own value, so the curve stays in the run's own cosmology and is not moved to another one).", "",
          "## 3. What the compilation we ingest did, before we received the numbers", "",
          f"{c['records']} observation curves come from the SWIFT/VELOCIraptor comparison-data compilation ([{c['repo'].split('github.com/')[1]}]({c['repo']}), commit `{(c['commit'] or '')[:7]}`). Its scripts re-express each published table in its own conventions. From reading those scripts:", "",
          f"- {c['hCorrected']} of the {c['records']} are corrected for h to a {c['cosmology']} cosmology (the observers' own h is replaced by the compilation's).",
          f"- {c['imfConverted']} of them also have their stellar masses converted to a Chabrier IMF by the compilation (Kroupa to Chabrier: mass times {c['factors'].get('kroupa_to_chabrier_mass')}, {math_dex(c['factors'].get('kroupa_to_chabrier_mass')):+.3f} dex; Salpeter to Chabrier: times {c['factors'].get('salpeter_to_chabrier_mass')}, {math_dex(c['factors'].get('salpeter_to_chabrier_mass')):+.3f} dex): " + "; ".join(f"{k} (from {v['from']}, {v['records']} curve{'s' if v['records'] != 1 else ''})" for k, v in c["imfConvertedDatasets"].items()) + ".",
          f"- {c['noConversion']} are taken as published and {c['notTraced']} come from a file whose script could not be matched.",
          "", "We keep these values as the compilation made them and record Chabrier IMF and Planck15 as their definitions. We did not re-derive them from the original papers; to check one, the record's `provenance.sourceMember` names the compilation file and its warning quotes the compilation's own note.", "",
          "## 4. An optional switch on screen", "",
          f"The Explorer can shift the stellar-mass and SFR axes of simulation curves to a Chabrier IMF (Kroupa {kro:+.3f} dex, Salpeter {sal:+.3f} dex). It is off by default, labelled in the legend, the evidence panel and exported figures when on, never applied to curves whose IMF is not stated, and **downloads and the Python loader always hold the published values**. These offsets are population averages (uncertain at about 0.02 dex) and are the same factors the compilation applied in section 3 (data/imf-offsets.json; the Explorer used slightly different, undocumented values until 2026-10-18, and the two registered studies keep the offsets they were registered with).", "",
          "## 5. Mistakes we fixed", "",
          f"{a['correctionsLogged']} fixes to data, analyses or claims are listed, with the release each was made in, in [CORRECTIONS.md](CORRECTIONS.md).", "",
          "## 6. Definitions added from the papers", "",
          f"{f['records']} simulation records carry at least one definition (for example the stellar-mass aperture) that the table or figure left unstated and the source paper states ({f['rules']} sourced rules in `data/definition-fills.json`, each with paper, section, a short quote and the SHA-256 of the arXiv source read). A stated value is never overwritten. {f['papersReadWithoutResult']} papers were read for a definition and do not state it (listed on the Methods page); those values stay unspecified.", "",
          "## What the analyses do with this", "",
          "- The harmonisation study applies IMF offsets and aperture maps inside its own calculation, to test whether matching definitions closes the gap between simulated mass functions. It changes no stored curve.",
          "- The definition-budget analysis measures how large definition differences are. It corrects no curve.",
          "- The dials page uses the CAMELS simulations as measured (every CAMELS code is measured the same way, so no conversion is needed between them). The published and observed curves drawn on it are not adjusted to the CAMELS definitions; the page says so.",
          "- Check your run does not convert your numbers. It tells you which of your definitions differ from each curve's.", ""]
    return "\n".join(L)


def math_dex(x):
    import math
    return math.log10(x) if x else 0.0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    records = load_records()
    fresh = count_records(records)
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    if "--check" in sys.argv:
        for k in fresh:
            if old.get(k) != fresh[k]:
                print(f"conversions audit: '{k}' differs from the committed file; run scripts/audit_conversions.py and commit the result"); print(" committed:", json.dumps(old.get(k))[:300]); print(" now:      ", json.dumps(fresh[k])[:300]); sys.exit(1)
        print("conversions audit: the counts in data/analysis/conversions-audit.json match the records"); return
    if args:
        fresh["compilation"] = audit_compilation(args[0], records)
    elif "compilation" in old:
        fresh["compilation"] = old["compilation"]
    else:
        sys.exit("no committed compilation numbers; pass the path of a clone of the comparison-data repository")
    OUT.write_text(json.dumps(fresh, indent=1) + "\n")
    DOC.write_text(render(fresh))
    c = fresh["compilation"]
    print(f"conversions audit: {sum(v['records'] for v in fresh['exactReexpressions'].values())} exact re-expressions counted; compilation: {c['hCorrected']} h-corrected, {c['imfConverted']} IMF-converted of {c['records']}")


if __name__ == "__main__":
    main()
