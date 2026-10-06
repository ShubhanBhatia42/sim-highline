import json
import math
from datetime import date
from pathlib import Path

URL = "https://colibre.strw.leidenuniv.nl/paper_data/2509.07960.yml"
DM = 0.2
RUNS = {
    "COLIBRE_L025m5": ("m5 (L025)", 2.3e5, 25.0, 7.5, {
        0.0: [157, 114, 119, 90, 86, 79, 81, 73, 61, 45, 35, 19, 27, 26, 22, 12, 6, 5, 5, 2, 1],
        0.1: [158, 125, 129, 95, 92, 83, 82, 68, 63, 46, 32, 25, 24, 34, 21, 10, 6, 4, 5, 2, 1],
        0.5: [196, 164, 140, 99, 114, 98, 95, 80, 67, 52, 29, 30, 19, 25, 16, 8, 9, 5, 4, 2],
        1.0: [234, 189, 139, 135, 121, 113, 91, 89, 53, 51, 40, 26, 21, 8, 3, 10, 12, 6, 2, 1],
        2.0: [253, 214, 185, 157, 136, 117, 84, 75, 54, 40, 35, 10, 8, 5, 11, 2, 5, 2],
        3.0: [259, 194, 163, 120, 120, 83, 55, 44, 41, 20, 10, 5, 4, 4, 5, 1, 2],
        4.0: [191, 157, 135, 82, 79, 45, 39, 18, 16, 6, 4, 6, 4, 1, 1, 1],
        5.0: {7.5: 142, 7.7: 117, 7.9: 71, 8.1: 58, 8.3: 32, 8.5: 23, 8.7: 14, 8.9: 7, 9.1: 8, 9.3: 5, 9.7: 3, 9.9: 2},
        6.0: {7.5: 75, 7.7: 56, 7.9: 32, 8.1: 29, 8.3: 14, 8.5: 13, 8.7: 4, 8.9: 3, 9.1: 6, 9.5: 1},
        7.0: [45, 30, 12, 9, 6, 3, 4],
        8.0: [17, 7, 5, 3, 3, 2],
        9.0: [3, 5, 2],
        10.0: [1, 2]}),
    "COLIBRE_L025m6": ("m6 (L025)", 1.84e6, 25.0, 8.5, {
        0.0: [63, 64, 43, 44, 38, 28, 30, 15, 30, 23, 15, 8, 4, 3, 5],
        0.1: [65, 59, 55, 38, 41, 29, 32, 17, 34, 21, 15, 8, 3, 2, 5],
        0.5: [76, 63, 54, 48, 39, 25, 28, 27, 22, 23, 13, 8, 4, 3, 2],
        1.0: [80, 53, 54, 44, 35, 37, 36, 20, 21, 10, 13, 11, 6, 1],
        2.0: [67, 56, 54, 44, 32, 26, 28, 14, 6, 14, 6, 3, 1],
        3.0: [52, 43, 41, 38, 22, 7, 8, 5, 7, 5, 1, 2],
        4.0: [29, 30, 14, 13, 7, 5, 5, 3, 3, 1, 1],
        5.0: [16, 13, 8, 6, 5, 1, 2, 1],
        6.0: [8, 2, 4, 3, 2],
        7.0: [3, 1]}),
    "COLIBRE_L025m7": ("m7 (L025)", 1.47e7, 25.0, 9.3, {
        0.0: [34, 32, 18, 21, 23, 26, 17, 9, 5, 4, 5],
        0.1: [34, 27, 21, 26, 29, 25, 14, 7, 6, 3, 5],
        0.5: [23, 29, 30, 20, 25, 21, 15, 6, 9, 2, 3],
        1.0: [38, 31, 24, 23, 15, 7, 10, 13, 9, 2],
        2.0: [27, 19, 22, 8, 7, 6, 12, 9, 1],
        3.0: [14, 4, 8, 7, 4, 5, 5, 2],
        4.0: [4, 6, 4, 4, 1, 2, 2],
        5.0: [1, 3, 1, 2]}),
    "COLIBRE_L050m5": ("m5 (L050)", 2.3e5, 50.0, 7.5, {
        1.0: {**{round(7.5 + 0.2 * i, 1): n for i, n in enumerate([1909, 1645, 1272, 1073, 959, 815, 737, 631, 486, 399, 264, 221, 180, 131, 103, 85, 44, 27, 12, 4])}, 11.7: 1},
        2.0: [2384, 1804, 1493, 1167, 1011, 843, 685, 526, 388, 319, 205, 155, 80, 63, 48, 30, 22, 8, 8, 2],
        3.0: [2108, 1675, 1264, 1029, 839, 601, 491, 360, 280, 164, 117, 62, 42, 31, 19, 9, 9, 1, 4],
        4.0: [1622, 1192, 910, 715, 513, 366, 298, 205, 138, 87, 44, 36, 9, 13, 7, 4, 2],
        5.0: [1063, 771, 530, 412, 276, 212, 145, 100, 58, 40, 19, 11, 5, 7, 1]}),
}
PUBLISHED = [("COLIBRE_L025m5", 0.0, 7.5, -1.2989503698999922), ("COLIBRE_L025m6", 2.0, 8.5, -1.6687752196083994),
             ("COLIBRE_L025m7", 1.0, 9.3, -1.9150664256924157), ("COLIBRE_L050m5", 3.0, 7.5, -1.0740694027606605),
             ("COLIBRE_L050m5", 1.0, 11.7, -4.39794000930117), ("COLIBRE_L025m5", 5.0, 9.7, -3.0177287675895634)]


def bins(spec, xmin):
    return spec if isinstance(spec, dict) else {round(xmin + DM * i, 1): n for i, n in enumerate(spec)}


for key, z, x, y in PUBLISHED:
    _, _, box, xmin, table = RUNS[key]
    n = bins(table[z], xmin)[x]
    assert abs(math.log10(n / box**3 / DM) - y) < 1e-9, (key, z, x)

records = []
for key, (run, mpart, box, xmin, table) in RUNS.items():
    vol = box**3 * DM
    assert xmin - 0.1 >= math.log10(100 * mpart), key
    for z, spec in table.items():
        b = bins(spec, xmin)
        if len(b) < 2:
            continue
        points = [{"x": x, "y": round(math.log10(n / vol), 4), "yLow": round(math.log10(max(n - math.sqrt(n), 0.5) / vol), 4),
                   "yHigh": round(math.log10((n + math.sqrt(n)) / vol), 4), "count": n} for x, n in sorted(b.items())]
        records.append({
            "id": f"chaikin26.colibre.{key.split('_')[1].lower()}.gsmf.z{z:g}", "source": "COLIBRE", "run": run, "kind": "simulation", "relation": "gsmf",
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
            "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy number density per dex (raw, no Eddington bias)", "yUnit": "log10(cMpc^-3 dex^-1)"},
            "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": points},
            "scatter": None,
            "selection": {"population": "all galaxies", "warning": (f"Chaikin et al. 2026 published GSMF (gsmf_raw, 0.2 dex bins) for the ({box:g} cMpc)^3 box. Bin counts transcribed from the published file; "
                          f"values recomputed as log10(N / V / 0.2 dex) and checked against the published values. Bins below 100 baryonic particle masses dropped; Poisson errors only, "
                          "so cosmic variance of this small box is not included and the massive end is noisy.")},
            "definitions": {"massDefinition": "unspecified", "imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "densityFrame": "comoving", "population": "all"},
            "provenance": {"tier": "published-table", "citation": "Chaikin et al. 2026, MNRAS 548, stag740 (doi:10.1093/mnras/stag740), COLIBRE plot data", "doi": "10.1093/mnras/stag740", "url": URL,
                           "retrieved": "2026-10-05", "sourceMember": f"{key}/gsmf_raw/z{z:.1f} (bin_counts, transcribed)"},
            "calibration": "target" if z <= 0.1 else "prediction", "rankable": True,
            "notes": "Superseded by scripts/ingest_colibre_gsmf.py when run on the full file (identical record ids)."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "colibre-gsmf-small-boxes.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} COLIBRE GSMF records; {len(PUBLISHED)} published values reproduced exactly")
