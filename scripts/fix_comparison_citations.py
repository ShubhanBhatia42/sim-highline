import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "curves" / "comparison-data.json"
FIX = {
    "vcd.chang-et-al-2015-sdss.": ("Chang et al. 2015, ApJS 219, 8", "10.1088/0067-0049/219/1/8"),
    "vcd.gruppioni-et-al-2013-herschel-ir.": ("Gruppioni et al. 2013, MNRAS 432, 23", "10.1093/mnras/stt308"),
    "vcd.smit-et-al-2012-uv-derived.": ("Smit et al. 2012, ApJ 756, 14", "10.1088/0004-637X/756/1/14"),
    "vcd.xgass-catinella-et-al-2018.": ("Catinella et al. 2018, MNRAS 476, 875 (xGASS)", "10.1093/mnras/sty089"),
}
doc = json.loads(PATH.read_text())
n = 0
for r in doc["records"]:
    for prefix, (cite, doi) in FIX.items():
        if r["id"].startswith(prefix):
            p = r["provenance"]
            if "upstreamCitation" not in p:
                p["upstreamCitation"] = p["citation"]
            p["citation"] = f"{cite}, via the velociraptor comparison data"
            p["doi"] = doi
            p["url"] = f"https://doi.org/{doi}"
            n += 1
PATH.write_text(json.dumps(doc, indent=2) + "\n")
print(f"Corrected citations on {n} comparison-data records")
