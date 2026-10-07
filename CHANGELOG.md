# Changelog

## 0.12.0 (2026-10-08)

- Data (vector figures): TNG100-1 ISM gas fraction at z 0, 1, 2, 4 (Torrey+19; the gas-fraction relation gains a third simulation), EAGLE stellar mass density histories for the four calibrated L050N0752 models (Crain+15), Romulus25 cosmic SFR density (Tremmel+17).
- Literature triage: all 139 untriaged papers were scanned (`data/literature-scan.json`); each backlog entry now says which relations its captions cover and in what format. 18 semi-analytic and method papers were marked out of scope; five more were skipped with reasons (quenched fraction against halo mass, test-box SFRD of unclear volume, MUFASA and FIRE-1 are not SIMBA and FIRE-2, Auriga needs a profile).

## 0.11.0 (2026-10-08)

- Licence: code MIT (`LICENSE`), dataset CC BY 4.0 (`LICENSE-DATA.md`); third-party terms recorded in `docs/SOURCE-TERMS.md` (Sharda+26 is GPL-2.0, Garcia+24 has no licence file: both open). `CITATION.cff`, `.zenodo.json` and `data/release.json` carry the licence and repository; no DOI yet.
- Beta: dataset Cite box (text and BibTeX) in Get data; "Report an issue" on every curve (prefilled GitHub issue form); "rankable only" pill in the legend; per-relation anchor picker (also used by Tension); optional on-screen IMF conversion to Chabrier with standard offsets (downloads keep published values); embed mode (`&embed=1`) and "Copy embed code"; keyboard hint; landing page "Start with a question" deep links; fixed a first-paint flash of the side panel.
- Python: installable package (`pyproject.toml`, wheel bundles the export tables), `notebooks/quickstart.ipynb`.
- Tooling: `scripts/verify-all.sh` (one verification chain), GitHub issue forms, pull request template, `verify` workflow (pull requests) and weekly `watch-arxiv` workflow, `scripts/watch-arxiv.py`, `scripts/scan_literature.py`; `coverage-report.json` is stamped with the release date so regenerated files are deterministic.

## 0.10.0 (2026-10-08)

- Data (vector figures): FIREbox stellar mass function at z 0-10, cosmic SFR density and stellar mass density (Feldmann+23; 10 records), TNG100 3D half-mass size for main-sequence, quenched and all galaxies at z 0-3 (Genel+18; 12 records), NewHorizon stellar mass density (Dubois+21).
- App: new relation Cosmic stellar mass density (SMD) with its own notes and comparison rules; the site wordmark now reads SIM/HIGHLINE and links home, the app wordmark links to the site, pages fade into each other (cross-document view transitions), the About overlay opens at its title, the Use cases page no longer overflows on phones, and counts on the site pages are generated from the data.
- Literature backlog: 33 ingested; four more papers examined and skipped with reasons (luminosity Tully-Fisher in TNG50, another HI-fraction selection, TNG black hole feedback, arcsecond FIRE-2 sizes).

## 0.9.0 (2026-10-07)

- Data (published tables, transcribed): BlueTides galaxy properties at z 8-14 (Wilkins+17: stellar mass function, median sSFR, star-forming gas metallicity, stellar-to-DM mass ratio, intrinsic and attenuated UV functions with Schechter fits, median black hole mass; 46 records) and FLARES UV luminosity function at z 5-10 with Poisson errors and Schechter fits (Vijayan+21; 12 records).
- Data (vector figures): FLARES SFR density (total, obscured, unobscured), Illustris SFR density and per-galaxy baryonic and stellar Tully-Fisher points, THESAN-ZOOM stellar mass function, UV function (two dust treatments) and SFR density (Kannan+25, 20 records), Horizon-AGN size-mass z 0-4 and mean sSFR with its no-AGN twin (Dubois+16).
- Simulation redshift ranges for BlueTides (to z=15) and THESAN-ZOOM (to z=14.5) updated with their basis; audit plausible sSFR mass range widened to 10^14.

## 0.8.0 (2026-10-07)

- Renamed the project from Concord to sim-highline everywhere. Export files are now `data/export/sim-highline-*.{csv,json,bib}`, the pandas loader is `sim_highline.py` (`import sim_highline`), and the page globals are `SimHighlineCompare`, `SimHighlineExport`, `SimHighlineLogic` and `SIMHIGHLINE_*`. Earlier entries below keep the text as it was after the rename. Downloaded file names from the page start with `sim-highline_`.

## 0.7.0 (2026-10-07)

- Data: COLIBRE size and j_star at z 0-3 (star-forming and passive centrals, all galaxies; Ludlow+26, 32 records) and reference SFR-M* and SHMR at z 0, 10, 17 (Chaikin+26, 6 records); SFR density for SIMBA (Dave+19, converted from cosmic time), Horizon-AGN (Kaviraj+17) and NewHorizon (Dubois+21); z=0 stellar mass function and median sSFR for SIMBA, TNG100 and EAGLE (Dave+20); APOSTLE + EAGLE baryonic Tully-Fisher fits (Sales+17; each fit validated against the curve drawn in the paper, domain read from it); redshift-evolving FIRE-2 MZR fits z 5-12 (Marszewski+24, Z/Zsun).
- App: analytic-evolution simulation records are drawn at any epoch inside their redshift range; COLIBRE fiducial for size and j_star is the star-forming centrals; `z` is available in parametric expressions (`compare.js`).
- Literature: backlog statuses (184 papers: 26 ingested, 8 skipped with reasons, 150 candidates); Baker+24, Weinberger+17, Thomas+19, Ferrero+17, the MaNGA-TNG BTFR paper and Huppenkothen+26 examined and skipped with the reason recorded.

## 0.6.0 (2026-10-06)

- New relations: UV luminosity function (`uvlf`) and cosmic SFR density (`sfrd`). Observations transcribed from the arXiv LaTeX tables: Bouwens+21 (stepwise and Schechter, z 2-10), Harikane+23 (binned, Schechter and SFR densities, z 9-16), Donnan+24 (z 9-14.5), Madau & Dickinson 2014 Eq. 15 (`scripts/transcribe_uvlf_sfrd_obs.py`, 32 records). Simulations digitized from vector figures: THESAN-1/-2/-SDAO-2 UV functions z 6-10 and SFR density (Kannan+22), ASTRID SFR density (Bird+22), EAGLE SFR density (Furlong+15), FIRE-2 intrinsic UV functions z 6-12 (Ma+18), FLARES observed and intrinsic UV functions z 10-15 (Wilkins+22; far-UV luminosity converted exactly to M_UV and per dex to per magnitude).
- Data: cold gas (HI and H2 fraction) for SIMBA, TNG100 and two EAGLE runs from Dave+20 (8 records); SIMBA baryonic Tully-Fisher fits for four velocity definitions and three samples (Glowacki+20 table, 12 records); TNG100 specific angular momentum of early- and late-type centrals with 16-84% bands, kinematic and visual-like morphology (Rodriguez-Gomez+22, 4 records). Observation profiles for all 82 observational sources (survey or facility and what is measured; drafted from titles and abstracts). Citation corrections (Chang+15, Gruppioni+13, Smit+12, xGASS) in `scripts/fix_comparison_citations.py`, upstream citation kept in `provenance.upstreamCitation`.
- Website: default observational anchor per relation (bold line) with each simulation's median offset in the legend and compatibility marks against it; Tension view (simulation by relation, offset at a chosen reference redshift); observational row in Coverage; three guided recipes in the About overlay; redshift-axis and reversed-axis relations; accessibility pass (skip link, dialog and tab semantics, focus return, chart description for screen readers, contrast of secondary text); fiducial-run and offset logic extracted to `highline/logic.js` with unit tests (`scripts/test-logic.mjs`).
- Storage and process: `data/literature-backlog.json` (179 papers with status ingested, queued or skipped with reason; `scripts/build-literature-backlog.py`, `scripts/test-literature.mjs`); `docs/author-requests.md` (generated, 30 papers and 552 digitized records that an author table would replace); `docs/expert-audit-request.md` and `data/audit-outcomes.json`; `CONTRIBUTING.md` and `scripts/digitizer-template.py`; `docs/RELEASE-CHECKLIST.md`.
- Validator: a one-point record may have a zero-width x domain. Audit: `uvlf` plausible x range widened to -25..-5 magnitudes.

## 0.5.1 (2026-10-06)

- Website: provenance on every line (badge O/C/T/F/D in the legend, tooltip names the evidence tier and the paper); relation panel renamed Notes; links to the new About and Simulations & observations pages; evidence panel links to each source's entry.
- Pages: science-first `about.html` with four data-driven figures and computed captions; `sources.html` with numerical method, code, set-up, purpose, team and date for the 19 simulations, and survey or facility for 56 of 75 observational sources, plus a list of metadata issues found.
- Data files: `data/simulation-profiles.json`, `data/observation-profiles.json`; tests `scripts/test-profiles.mjs`, extended `scripts/test-site.mjs`.
- Docs: `docs/literature-candidates.md` (arXiv-verified search of simulation papers, not ingested); addendum to `docs/REVIEW.md`.

## 0.5.0 (2026-10-06)

- Data: Magneticum now has all released boxes (Box0/mr, Box2b/hr, Box2/hr, Box3/uhr, Box4/uhr) plus SHMR and stellar metallicity from the same official tables; NewHorizon complete for every figure that fits an existing relation (size, BTFR, cold gas fraction, MBH-M*, with the earlier sSFR, O/H, Z and SHMR); MBH-M* medians with percentile bands for Illustris, TNG100, TNG300, Horizon-AGN, EAGLE and SIMBA at z=0-5 (Habouzit+21); EAGLE HI fractions at z=0, 1, 4 (Crain+17) and H2 fractions (Lagos+15); EAGLE j*-M* at five redshifts (Lagos+17) and Illustris j*-M* with subsamples (Genel+15).
- Website: each simulation shows one fiducial run by default (variants one click away, per relation); all / none / only controls for the simulations of each relation; relation chips show suite counts and tuck sparse relations (fewer than three simulations) behind a toggle; legend moves to the right on wide screens; auto-range ignores fit lines.
- Website: an About panel per relation with a one-paragraph summary (observations past and present, simulations versus data, physical implication, definition pitfalls), a live line on what this data well holds, and 3 to 8 attributed references with DOI and arXiv links (`data/relation-notes.json`, tested by `scripts/test-notes.mjs`).
- Docs and pages: candid assessment in `docs/REVIEW.md`; product and use-case pages in `site/src/` built to `dist/site/` with numbers taken from the data.
- Fixes: the Magneticum ingest took only the last box column and the test suite assumed a single box.


## 0.4.0 (2026-10-06)

- Export: `data/export/` (records and points tables, full JSON, BibTeX, manifest with SHA-256), `sim_highline.py` loader, `export-lib.js` shared with the website.
- Website (`highline/`): relations sSFR, HI and H2 gas fraction, BTFR and STFR; evidence filters by tier and rankable flag; run-level legend with definition-compatibility marks against a chosen reference; residual view; all-epochs view coloured by redshift; value-at-fixed-x versus redshift view; axis transforms and physical tick labels; ranges; least-squares fit; user overlay; data download (CSV, JSON, Python snippet, BibTeX); SVG and PNG figures with citations; state in the page link; mobile layout.
- Data: NewHorizon sSFR and cold-gas O/H (Dubois+21); TNG100/300 HI and H2 gas fractions (Diemer+19); audit pipeline with accepted-issues file.
- Trust: `scripts/regress_digitizers.py`, tests for `vector_figure`, exporter and loader, expert-audit sample, methods and data card.
