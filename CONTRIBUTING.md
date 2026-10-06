# Contributing a source to sim-highline

sim-highline holds curves that someone published, with the definitions that decide whether two curves can be compared. A contribution is a paper (or a data release) whose curve is not in the dataset yet. Nothing is synthesised, interpolated or filled: a missing epoch stays missing.

## Before you start

1. Check `data/sources-catalogue.json` and `data/literature-backlog.json` (179 papers, with status) so the work is not duplicated. Open an issue or add a `queued` entry with a note if you take one.
2. Check the relation exists in `highline/index.html` (`REL`). A new relation needs a note in `data/relation-notes.json` (120 to 260 words, at least three references including a review or compilation and a simulation-versus-data paper; `scripts/test-notes.mjs` enforces it).

## What every record carries

`id`, `source`, `run`, `kind`, `relation`, `epoch` (exact), `axes` (native definitions and units), `representation` (points or parametric), `definitions` (IMF, cosmology, mass and aperture, halo definition, population, SFR timescale, metallicity tracer where they apply), `provenance` (tier, citation with volume and page, DOI that resolves on Crossref, URL, retrieved date, source member, SHA-256 where a file exists), `calibration`, `rankable`. Schema: `schemas/curve-schema.json`.

Tiers: `catalog-derived`, `official-table` (needs the SHA-256 of the released file), `published-table` (values transcribed from a table in a paper), `published-fit`, `digitized-figure` (never rankable). Units are physical, h-free, log10; record every conversion.

## Three routes, easiest first

- **Table in the paper or its LaTeX source.** Fetch `https://arxiv.org/e-print/<id>`, parse the table, and add spot checks of at least two published numbers inside the script. See `scripts/transcribe_uvlf_sfrd_obs.py`, `scripts/transcribe_btfr_glowacki20.py`.
- **Vector figure.** Copy `scripts/digitizer-template.py` to `scripts/digitize_<suite>_<paper>_<what>.py`. The helpers in `scripts/vector_figure.py` calibrate axes on tick labels and read path vertices, so the result is exact to the plotted line. Assert two plotted values. See `scripts/digitize_thesan_kannan22_uvlf_sfrd.py`. Raster figures are out of scope.
- **Data release.** Write an `ingest_*` or `derive_*` script and record the file checksum.

## Check before you send

```
node scripts/annotate-definitions.mjs && node scripts/validate-curves.mjs && node scripts/validate-manifest.mjs \
 && node scripts/test-curves.mjs && node scripts/test-compare.mjs && node scripts/report-coverage.mjs \
 && node scripts/build-curve-index.mjs && node scripts/export-dataset.mjs && node scripts/test-export.mjs \
 && node scripts/build-static.mjs && node scripts/test-static.mjs && node scripts/build-highline.mjs \
 && node scripts/test-logic.mjs && node scripts/test-literature.mjs && node scripts/test-notes.mjs \
 && node scripts/test-profiles.mjs && node scripts/build-site.mjs && node scripts/test-site.mjs \
 && for t in scripts/test_*.py; do python3 $t; done && node scripts/audit-curves.mjs
python3 scripts/regress_digitizers.py
python3 scripts/verify-dois.py   # network: every DOI resolves and matches the stated first author, volume and page
```

The audit must end with 0 errors and 0 warnings; accepted findings go in `data/audit-known.json` with a reason. Add an entry to `data/sources-catalogue.json`, profile any new observational source in `data/observation-profiles.json`, bump `data/release.json` and add a line to `CHANGELOG.md`.

## Style

Surgical changes, ASCII names, no verbose comments, consistent with the neighbouring scripts. A contribution that is wrong in a way the audit cannot see is worse than one that is missing: when a definition is not stated in the paper, write `unspecified`.
