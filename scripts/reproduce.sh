#!/usr/bin/env bash
# Rebuild the numbers from the data, in the order a reader would. Run from the repository root.
#   scripts/reproduce.sh          exploratory checks, rankings and exports from the saved registered results (about 10 minutes on four cores)
#   scripts/reproduce.sh full     also re-runs the two registered analyses from the saved catalogues (about 1 hour 20 minutes more); afterwards `git diff --stat data/analysis` must be empty, which is what "reproduces" means
# Needs python3 with requirements-analysis.txt (numpy, scipy, scikit-learn) and node. The catalogues themselves are rebuilt by scripts/ingest_camels_galaxies.py (about 35 minutes per suite, needs a network and requirements-ingest.txt) and are not touched here.
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
t0=$(date +%s)
stage() { echo; echo "== $1"; }
if [ "${1:-}" = "full" ]; then
  stage "registered: all at once (about 1 hour)";      python3 scripts/analyze_joint_reachability.py
  stage "registered: model form (about 20 minutes)";    python3 scripts/analyze_model_form.py > /dev/null
  git diff --stat data/analysis || true
fi
stage "retuning data for the dials page (seconds)";     python3 scripts/export_retune_data.py
stage "robustness checks (about 5 minutes)";            python3 scripts/explore_joint_robustness.py
stage "third code (about 2 minutes)";                   python3 scripts/explore_third_code.py
stage "tuning to observations (under a minute)";        python3 scripts/explore_tune_to_observations.py
stage "ranking (seconds)";                              python3 scripts/rank_observables.py
stage "data quality (seconds)";                         python3 scripts/analyze_data_quality.py
stage "checks";                                         python3 scripts/test_calibration.py; python3 scripts/test_registration.py
echo; echo "reproduce: done in $(( $(date +%s) - t0 )) s"
