# Independent review of 2026-10-16 (by an AI agent) and what was done about it

**Who reviewed:** a separate AI agent (a Claude subagent), given the repository, the built site and a written brief, with no instruction about what to conclude. **It is not a human expert.** It read the documents, used the site at desktop and phone width, re-derived two headline numbers in Python, and audited claims against the saved data. It did not run the test suites. The full report follows the response table, unedited.

## Response

| # | finding | status |
|---|---|---|
| 1 | Export bug: `records.map(X.recordRow)` passed the row index as the redshift, so 91 parametric records had a wrong `z` and four redshift-dependent fits (Speagle 2014, Popesso 2023, two Marszewski 2024) had wrong points in the downloadable files, since v0.8.0 | **Fixed and tested** (`scripts/export-dataset.mjs`; `scripts/test-export.mjs` now checks the shipped files and fails on the old code). Listed in `docs/CORRECTIONS.md`. The Zenodo record of 0.23.0 still carries the error until a new release is deposited |
| 2 | "Independent review" was an AI agent; commits are mostly by Claude; pages say "one person" | **Fixed:** disclosure on the Methods, FAQ, front, summary and Explorer pages and in the README; the studies say "a separate AI agent (not a human expert)"; tested |
| 3 | "z = 0 to 2.15" typed in two places; the 169 outputs run to z = 4 | **Fixed:** generated from the saved result; tested |
| 4 | "Cannot be brought together by any dial setting" overstates (gas metallicity 0.07 dex; minimum at the box edge) | **Fixed:** wording now says "stays apart at every dial setting tried", gives the magnitudes and the edge-of-range caveat (plain words, FAQ, glossary, dials page, drafts) |
| 5 | "Documentation, not physics, is the binding constraint" is not a finding | **Fixed:** removed from the study page and README; the abstract says the data neither show nor rule it out |
| 6 | Phone dials page: panels far below the dials | **Fixed:** a live copy of the matched property is pinned with the headline on narrow screens; tested |
| 7 | Explorer first minute (opens on SFMS; raw field names; bottom sheet) | **Partly fixed:** opens on the stellar mass function; "Your run" uses plain labels and plain reasons; the UV luminosity function has its own try-this link. **Not done:** a bridge from a simulation snapshot to a curve; the size of the phone bottom sheet |
| 8 | Glossary lacks structural, removable, rankable, dex, anchor, Subfind, Latin hypercube | **Fixed** |
| 9 | SFH plain words | **Fixed:** the one-sentence result starts with what could not be shown, and states the two cautions |
| 10 | Observation-tuning one-liner is selective | **Fixed:** the page lists every family where neither code gets within one noise unit, with counts |
| 11 | "Best any dials" higher than the second optimiser's for three families | **Noted** in `docs/CHOICES-joint-reachability.md`; the dials page still shows the registered numbers |
| 12 | Pre-registration weak evidence; knife-edge ratio; single-family calibration | **Added** as objections 16 and 17 in `docs/SCEPTIC.md` (they stand) |
| 13 | "82 observational sources" includes 5 empirical-model sources | **Fixed:** "observational and empirical sources" throughout, drafts included |
| 14 | Google Fonts sends the reader's address to Google | **Disclosed** on the Methods page (objection 18); self-hosting the fonts is not done |
| NICE | legend count vs header, "1 observational curves", tab bar clipped at 390 px, 5.4 MB first load | **Not done** |

Gaps named by the reviewer: outside checking of the digitized curves (needs people); a direct check of the emulators at the minimiser (**partly done afterwards**: `docs/ANALYSIS-minimiser-check.md`, the simulations nearest the minimum are predicted as well as random ones, but none is at the minimum); a bridge from a user's snapshot to a curve (not done).

---

# Independent review of sim-highline v0.23.0

Scope: read the docs and data; used the built `dist/` at 1280 px and 390 px in Chromium (screenshots in `/tmp/claude-0/-home-user-sim-highline/10a97525-0b95-550a-a8f0-c701b08cbbe7/scratchpad/shots/`); re-derived numbers in Python. Not done: I did not run the test suites (read only), did not re-run the emulator-noise correction (A1), and did not test Firefox/Safari or the Explorer's "Over time / What exists / Disagreement" views.

## MUST-FIX

1. **The downloadable dataset has a silent bug.** `scripts/export-dataset.mjs:14` does `records.map(X.recordRow)` and `records.flatMap(X.pointRows)`; `Array.map` passes the row index as the second argument, which `export-lib.js:25-38` reads as the evaluation redshift. In `data/export/sim-highline-records.csv` (identical copy in `dist/data/export/`) all 91 sampled-parametric records have `z` = row index (`huang18.bluetides.bh.z8`: z=35, but z_min=z_max=8). Their sampled points use that z: `speagle14.sfms.evolution` exports log SFR = +1.91 at log M*=10.03 (z=0 gives -0.18; +1.89 is the z=437 value); `marszewski24.fire2.mzrz.evolution.ab` exports -2.70 at x=6, z=8 gives -2.02. The README's own `select(df, z=(1, 2))` filters on that `z` column (`sim_highline.py:71`). `test-export.mjs:23` uses a z-independent toy fit, so it cannot see this.
2. **"Independent review" is an automated agent, undisclosed on the site.** `study-joint`, `study-sfh`, `studies` and the README say an "independent review preceded the run"; `docs/PROTOCOL-joint-reachability.md:79` and `PROTOCOL-model-form.md:116` say "by a separate agent". No site page mentions it. Related: 41 of 59 commits are authored by "Claude" (36 carry a Co-Authored-By trailer), while the pages say "digitized ... by one maintainer" and "read from published figures by one person" (the readings are script output). A reader will take "independent review" as a human expert. Say what it was.
3. **Wrong range on both study pages.** "169 binned outputs ... z = 0 to 2.15" is typed in `scripts/site-joint.mjs:28,31`. `data/retune/retune.json` blocks and `joint-reachability.json` meta show the 169 include z=3 (gsmf 4, rho 2 outputs) and z=4 (rho, 2); the CHOICES doc says z = 0, 0.95, 2.15, 3, 4. No test reads that line.
4. **"Cannot be brought together by any dial setting" overstates.** Joint plain-words block, front page, summary. For gas metallicity the best setting leaves 1.7 noise units; I computed 0.078 dex rms there (one noise unit ≈ 0.041 dex). Black hole occupation is a real 0.46 fraction gap. The study page itself says "structural means beyond the scatter between two seeds, not physically large" (`study-joint` line 58), but the plain-words block, front page and summary do not. The minimum is at the box edge: my optimum has 4 of 8 dials exactly on the bounds, where the emulators are least tested (validation uses simulations within 0.5 of the fiducial cosmology).
5. **"The binding constraint is documentation, not physics"** (study-definitions abstract, README) is stated as a finding. `definition-budget.json`: 1,263 of 2,174 pairs (58%) are documented mismatches, only 466 (21%) are undocumented, and 0 of 16 tests survive correction; the analysis's own text says the data "neither show nor rule out" a definitional effect. Also the "4% of pairs" covers 7 relations and 5 epochs of this dataset, not "pairs of curves" in general.

## SHOULD-FIX

6. **Phone dials page does not "watch galaxies reshape".** At 390 px the last slider is at y=2095 and the first panel at y=3373 (page 11,575 px); only the one-line summary changes in view. Sliders are 16 px tall. Desktop is fine (`shots/dials3-desk.png`).
7. **First minute on the Explorer.** Direct visit opens on the star-forming main sequence, not the headline mass function, with a "New here?" box over the chart (`shots/explorer-desk.png`). "Try an example" then lists every published curve as x with "nothing is comparable until you declare definitions" (`shots/myrun2-desk.png`). After declaring, the group "FAIR TO COMPARE: YOUR DEFINITIONS AGREE" contains "~" rows whose reasons are "massDefinition: aperture-30pkpc vs aperture-50pkpc" (definitions differ). Raw field names (`sfrTimescaleMyr`, `caesar-6dfof-galaxy-total`, `instantaneous-200Myr` under "sfrStatistic"). At 390 px the bottom sheet takes ~60% of the screen (`shots/frontlink-mine-phone.png`).
8. **Glossary lacks the headline words**: structural, removable, rankable, dex, anchor, Subfind, Latin hypercube (0 hits in `glossary.html`).
9. **SFH plain words** say "removable by retuning". The analysis has the V4 SIMBA validation failing (1.51 against a limit of 1.5), the minimiser at the edge in 3 of 8 coordinates, and 0.13 dex left when ranges are cut to a quarter. "2.2 times as much" is stated before the hedge although the registered test was not met (phi 0.34, 90% CI -0.27 to 0.61).
10. **Observation-tuning one-liner is selective**: "neither reaches black hole mass (2.5 to 4.5)" rests on 2 curves with 3 to 5 bins. The same table has sSFR at z=2.15 at 4.4 / 5.9, Baker+25 mass function at 5.9 / 3.9, stellar metallicity 1.6 / 2.0. "Within one unit" for the mass function means ~0.2 dex.
11. **"Best any dials" is not the minimum for some families.** Registered search: shmr 1.53, fgas 0.371, sfms 1.107; the second implementation in `joint-robustness.json` and my L-BFGS-B get 1.38, 0.342, 1.059. No verdict changes, but the dials page shows the higher numbers.
12. **Pre-registration is weak evidence.** Harmonization: protocol 10:46, amendment A2 (new operator) 11:11, result 11:21, same day, git dates only (`SCEPTIC.md` #8 admits). The all-at-once structure/conflict split is a knife edge: point ratio 2.74422 against control 95th percentile 2.74429. Calibration: all 27 synthetic runs inject into one family (bhocc), 9 of the 17 negatives have true D=0.
13. "82 observational sources" = 77 observation + 5 empirical-model (UniverseMachine, Behroozi13, Moster13, ...).
14. Every page loads Google Fonts, so each visit sends the reader's IP to Google; at odds with "nothing leaves your browser" in spirit (the curve itself stays local; verified: no non-font external request).

## NICE
Legend "11 simulations" vs header "8"; "1 observational curves" (alt text); front-page caption counts 1 observational curve while the legend says "observations (4)"; Explorer first load 5.4 MB (`curve-index.js` ~5 MB); tab bar clipped at 390 px ("Di"); Explorer default z=0 SFMS plot is crowded.

## First minute, three visitors
- **(a) TNG-like PhD student:** clicks "Check your own run" (front page, 2nd tile). Gets the GSMF panel; must hand-pick ~6 definitions from raw-key dropdowns, with a "fill in like a published simulation" shortcut that helps. Stuck: nothing helps turn a snapshot into the curve (scripts exist, unsurfaced); the TNG digitized curve is "context only" so the closest comparison gives no verdict. Words: IMF, aperture, rankable, tier.
- **(b) z~8 observer:** the try-this link (`#r=gsmf&z=8`) works, 7 curves + 1 observation, slider sits on z=8 (`shots/z8-desk.png`). But the JWST observable is the UV luminosity function, not offered there; badges (O/C/T/F/D) and "variants off (49)" are unexplained.
- **(c) student:** dials page has a 30-second box and a tour button; the plain-language sentences are good. Stuck on phone (item 6); "gap", "noise unit", "structural" arrive before the glossary.
Speed: pages load in ~0.8 s locally; "make SIMBA look like TNG" settles in under 1.5 s. No page-level horizontal overflow at 390 px on front, study, quality, summary, dials pages.

## Claims audit
| # | Claim (page) | Verdict | Evidence |
|---|---|---|---|
| 1 | 1,699 records, 19 simulations, z 0-17 (front) | CONFIRMED | records.csv 1,699; 19 sim sources; max zRepresentative 17 |
| 2 | 82 observational sources (front) | WRONG label | 77 observation + 5 empirical-model |
| 3 | 55% of simulation curves digitized, none used for ranking | CONFIRMED | 792/1,433 = 55.3%; 0 of 792 rankable |
| 4 | 4% of 2,174 pairs fully matched; 21% unclassifiable | CONFIRMED | 97 (4.5%), 466 (21.4%) in definition-budget.json; "documentation is binding" not supported (item 5) |
| 5 | R=0.15, CI -1.04 to 0.51, p=0.11 | CONFIRMED | 0.1508, -1.0408, 0.5063, 0.1109 |
| 6 | Spread 0.17 to 0.37 dex, 2.2x; retuning 0.22 to 0.08 dex | CONFIRMED | 0.1686, 0.3688; D_fiducial 0.218, D_full 0.0794; caveats item 9 |
| 7 | Joint distance 4.8 | CONFIRMED | 4.848 raw, 4.819 corrected, half-sample median 4.77 |
| 8 | 169 outputs at z = 0 to 2.15 | WRONG | includes z=3 and 4 (item 3) |
| 9 | 2 of 11 structural, 6 removable, 3 borderline | CONFIRMED | J2 in joint-reachability.json |
| 10 | Two properties cannot be closed by any dial setting | OVERSTATED | 1.7 units = 0.078 dex (gas Z); item 4 |
| 11 | 0 of 17 below 0.95 structural, 8 of 8 above 1.1 | CONFIRMED | power.json rows; but see item 12 |
| 12 | Leave-one-out 3.7 to 5.2; weightings 4.5 to 5.4; without lowest two bins 2.5 | CONFIRMED | 3.72-5.20; 4.52-5.43; 2.49 |
| 13 | Dials: 2,054 simulations; 245/255 validation runs | CONFIRMED | 2 x (1,000 + 27); retune.json validation.n_test |
| 14 | Front figure: 6 sims reach 9, span 0.5 dex, +0.2 dex vs observation | CONFIRMED | I get 6, 0.54, +0.20; rests on 1 observational curve |
| 15 | Quality: 41 amber cells | CONFIRMED | 41 of 160 (plus 53 empty: 59% of cells under 3 sims) |
| 16 | Reading error median 0.01, max 0.05 dex | UNVERIFIABLE | author-declared field (`declared_uncertainty_dex`); only 1 of 792 has an independent check, and vector paths reproduce plotted points, so the real risk is wrong curve/run, not reading |
| 17 | Neither code reaches black hole mass (2.5 to 4.5) | CONFIRMED, selective | 2.49-4.52, n=2 curves; item 10 |
| 18 | "Independent review preceded the run" | MISLEADING | item 2 |
| 19 | Novelty | NOT CLAIMED on site | study page and SCEPTIC #7 say it is consistent with CAMELS papers; "not established as new" |

## Spot checks (re-derived)
- **4.8 noise units:** the dials page's definition (weights 1/n_block, noise scale per output) from `retune.json`. I confirmed `scale` = max(0.02, sqrt(seedT²+seedS²+emT²+emS²)) to 6e-6. At the fiducial point D=6.346 (page 6.35). Minimising over the 8-dial box (60 L-BFGS-B starts): 4.84806 against the study's 4.84807 raw. Reproduced. The 4.82 on the page is the amendment-A1 corrected figure; I did not re-derive that.
- **Digitized share:** 792/1,433 = 55.27%, 0 rankable. Reproduced. Also reproduced the front-figure caption numbers and the 0/17, 8/8 calibration counts.

## Weaknesses of the tests (read, not run)
- `test-export.mjs`: toy z-independent fit; never exercises the `records.map(...)` call site; passes with bug 1.
- `test_claims.py`: only README and OVERVIEW prose, substring matches at 1 decimal (4.77, 4.82, 4.85 all pass as "4.8"); site pages and dials page unchecked; typed strings in `site-joint.mjs` pass unseen.
- `test-parity.mjs`: JS emulator against Python from the same coefficients; checks transcription, not emulator quality at the box edge. `test-ui.mjs:252` accepts any best match between 4.5 and 5.3.
- `test_registration.py`: compares date-only strings from a generated file; same-day order always passes.
- Nothing tests digitized curves against sources except one pair; `test_vector_figure.py` is synthetic.

## Biggest gaps
1. **Outside checking.** Zero external review of 792 digitized curves; PROJECT.md success measures 1-3 not met; "nobody outside the project is known to have used it".
2. **Direct validation at the minimiser.** Compare emulator against the nearest of the 1,000 LH runs to my optimum, or CAMELS's extreme-parameter runs (to my knowledge they exist; not checked here), and a higher-resolution pair. Without this "structural" is "structural for these emulators".
3. **A bridge from my run to a verdict.** Snapshot to curve with correct definitions is the PhD student's real task; the extractors exist (`derive_*_relations.py`) but are outside the page's flow.

## Verdict
I would use the Explorer and the dataset's definition columns as a reading aid, but not the exported tables until bug 1 is fixed. I would recommend it to a colleague only with the caveat that curves are unreviewed, and I would not repeat the "cannot be closed" headline without the 0.08 dex and edge-of-box qualifications. The statistics are carefully done and mostly reproduce; the problems are in wording that outruns the evidence and in undisclosed AI involvement. The single change that would most raise my confidence: fix and test the export, then get two outside simulators to check 60 digitized curves, and state plainly what the "independent review" was.
