#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
WORK=${SIMHIGHLINE_WORK:-./_downloads}
mkdir -p "$WORK"

curl -fsSL -o "$WORK/2509.07960.yml" https://colibre.strw.leidenuniv.nl/paper_data/2509.07960.yml
python3 scripts/ingest_colibre_gsmf.py "$WORK/2509.07960.yml"

if [ -n "${TNG_API_KEY:-}" ]; then
  for run in TNG50-1 TNG100-1 TNG300-1; do
    python3 scripts/fetch_tng.py "$run" "$WORK/$run"
    python3 scripts/derive_subfind_relations.py "$run" "$WORK/$run"
  done
else
  echo "TNG_API_KEY not set: skipping IllustrisTNG"
fi

if [ -n "${EAGLE_USER:-}" ] && [ -n "${EAGLE_PASSWORD:-}" ]; then
  for sim in RefL0100N1504 RecalL0025N0752; do
    python3 scripts/derive_eagle_relations.py "$sim" --user "$EAGLE_USER" --password "$EAGLE_PASSWORD"
  done
else
  echo "EAGLE_USER/EAGLE_PASSWORD not set: skipping EAGLE"
fi

if [ -n "${FLAMINGO_SOAP_DIR:-}" ]; then
  python3 scripts/derive_soap_relations.py flamingo "${FLAMINGO_RUN:-L1_m9}" "${FLAMINGO_MBAR:-1.07e9}" "$FLAMINGO_SOAP_DIR"/halo_properties_*.hdf5
else
  echo "FLAMINGO_SOAP_DIR not set: skipping FLAMINGO"
fi

node scripts/annotate-definitions.mjs
node scripts/validate-curves.mjs
node scripts/test-compare.mjs
node scripts/build-static.mjs
node scripts/test-static.mjs
