import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1410.3485"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
TEX = SRC / "Appendix.tex"
PM = r"([-\d.]+)\s*\$\\pm\$\s*([\d.]+)"
SINGLE = "log10 galaxy number density per dex (single Schechter fit, converted from per-dM)"
DOUBLE = "log10 galaxy number density per dex (double Schechter fit, converted from per-dM)"
PUBLISHED = {("single", 0.1): (11.14, 0.84, -1.43), ("single", 4.0): (10.60, 0.12, -1.74), ("double", 1.0): (10.74, 1.51, -0.98, 0.48, -1.62),
             ("double", 4.0): (10.00, 0.24, 0.89, 0.43, -1.69)}

text = TEX.read_text()
rows = {"single": {}, "double": {}}
for line in text.splitlines():
    m = re.match(r"\s*([\d.]+)\s*&(.*)\\\\", line)
    if not m or "pm" not in line:
        continue
    z = float(m.group(1))
    vals = re.findall(PM, m.group(2))
    if len(vals) == 3:
        rows["single"][z] = [(float(v), float(e)) for v, e in vals]
    elif len(vals) == 5:
        rows["double"][z] = [(float(v), float(e)) for v, e in vals]
assert sorted(rows["single"]) == sorted(rows["double"]) == [0.1, 0.5, 1.0, 2.0, 3.0, 4.0], rows
for (kind, z), want in PUBLISHED.items():
    assert tuple(v for v, _ in rows[kind][z]) == want, (kind, z)


def schechter_dex(x, kind, p):
    r = 10 ** (x - p[0][0])
    if kind == "single":
        return math.log10(math.log(10) * p[1][0] * 1e-3 * r ** (p[2][0] + 1) * math.exp(-r))
    return math.log10(math.log(10) * math.exp(-r) * (p[1][0] * 1e-3 * r ** (p[2][0] + 1) + p[3][0] * 1e-3 * r ** (p[4][0] + 1)))


EXPR = {"single": "log10(Math.LN10*Math.exp(-Math.pow(10,x-logMstar))*phi1*Math.pow(10,(x-logMstar)*(alpha1+1)))",
        "double": "log10(Math.LN10*Math.exp(-Math.pow(10,x-logMstar))*(phi1*Math.pow(10,(x-logMstar)*(alpha1+1))+phi2*Math.pow(10,(x-logMstar)*(alpha2+1))))"}
EQ = {"single": "Phi_dex = ln(10) exp(-M/M*) phi1 (M/M*)^(alpha1+1)",
      "double": "Phi_dex = ln(10) exp(-M/M*) [phi1 (M/M*)^(alpha1+1) + phi2 (M/M*)^(alpha2+1)]"}
records = []
for kind in ("single", "double"):
    for z, p in sorted(rows[kind].items()):
        names = ["logMstar", "phi1", "alpha1"] + (["phi2", "alpha2"] if kind == "double" else [])
        params = {n: (v * 1e-3 if n.startswith("phi") else v) for n, (v, _) in zip(names, p)}
        params.update({n + "Error": (e * 1e-3 if n.startswith("phi") else e) for n, (_, e) in zip(names, p)})
        y = [schechter_dex(x, kind, p) for x in (8.0, 10.0, 11.0, 12.0)]
        assert y[0] > y[1] > y[2] > y[3], (kind, z)
        records.append({
            "id": f"furlong15.eagle-l100n1504.gsmf-{kind}-schechter.z{z:g}", "source": "EAGLE", "run": f"Ref-L100N1504 ({kind} Schechter fit)", "kind": "simulation", "relation": "gsmf",
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
            "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": DOUBLE if kind == "double" else SINGLE, "yUnit": "log10(cMpc^-3 dex^-1)"},
            "domain": {"xMin": 8.0, "xMax": 12.0},
            "representation": {"type": "parametric", "equation": EQ[kind], "expression": EXPR[kind], "parameters": params},
            "scatter": None,
            "selection": {"population": "all galaxies", "warning": "Least-squares fit by Furlong et al. 2015 to 0.2 dex bins of the Ref-L100N1504 GSMF between 10^8 and 10^12 Msun, Poisson-weighted. "
                          "Phi* is per unit M/M* (cMpc^-3) as tabulated; the record converts to per dex. Fit, not the simulation curve itself; the fit degeneracies between M* and Phi* are noted by the authors."
                          + (" Phi*_2 at z=0.1 is tabulated as 0.00 (rounded)." if kind == "double" and z == 0.1 else "")},
            "definitions": {"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "densityFrame": "comoving", "population": "all"},
            "provenance": {"tier": "published-fit", "citation": "Furlong et al. 2015, MNRAS 450, 4486, Appendix A Table (Schechter fits)", "doi": "10.1093/mnras/stv852",
                           "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": vf.RETRIEVED, "sourceMember": "Appendix.tex table:Schechter (arXiv source, transcribed)"},
            "calibration": "target" if z <= 0.1 else "prediction", "rankable": True,
            "notes": "Transcribed from the paper's table; spot-checked against published values in the script."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "furlong15-eagle-gsmf-schechter.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE GSMF Schechter records; {len(PUBLISHED)} published rows reproduced exactly")
