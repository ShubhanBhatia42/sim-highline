# How the project is put together (one page)

**What it is.** A curated dataset of galaxy scaling relations from simulations and observations (`data/curves/`), a browser Explorer to look at it, a small site that explains and hosts it, four studies asked of the data, and an instrument (the dials page) built on one of them. Everything a visitor sees is static files; there is no server.

```
data/curves/*.json          the records: one curve per record, with definitions, source, tier  (hand-curated; schemas/)
data/ensembles/*.json       CAMELS summaries of 1,000 simulations per code (ingested by range reads from public catalogues)
        │
        ├─ scripts/validate-*, test-*, audit-curves     checks on the records (verify-all.sh)
        ├─ scripts/export-dataset.mjs                  → data/export/  CSV and JSON, the files people download
        ├─ scripts/build-curve-index.mjs               → data/curve-index.js  (what the Explorer embeds)
        │
        ├─ scripts/analyze_*.py   the four studies, each with a protocol in docs/PROTOCOL-*.md written first
        │        └→ data/analysis/*.json  and  docs/ANALYSIS-*.md  (generated; never edited by hand)
        ├─ scripts/explore_*.py   checks made after a registered run (robustness, a third code, tuning to observations); exploratory
        ├─ scripts/export_retune_data.py  → data/retune/retune.json   emulator coefficients and curves for the dials page
        └─ scripts/analyze_data_quality.py → data/analysis/data-quality.json, docs/DATA-QUALITY.md

highline/index.html + logic.js + ../compare.js  the Explorer (one file once built, data embedded as JSON text)
site/src/*.html, site.css, retune.js            the site templates; {{placeholders}} are filled from the JSON above
scripts/build-highline.mjs, build-site.mjs, build-static.mjs   → dist/   (highline.html, site/, 404.html, data/)
.github/workflows/      verify (offline checks + browser tests), pages (deploy main), watch (weekly)
```

**Rules that hold the design together**

1. *Nothing is synthesised.* A curve that does not exist at an epoch is absent, not interpolated.
2. *Generated files are generated.* Anything under `data/analysis/`, `data/export/`, `docs/ANALYSIS-*.md`, `docs/DATA-QUALITY.md` and `dist/` comes from a script; CI fails when a committed file differs from what the script produces.
3. *Rules before results.* A study's protocol is committed before its result file exists (`data/registration-trail.json`, `scripts/test_registration.py`). Checks made afterwards are labelled exploratory and change no verdict.
4. *Numbers on pages come from the data.* Pages are templates filled from the saved results; tests read the saved results and compare them with what the page says.
5. *The page and the analysis agree.* The dials page evaluates the emulators in JavaScript; `scripts/test_parity.py` and `scripts/test-parity.mjs` compare that with the full Python emulators at 24 dial settings.

**Tests, by what they guard**

| guard | scripts |
|---|---|
| the data | `validate-curves`, `validate-manifest`, `test-curves`, `audit-curves`, `test_claims.py`, `screen_outliers.py` |
| the export and the package | `test-export`, `test_sim_highline_loader.py`, `test_cli.py` |
| the studies | `test_harmonization.py`, `test_model_form.py`, `test_joint_reachability.py` (about 2 minutes on four cores), `test_calibration.py`, `test_registration.py`, `test_parity.py` |
| the pages | `test-site`, `lint.mjs`, `check_prose.py`, `test-determinism` |
| the browser | `test-ui`, `test-journeys`, `test-yourrun`, `test-dials`, `test-layouts`, `test-keyboard`, `test-resilience`, `test-performance`, `test-parity` |

**One-off scripts kept as provenance.** `ingest_*`, `derive_*`, `digitize_*`, `transcribe_*` and `curate_*` produced records once, from a paper or a catalogue; they are kept so that every record can be traced to the code that made it, and are not part of the build. A new record comes from one of these three routes (see `CONTRIBUTING.md`).

**Commands.** `make help` lists them; `make verify` is what a pull request has to pass.
