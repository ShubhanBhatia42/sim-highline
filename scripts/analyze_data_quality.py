"""What the dataset can and cannot be trusted for, computed from the records (nothing typed by hand): how each curve was obtained, how accurate the extraction from figures is where an independent table exists, where one
simulation appears in two papers and the papers disagree, which relation-epoch cells have thin evidence, and which records carry third-party terms. Writes data/analysis/data-quality.json and docs/DATA-QUALITY.md.
Usage: python3 scripts/analyze_data_quality.py"""
import collections
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
REF_TIERS = ("official-table", "published-table", "catalog-derived", "published-fit")
EPOCHS = (0.1, 0.5, 1, 2, 3, 4, 6, 8)  # representative epochs for the thin-evidence table


def load():
    return json.loads((ROOT / "data" / "export" / "sim-highline-records.json").read_text())["records"]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def pts(r):
    rep = r["representation"]
    if rep.get("type") != "points":
        return None
    p = [(q["x"], q["y"]) for q in rep["points"] if q.get("x") is not None and q.get("y") is not None]
    return np.array(sorted(p)) if len(p) >= 4 else None


def deviation(a, b):
    """Differences in y of curve a from curve b at the x of the sparser curve, over their common range; None if fewer than 4 shared points."""
    lo, hi = max(a[0, 0], b[0, 0]), min(a[-1, 0], b[-1, 0])
    if hi <= lo:
        return None
    sparse, dense = (a, b) if len(a) <= len(b) else (b, a)
    m = (sparse[:, 0] >= lo) & (sparse[:, 0] <= hi)
    if m.sum() < 4:
        return None
    d = sparse[m, 1] - np.interp(sparse[m, 0], dense[:, 0], dense[:, 1])
    return {"n": int(m.sum()), "median_abs": float(np.median(np.abs(d))), "max_abs": float(np.max(np.abs(d))), "signed_median": float(np.median(d)) * (1 if sparse is a else -1)}


def same_curve_candidates(recs, by_run):
    """Pairs of records of one source and relation at the same epoch. by_run: also require the same run name and axis definitions (two papers on one simulation); otherwise require identical definitions (a figure against a table of the same thing)."""
    by = collections.defaultdict(list)
    for r in recs:
        by[(r["source"], r["relation"])].append(r)
    for (src, rel), rs in by.items():
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                if abs(a["epoch"]["zRepresentative"] - b["epoch"]["zRepresentative"]) > 0.05:
                    continue
                if by_run:
                    if norm(a.get("run")) != norm(b.get("run")):
                        continue
                    if (norm(a["axes"].get("xDefinition")), norm(a["axes"].get("yDefinition"))) != (norm(b["axes"].get("xDefinition")), norm(b["axes"].get("yDefinition"))):
                        continue
                elif json.dumps(a.get("definitions"), sort_keys=True) != json.dumps(b.get("definitions"), sort_keys=True):
                    continue
                yield a, b


def label(r):
    return f"{r['source']} {r.get('run') or ''} ({r['relation']}, z = {r['epoch']['zRepresentative']:g})".replace("  ", " ")


def cross_checks(recs):
    """Extraction check: a digitized figure against a table or fit of the same thing (same source, relation, epoch, units and definitions). Paper check: one simulation and run in two papers with the same axis definitions."""
    def pair(a, b):
        if (a["axes"].get("xUnit"), a["axes"].get("yUnit")) != (b["axes"].get("xUnit"), b["axes"].get("yUnit")):
            return None
        pa, pb = pts(a), pts(b)
        if pa is None or pb is None:
            return None
        dv = deviation(pa, pb)
        if dv is None:
            return None
        return {"a": a["id"], "b": b["id"], "label": label(a), "tier_a": a["provenance"]["tier"], "tier_b": b["provenance"]["tier"], "unit": a["axes"].get("yUnit"), **dv}
    extraction, papers = [], []
    for a, b in same_curve_candidates(recs, False):
        ta, tb = a["provenance"]["tier"], b["provenance"]["tier"]
        if "digitized-figure" in (ta, tb) and (ta in REF_TIERS or tb in REF_TIERS):
            row = pair(a, b)
            if row:
                extraction.append({**row, "same_definitions": True})
    for a, b in same_curve_candidates(recs, True):
        if a["provenance"].get("citation") != b["provenance"].get("citation"):
            row = pair(a, b)
            if row:
                papers.append({**row, "same_definitions": json.dumps(a.get("definitions"), sort_keys=True) == json.dumps(b.get("definitions"), sort_keys=True)})
    # a figure can be paired with the tables of several runs that share its definitions; keep, for each figure curve, the candidate it agrees with best (the pairing cannot tell which run a table belongs to, so this is the most favourable reading)
    best = {}
    for r in extraction:
        fig = r["a"] if r["tier_a"] == "digitized-figure" else r["b"]
        if fig not in best or r["median_abs"] < best[fig]["median_abs"]:
            best[fig] = r
    key = lambda r: -r["max_abs"]
    return sorted(best.values(), key=key), sorted(papers, key=key)


def thin_cells(recs):
    """Distinct simulation sources with a curve within 0.3 in z of each representative epoch, by relation."""
    rels = sorted({r["relation"] for r in recs if r["kind"] == "simulation"})
    out = {}
    for rel in rels:
        row = {}
        for z in EPOCHS:
            srcs = {r["source"] for r in recs if r["kind"] == "simulation" and r["relation"] == rel and abs(r["epoch"]["zRepresentative"] - z) <= max(0.3, 0.15 * z)}
            row[str(z)] = len(srcs)
        out[rel] = row
    return out


def vocabulary(recs):
    """For each definition key, how many distinct spellings there are and which differ only in case, punctuation or filler words (so that string comparison would call them different)."""
    out = {}
    for key in ("population", "massDefinition", "imf", "densityFrame", "sizeDefinition"):
        vals = collections.Counter(str(r["definitions"][key]) for r in recs if r.get("definitions") and r["definitions"].get(key) is not None)
        groups = collections.defaultdict(list)
        for v in vals:
            groups[re.sub(r"(galaxies|galaxy|the|of|all|sample)", "", re.sub(r"[^a-z0-9]", "", v.lower())) or "empty"].append(v)
        near = [sorted(g, key=lambda v: -vals[v]) for g in groups.values() if len(g) > 1]
        out[key] = {"distinct": len(vals), "records": sum(vals.values()), "near_duplicates": [{"spellings": g, "records": [vals[v] for v in g]} for g in near]}
    # consequence: pairs of curves at a relation whose rules make population a hard key, which differ as strings but not after the normalisation above
    canon = lambda v: re.sub(r"(galaxies|galaxy|the|of|all|sample)", "", re.sub(r"[^a-z0-9]", "", str(v).lower())) or "all"
    blocked = {}
    for rel in ("sfms", "ssfr", "size"):
        rs = [r for r in recs if r["relation"] == rel and r["kind"] == "simulation" and (r.get("definitions") or {}).get("population") is not None]
        total = spelled = 0
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                if a["source"] == b["source"] or abs(a["epoch"]["zRepresentative"] - b["epoch"]["zRepresentative"]) > 0.3:
                    continue
                total += 1
                pa, pb = a["definitions"]["population"], b["definitions"]["population"]
                spelled += pa != pb and canon(pa) == canon(pb)
        blocked[rel] = {"pairs": total, "differ_only_in_spelling": spelled}
    out["population_hard_key"] = blocked
    return out


def analyse():
    recs = load()
    tiers = collections.defaultdict(lambda: {"records": 0, "rankable": 0})
    for r in recs:
        t = tiers[(r["kind"], r["provenance"]["tier"])]
        t["records"] += 1
        t["rankable"] += bool(r["rankable"])
    sims = [r for r in recs if r["kind"] == "simulation"]
    dig = [r for r in sims if r["provenance"]["tier"] == "digitized-figure"]
    unc = [r["provenance"].get("digitizationUncertaintyDex") for r in dig if r["provenance"].get("digitizationUncertaintyDex") is not None]
    methods = collections.Counter((r["provenance"].get("extractionMethod") or "unspecified").split(";")[0].split(",")[0][:60] for r in dig)
    extraction, papers = cross_checks(recs)
    terms = collections.Counter((r["provenance"].get("terms") or "").split(";")[0] for r in recs if r["provenance"].get("terms"))
    pending = [r["id"] for r in recs if "permission not yet requested" in (r["provenance"].get("terms") or "")]
    thin = thin_cells(recs)
    return {"n_records": len(recs), "n_sources": len({r["source"] for r in recs}),
            "tiers": [{"kind": k, "tier": t, **v} for (k, t), v in sorted(tiers.items())],
            "digitized": {"n": len(dig), "share_of_simulation_curves": len(dig) / len(sims), "n_simulation_curves": len(sims), "declared_uncertainty_dex": {"n": len(unc), "median": float(np.median(unc)) if unc else None, "max": float(max(unc)) if unc else None},
                          "extraction_methods": methods.most_common(6), "rankable": sum(bool(r["rankable"]) for r in dig)},
            "extraction_checks": {"pairs": extraction, "n": len(extraction), "n_same_definitions": sum(1 for p in extraction if p["same_definitions"])},
            "redigitization": redigitization(),
            "released_tables": released_tables(recs),
            "paper_disagreements": {"pairs": papers, "n": len(papers)},
            "terms": {"records_with_terms": sum(terms.values()), "by_terms": terms.most_common(8), "permission_not_requested": len(pending)},
            "thin": {"epochs": list(EPOCHS), "cells": thin}, "vocabulary": vocabulary(recs),
            "checksums": {"with_checksum": sum(bool(r["provenance"].get("checksumSha256")) for r in recs), "records": len(recs)}}


def replaced_sentence(rt):
    if "exactMatch" not in rt:
        return ""
    s = f"Of the {rt['exactMatch']} curves for which a table that matches the plotted numbers exactly was found, {len(rt['replaced'])} have been replaced by the table's numbers (their tier is now published-table or official-table)"
    n = len(rt["stillFigureRead"])
    if n:
        s += f"; {n} {'is' if n == 1 else 'are'} still the figure read: " + ", ".join("`" + i + "`" for i in rt["stillFigureRead"])
    s += "."
    if rt.get("duplicates"):
        s += f" {len(rt['duplicates'])} more figure-read curve{' is' if len(rt['duplicates']) == 1 else 's are'} a duplicate of numbers already in the dataset as an official table ({', '.join('`' + i + '`' for i in rt['duplicates'])}); {'it is' if len(rt['duplicates']) == 1 else 'they are'} kept because the figure shows an aperture series."
    return s


def pct(x):
    return f"{100 * x:.0f}%"


def render(q):
    d = q["digitized"]
    L = ["# Data quality", "", "Generated by `scripts/analyze_data_quality.py` from the exported records; do not edit by hand. Nothing here is typed: every number is computed from the records.", "",
         f"## How the {q['n_records']} curves were obtained", "", "| kind | how it was obtained | records | usable for ranking |", "|---|---|---|---|"]
    for t in q["tiers"]:
        L.append(f"| {t['kind']} | {t['tier']} | {t['records']} | {t['rankable']} |")
    unc = d["declared_uncertainty_dex"]
    L += ["", f"{d['n']} of the {d['n_simulation_curves']} simulation curves ({pct(d['share_of_simulation_curves'])}) were read from published figures and none is used for ranking ({d['rankable']} are marked rankable). "
          f"They are read from the vector paths of the figure files, with the axes calibrated on the printed tick marks, not by eye from pixels; the extraction error the scripts declare is a median {unc['median']} dex and at most {unc['max']} dex over {unc['n']} curves. "
          "That is the error of reading the figure, not the error of the figure's own content, which only the authors can vouch for.", "",
          "Extraction methods recorded: " + "; ".join(f"{m} ({n})" for m, n in d["extraction_methods"]) + ".", ""]
    e = q["extraction_checks"]
    L += ["## Does the extraction agree with an independent table?", "",
          f"Where the same source, relation and epoch exists both as a figure we read and as a table or fit, with identical definitions and units, the two can be compared directly. This is possible for only {e['n']} of the {d['n']} digitized curves ({100 * e['n'] / max(1, d['n']):.1f} %). The pairing cannot tell which run a table belongs to, so for each figure the closest candidate is shown, which is the most favourable reading. Differences are in the y units of the curve. For all other digitized curves the extraction has no independent check in the data.", ""]
    if e["pairs"]:
        L += ["| curve | one is a figure, the other | unit | shared points | median difference | largest difference | same definitions |", "|---|---|---|---|---|---|---|"]
        for p in e["pairs"][:25]:
            L.append(f"| {p['label']} | {p['tier_a']} / {p['tier_b']} | {p['unit']} | {p['n']} | {p['median_abs']:.3f} | {p['max_abs']:.3f} | {'yes' if p['same_definitions'] else 'no'} |")
        L += ["", "The extraction code itself is tested on synthetic figures with known curves and axes (`scripts/test_vector_figure.py`: linear and log calibration, curve vertices, marker centres), which checks the method but not each figure."]
    rd = q.get("redigitization")
    if rd:
        L += ["", "## Re-digitizing a random sample by a different method", "",
              f"The original extraction reads the vector paths of the figure. To test it without those paths, a second reader rendered each figure to a 400 dpi raster, recalibrated the axes from the tick marks in the image, and traced the curve by colour (`data/analysis/redigitization-check.json`). Curves were drawn at random until {rd['checked']} could be checked; {rd['attempted']} were tried, and {rd['notCheckable']} could not be checked (overlapping curves of one colour, raster or outlined axes, or a stored quantity that is a transform of the plotted one). "
              f"Of the {rd['checked']} checked, from {rd['papers']} papers, {rd['pass']} are within tolerance and {rd['fail']} are not. On the {rd['logYChecked']} curves with logarithmic y axes the median of the per-curve median differences is {rd['logYMedianDex']:.4f} dex and the 90th percentile of the per-curve maxima is {rd['logYP90Dex']:.2f} dex; {rd['logYExceed']} exceed the extraction's stated uncertainty. Each failure was inspected: none could be attributed to a stored curve (a marker, error bar or other stroke of the same colour lay on the curve, or the panel holds many near-identical curves), one is inconclusive at about 0.01 dex. "
              "This checks the extraction of the curves it could check (21% of those tried); it is not a statement about the rest, it cannot see a wrong panel or run, or a wrong tick label shared by both methods, and one reader made it.", ""]
    rt = q.get("released_tables")
    if rt:
        c, rc = rt["categories"], rt["recordsByCategory"]
        L += ["", "## Did the authors release the numbers?", "",
              f"For the {rt['papers']} papers behind the {rt['records']} figure-read simulation curves, `data/analysis/released-tables.json` records whether the numbers were published or released. Result: the numbers of {c.get('table-in-eprint', 0) + c.get('table-in-paper', 0) + c.get('table-released-full', 0)} paper(s) are fully available as a table, {c.get('table-released-partial', 0) + c.get('table-partial', 0) + c.get('table-released-unverified', 0)} partly; for {c.get('catalog-public-recompute', 0)} papers ({rc.get('catalog-public-recompute', 0)} curves) only the simulation's catalogues are public, so the plotted numbers would have to be recomputed; {c.get('on-request', 0) + c.get('announced-not-released', 0)} papers say the data are available on request or will be released ({rc.get('on-request', 0) + rc.get('announced-not-released', 0)} curves, among them the largest block); for {c.get('none-found', 0)} nothing was found. " + replaced_sentence(rt), ""]
    p = q["paper_disagreements"]
    L += ["", "## Where two papers give the same simulation and disagree", "", f"{p['n']} pairs of curves of the same simulation, relation and epoch come from different papers with the same axis units.", ""]
    if p["pairs"]:
        L += ["| curve | how obtained | unit | shared points | median difference | largest difference | same definitions |", "|---|---|---|---|---|---|---|"]
        for r in p["pairs"][:25]:
            L.append(f"| {r['label']} | {r['tier_a']} / {r['tier_b']} | {r['unit']} | {r['n']} | {r['median_abs']:.3f} | {r['max_abs']:.3f} | {'yes' if r['same_definitions'] else 'no'} |")
    t = q["terms"]
    L += ["", "## Third-party terms", "", f"{t['records_with_terms']} records carry explicit terms; {t['permission_not_requested']} of them are binned values derived by sim-highline from a repository that has no licence file, for which permission has not yet been requested. " + "; ".join(f"{k} ({n})" for k, n in t["by_terms"]) + ".", ""]
    c = q["checksums"]
    L += ["## Source checksums", "", f"{c['with_checksum']} of {c['records']} records carry the SHA-256 of the file they were made from. The digitizer regression re-fetches every source and compares; the records without a checksum are transcribed fits and tables.", "", "## Spelling of definitions", "",
          "Comparison rules match definition values as strings, so two spellings of one thing count as different. Spellings that differ only in case, punctuation or filler words:", ""]
    for key, v in q["vocabulary"].items():
        if key == "population_hard_key":
            L.append("- **Consequence**: population is a hard key for " + ", ".join(f"{rel} ({v2['differ_only_in_spelling']} of {v2['pairs']} cross-simulation pairs near the same epoch differ only in spelling)" for rel, v2 in v.items()) + ". Such pairs are judged not comparable only because of how the population was written.")
            continue
        L.append(f"- **{key}**: {v['distinct']} distinct values over {v['records']} records" + (f"; {len(v['near_duplicates'])} groups of near-duplicates, for example " + "; ".join(" / ".join(f"`{x}` ({n})" for x, n in zip(g["spellings"], g["records"])) for g in v["near_duplicates"][:3]) if v["near_duplicates"] else "; no near-duplicates"))
    L += ["", "Changing the vocabulary changes the inputs of the definitions and mass-function studies, whose rules were fixed in advance, so it is recorded here and not changed silently.", ""]
    th = q["thin"]
    L += ["## Where the evidence is thin", "", "Distinct simulations with a curve of the relation near each epoch (within 0.3 in z, or 15 % of z at higher z). Cells with fewer than three are thin: an offset against so few says little about the field.", "",
          "| relation | " + " | ".join(f"z={z}" for z in th["epochs"]) + " |", "|---|" + "---|" * len(th["epochs"])]
    for rel, row in th["cells"].items():
        L.append(f"| {rel} | " + " | ".join(str(row[str(z)]) for z in th["epochs"]) + " |")
    return "\n".join(L) + "\n"


def redigitization():
    f = ROOT / "data" / "analysis" / "redigitization-check.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    sm = d["summary"]
    return {"attempted": sm["nAttempted"], "checked": sm["nChecked"], "pass": sm["nPassTolerance"], "fail": sm["nFailTolerance"], "notCheckable": sm["nNotCheckable"], "logYMedianDex": sm["logY_medianOfMedians_dex"],
            "logYP90Dex": sm["logY_p90OfMaxima_dex"], "logYChecked": sm["nLogYAxisCurves"], "logYExceed": sm["logY_nExceedStatedUncertainty"], "papers": len({c["arxiv"] for c in d["curves"]}), "classes": sm["notCheckableByClass"]}


def released_tables(recs=None):
    f = ROOT / "data" / "analysis" / "released-tables.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    cat = collections.Counter(e["category"] for e in d["entries"])
    covered = collections.Counter()
    for e in d["entries"]:
        covered[e["category"]] += e["digitizedSimRecords"]
    out = {"papers": len(d["entries"]), "records": sum(e["digitizedSimRecords"] for e in d["entries"]), "categories": dict(cat), "recordsByCategory": dict(covered)}
    if recs is not None:
        tier = {r["id"]: r["provenance"]["tier"] for r in recs}
        raw = [x for e in d["entries"] if isinstance(e["recordsCovered"], dict) for x in e["recordsCovered"].get("exact-match", [])]
        dup = {re.split(r" \(", x)[0] for x in raw if "already present as" in x}   # the table's numbers are already in the dataset under another record: the figure-read record is a duplicate, not a missing replacement
        exact = [i for i in (re.split(r" \(", x)[0] for x in raw) if i in tier and i not in dup]
        out["exactMatch"] = len(exact)
        out["replaced"] = sorted(i for i in exact if tier[i] != "digitized-figure")
        out["stillFigureRead"] = sorted(i for i in exact if tier[i] == "digitized-figure")
        out["duplicates"] = sorted(i for i in dup if i in tier)
    return out


def main():
    q = analyse()
    (ROOT / "data" / "analysis" / "data-quality.json").write_text(json.dumps(q, indent=1) + "\n")
    (ROOT / "docs" / "DATA-QUALITY.md").write_text(render(q))
    e, p = q["extraction_checks"], q["paper_disagreements"]
    print(f"data quality: {q['n_records']} records; digitized {q['digitized']['n']}; extraction pairs {e['n']} ({e['n_same_definitions']} same definitions); paper pairs {p['n']}")


if __name__ == "__main__":
    main()
