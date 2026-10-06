import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

fixture = {"Description": "synthetic test fixture, not COLIBRE data",
           "COLIBRE_L200m6": {"gsmf_raw": {"z0.0": {"log10_bin_centers": [7.9, 8.1, 8.3, 8.5, 10.1], "log10_gsmf_values": [-1.0, -1.1, -1.2, -1.3, -2.5], "bin_counts": [400, 300, 200, 100, 4]}}}}
with tempfile.TemporaryDirectory() as tmp:
    src, out = Path(tmp) / "fx.yml", Path(tmp) / "out.json"
    src.write_text(yaml.safe_dump(fixture))
    subprocess.run([sys.executable, str(Path(__file__).with_name("ingest_colibre_gsmf.py")), str(src), str(out)], check=True, capture_output=True)
    record = json.loads(out.read_text())["records"][0]
points = record["representation"]["points"]
assert [p["x"] for p in points] == [8.5, 10.1], "bins below 100 particle masses must be dropped"
assert abs(points[1]["yHigh"] - (-2.5 + math.log10(1.5))) < 1e-4, "Poisson errors must follow the published counts"
assert record["calibration"] == "target", "z~0 COLIBRE GSMF is a calibration target"
print("COLIBRE GSMF ingester fixture test passed")
