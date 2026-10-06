# Changelog

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
