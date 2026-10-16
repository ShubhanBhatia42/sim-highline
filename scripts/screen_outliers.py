"""Plausibility screen: records that sit far from what other sources publish for the same relation, epoch and units.
Screening only: nothing is corrected or removed; flags are leads for a source check, not verdicts."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sim_highline

MIN_PEERS = 3
MIN_POINTS = 3
DZ = 0.15
FLAG_DEX = 0.7
FLAG_Z = 3.0
SKIP = {"sfrd", "smd", "uvlf", "hmf", "sfrf"}


def screen(df):
    d = df[(df.kind != "empirical-model") & ~df.relation.isin(SKIP)].dropna(subset=["x", "y"])
    curves = {}
    for rid, g in d.groupby("record_id"):
        g = g.sort_values("x")
        h = g.iloc[0]
        if len(g) < MIN_POINTS:
            continue
        curves[rid] = dict(rel=h.relation, xu=h.x_unit, yu=h.y_unit, mq="" if h.metallicity_quantity is None or h.metallicity_quantity!=h.metallicity_quantity else str(h.metallicity_quantity), z=float(h.z), src=h.source, kind=h.kind, x=g.x.to_numpy(float), y=g.y.to_numpy(float), run=h.run)
    groups = {}
    for rid, c in curves.items():
        groups.setdefault((c["rel"], c["xu"], c["yu"], c["mq"]), []).append(rid)
    out = []
    for (rel, xu, yu, _mq), ids in groups.items():
        for rid in ids:
            c = curves[rid]
            peers = [curves[o] for o in ids if curves[o]["src"] != c["src"] and abs(curves[o]["z"] - c["z"]) <= DZ]
            by_src = {}
            for p in peers:
                by_src.setdefault(p["src"], []).append(p)
            offs = []
            for x, y in zip(c["x"], c["y"]):
                vals = []
                for plist in by_src.values():
                    v = [np.interp(x, p["x"], p["y"]) for p in plist if p["x"][0] <= x <= p["x"][-1]]
                    if v:
                        vals.append(np.median(v))
                if len(vals) >= MIN_PEERS:
                    offs.append(y - np.median(vals))
            if len(offs) >= MIN_POINTS:
                out.append(dict(id=rid, relation=rel, source=c["src"], run=c["run"], kind=c["kind"], z=c["z"], medianOffsetDex=float(np.median(offs)), nPoints=len(offs), xUnit=xu, yUnit=yu))
    for rel in {o["relation"] for o in out}:
        sub = [o for o in out if o["relation"] == rel]
        v = np.array([o["medianOffsetDex"] for o in sub])
        mad = max(1.4826 * np.median(np.abs(v - np.median(v))), 0.05)
        for o in sub:
            o["robustZ"] = float((o["medianOffsetDex"] - np.median(v)) / mad)
            o["flag"] = abs(o["medianOffsetDex"]) >= FLAG_DEX and abs(o["robustZ"]) >= FLAG_Z
    return out


def main():
    res = screen(sim_highline.load())
    meta = {}
    for f in sorted((ROOT / "data" / "curves").glob("*.json")):
        for r in json.loads(f.read_text())["records"]:
            meta[r["id"]] = r
    for o in res:
        r = meta.get(o["id"], {})
        o["population"] = r.get("selection", {}).get("population")
        o["recordWarning"] = (r.get("selection", {}).get("warning") or "")[:240]
    flagged = sorted((o for o in res if o["flag"]), key=lambda o: -abs(o["medianOffsetDex"]))
    by_src = {}
    for o in res:
        by_src.setdefault((o["source"], o["relation"]), []).append(o)
    systematic = [dict(source=s, relation=r, records=len(v), flagged=sum(o["flag"] for o in v), medianOffsetDex=round(float(np.median([o["medianOffsetDex"] for o in v])), 3))
                  for (s, r), v in by_src.items() if len(v) >= 3 and sum(o["flag"] for o in v) >= max(2, len(v) // 2)]
    doc = dict(schemaVersion="1.0.0", method=f"Offset of each curve from the median of other sources' curves (interpolating peers only inside their published range) at the same relation, units and z within {DZ}; at least {MIN_PEERS} peer sources per point. Flag: |median offset| >= {FLAG_DEX} dex and robust z >= {FLAG_Z} within the relation.",
               nScreened=len(res), nFlagged=len(flagged), systematic=sorted(systematic, key=lambda s: -abs(s["medianOffsetDex"])),
               flagged=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items()} for o in flagged])
    (ROOT / "data" / "analysis" / "plausibility-screen.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(f"plausibility screen: {len(res)} curves screened, {len(flagged)} flagged, {len(systematic)} source/relation pairs systematic")
    triaged = json.loads((ROOT / "data" / "screen-triaged.json").read_text())["triaged"]
    new = [o["id"] for o in flagged if o["id"] not in triaged]
    if new:
        raise SystemExit("flagged by the plausibility screen and not yet triaged (add each to data/screen-triaged.json with a reason, or fix the record): " + ", ".join(new))


if __name__ == "__main__":
    main()
