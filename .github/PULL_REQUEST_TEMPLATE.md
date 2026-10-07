## What this adds or changes

Source (paper, DOI, figure or table):
Suite and relation:
Tier (`published-table`, `digitized-figure`, ...):

## Checklist

- [ ] `./scripts/verify-all.sh` passes and the regenerated files are committed (CI fails if they are out of date)
- [ ] the script contains spot checks against at least two published numbers
- [ ] every record has epoch, native axis definitions and units, structured definitions, provenance and calibration (see CONTRIBUTING.md)
- [ ] `python3 scripts/verify-dois.py` passes for new DOIs (no DOI written from memory)
- [ ] `data/sources-catalogue.json` and `data/release.json` (version bump) and `CHANGELOG.md` are updated
- [ ] no values were interpolated, smoothed or filled in
