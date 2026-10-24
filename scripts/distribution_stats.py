"""Statistics of a per-galaxy distribution given as counts on a grid: quantiles, fraction below thresholds, the fraction between the two thresholds (for sSFR: the green valley) and the two peak positions.
Mirrors distributionStats in compare.js step for step (tests/fixtures/distribution-fixture.json is evaluated by both and compared by scripts/test-distributions.mjs and scripts/test_distributions.py).
Also the helper the catalogue adapters use to turn per-galaxy arrays into counts. The code lives in sim_highline_derive.py (so that `sim-highline derive` can use it); this file keeps the names the scripts import.
Usage: imported by ingest_camels_distributions.py, derive-distributions.mjs's tests and the adapters."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim_highline_derive import LEVELS, MIN_COUNT, _r6, bin_counts, dist_fraction_below as fraction_below, dist_quantile as quantile, dist_stats as stats  # noqa: E402,F401
