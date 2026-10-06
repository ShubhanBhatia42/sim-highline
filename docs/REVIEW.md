# sim-highline: a candid review

Date: 2026-10-06, dataset v0.5.0. Numbers are computed from `data/curves/` and the audit report; nothing here is estimated.

## Verdict

sim-highline has a real but narrow reason to exist. It is a **definition-aware, citable lookup of published predictions**, with a clean export, and it is most useful where the alternative is opening a dozen papers and reading values off figures: high-redshift predictions, cross-simulation comparisons, and onboarding. It is **not** a benchmark, not a replacement for the authors' own data releases, and not yet independently verified. Presented that way it earns its place; presented as an arbiter of which simulation is right, it would not.

## Who would use it, and how well it serves them today

| Job | Fit now | Why |
|---|---|---|
| Observer planning a high-z (JWST) proposal or writing the "what simulations predict" paragraph | Strong, with a gap | 209 simulation records at z≥6 from 13 simulations, each with definitions and citation. Gap: JWST analyses compare UV luminosity functions and cosmic SFR density more than stellar-mass relations, and neither is in sim-highline. |
| Student or newcomer getting oriented in a relation | Strong | Per-relation summaries with past and present reviews, simulation-versus-data statements and the definition pitfalls; every curve opens to its source. |
| Writing a paper or thesis chapter | Good | Tidy CSV/JSON with units and definitions, BibTeX, SVG/PNG figures with a citation footer, state in the page link. |
| Simulator checking their own run against others | Medium | They can overlay their CSV and export others as pandas. Limits: 48% of simulation records are digitized from figures (precision is the plotted line, not the underlying data), and there is no scoring. |
| Modeller (SAM, empirical model, emulator) wanting calibration targets | Medium | Export and loader are good; the observational side is thin (234 records from 75 sources) and uneven across relations. |
| Someone ranking simulations against each other | Not served, on purpose | Digitized records are never rankable, and many pairs are flagged not comparable. This is the correct behaviour, but it will disappoint anyone expecting a leaderboard. |

## What already exists, and what sim-highline adds

Authors' data releases (TNG, EAGLE, COLIBRE, FLAMINGO, THESAN, Magneticum), simulation databases, compilations such as Speagle et al. 2014 and Popesso et al. 2023, UniverseMachine mock catalogues, and the figures in each paper. Someone with a TNG API key can compute any relation with the exact definition they want, so sim-highline adds little for them with respect to TNG. What none of those provide is **one place, one axis convention, one schema** across 19 simulations, with the definitions that decide comparability attached and flagged. The value is convenience plus the comparability flags, which is genuine but is the kind of value that disappears if the data go stale or are wrong.

## Data quality

- 1,315 records (1,081 simulation, 234 observational), 19 simulations, 75 observational sources, 111 distinct citations, 37,485 plotted points.
- Evidence tiers of simulation records: 515 digitized from figures (48%), 254 official tables, 190 catalogue-derived, 96 tabulated in papers, 26 published fits. Only 424 simulation records are rankable (39%).
- Definitions are incomplete: 432 simulation records (40%) have an unspecified mass definition and 105 an unspecified IMF. The compatibility check treats those as blockers or caveats, which is right but means many comparisons end as "not comparable".
- Extraction is exact to the file (vector paths, not raster tracing) and every digitizer regenerates its records byte for byte, but exactness is not truth: the figure shows the author's choices (binning, which runs are drawn, which population). Audit 0 errors/0 warnings means internal consistency and plausible ranges, not that each curve is the right one.
- The 36-record expert-audit sample (`docs/expert-audit-sample.md`) has not been reviewed by anyone who knows those simulations. Until it is, "verified" should be read as "checked by the maintainer and by scripts".
- Coverage is uneven: nine relations have four or more simulations; BTFR, STFR, gas fractions and several others have two or fewer. The page now says so.

## Product review

Strengths: every curve opens to provenance; state is in the URL; the export matches what is on screen; fiducial runs keep the default view readable; the compatibility marks and residuals make definition mismatches visible instead of hiding them.

Weaknesses: first-time users get no guided path (the About panel helps but is optional); the legend and Customise panel are dense; the compatibility verdict is often "not comparable", which is honest but offers no next step; interactive behaviour was tested at widths up to about 1,000 px and by scripted state checks, not with a user study or an accessibility audit; the fiducial-run logic and the panels have no automated unit tests; the single-file page embeds all data (3.9 MB), which is fine now but will not scale to ten times the records.

## Risks

- **Misuse:** curves cited without the paper. Mitigation in place: citation and DOI columns, BibTeX export, citation footer on figures, "context only" labels. Not solved: nothing stops screenshots without footers.
- **Staleness:** new releases (COLIBRE, FLAMINGO, MillenniumTNG, TNG-Cluster, new JWST data) arrive faster than one maintainer can digitize them.
- **Trust:** single maintainer, no peer review, no DOI, licence undecided.
- **Maintenance cost of digitization:** each figure takes judgement; replacing digitized records with authors' tables is the durable fix and needs outreach, not code.

## Recommendations, in order

1. Send the expert-audit sample to one person per suite for a ten-minute check, and record outcomes. This is the cheapest way to move from "maintainer-checked" to "externally checked".
2. Add the missing high-z observables: UV luminosity function and cosmic SFR/stellar-mass density, plus recent JWST stellar-mass and SFMS references. This is where the strongest user group lives.
3. Ask authors for their own tables for the most-used digitized curves; every replacement becomes an official-table record.
4. Choose a licence, mint a DOI (Zenodo), and publish the dataset with the changelog.
5. Add a contribution path ("add a source" template with the required fields and the digitizer helper).
6. Add a short guided start (three recipes: high-z prediction table, compare two simulations, build a pandas calibration set).
7. Add unit tests for the fiducial-run selection and panel logic; do an accessibility pass (focus order, labels, contrast).
8. Grow the observational anchors for the sparse relations before adding more simulation variants; depth beats breadth now.

## Should it exist?

Yes, on those terms. The test that matters is simple: would an observer or a student save an hour by using it, and would a careful reader trust what they find? The first is plausible today. The second depends on step 1 above, which costs a few emails.

## Addendum (2026-10-06): quick wins, the market, and whether it deserves a beta

**Quick wins on the sims-versus-observations theme (no redesign needed)**
1. A default observational anchor per relation (for example COSMOS-Web or Weaver et al. for the mass function, Speagle et al. for the main sequence, Curti et al. for O/H, McConnell and Ma for black holes), drawn bold, with each simulation's median offset from it in the legend. The residual machinery already exists; this makes the headline number visible without clicks.
2. A one-screen "tension map" (simulation by relation, offset from the anchor at a reference epoch). The full workbench already has a fingerprint view; porting a simplified version is cheap and is the most shareable picture the project could produce.
3. Show observational coverage in the Coverage view (today it shows simulations only).
4. Clean the observational metadata (two records still carry another paper's citation; 19 of 75 sources have no survey or facility entry yet).
5. Extract from the 2026 COLIBRE papers and the other relation-specific papers listed in `docs/literature-candidates.md`: several would fill the sparse relations (sizes and angular momentum, atomic gas, high-z sizes).
6. Per-line provenance is now visible (badge and tooltip); the next step is to replace digitized curves by authors' tables where authors agree.

**Market.** A web search (standard mode, three queries) found no dedicated interactive tool that puts several simulations and observations on one axis with definitions attached. It did find the neighbours: Encyclopedia Magneticum (28 relations, one suite, a paper), the EAGLE SQL database, the TNG data API and public releases, the UniverseMachine DR1 (observational compilations and mocks), CAMELS, compilations such as Speagle et al. 2014 and Popesso et al. 2023, and comparison papers such as Davé et al. 2020 (cold gas in EAGLE, TNG and Simba) and Habouzit et al. 2021 (black holes). A short search is not proof of absence; ask colleagues and search GitHub and ADS before claiming "first".

**Does it deserve a beta?** Yes, as a small invited beta, not an announcement. It is already honest about being unreviewed; before a wider release it needs (1) the expert-audit sample reviewed by at least a few people who know those simulations, (2) a licence and a DOI, (3) the two metadata fixes above. Ask five invited users (an observer, a simulator, a student, a modeller, a referee-minded colleague) one question each: what did you try to do, and where did you stop trusting it?

## Status (2026-10-06, dataset v0.6.0: 1,408 records, 1,142 simulation, 49% of those digitized)

What was done against the recommendations and the quick wins above, and what was not.

| Item | Status |
|---|---|
| 1. Expert audit | Packet written (`docs/expert-audit-request.md`, outcomes file `data/audit-outcomes.json`); **not sent**: needs the maintainer. Until replies exist, "verified" still means maintainer-checked and scripted. |
| 2. High-z observables | UV luminosity function and cosmic SFR density added. Observations: Bouwens+21, Harikane+23, Donnan+24, Madau & Dickinson 2014. Simulations: UV functions from THESAN, FIRE-2, FLARES (z 10-15); SFR density from THESAN, ASTRID, EAGLE. Thin (three simulations for the UV function, six for the SFR density), dust treatment differs between simulations and is a hard comparability key. New JWST stellar-mass references were not added beyond COSMOS-Web. |
| 3. Author tables | List generated (`docs/author-requests.md`: 30 papers, 552 digitized records); **no email sent**. |
| 4. Licence, DOI | `docs/RELEASE-CHECKLIST.md`; **both are the maintainer's decisions** and neither is made. |
| 5. Contribution path | `CONTRIBUTING.md` and `scripts/digitizer-template.py`. |
| 6. Guided start | Three recipes in the About overlay (high-z prediction, compare two simulations, calibration set). |
| 7. Tests and accessibility | Fiducial-run, epoch, offset and anchor logic extracted to `highline/logic.js` with unit tests. Accessibility pass: skip link, dialog and tab semantics, focus return, chart description, contrast of secondary text above 4.5:1 in both themes. Checked by scripted browser sessions and a computed contrast table only; no screen-reader or user test. |
| 8. Observational anchors for sparse relations | Each relation now has a default anchor; the sparse relations (Tully-Fisher, gas fractions) still have one or two observational sources. Not done. |
| Quick win 1: anchor and offsets | Done (bold line, offset beside each simulation, compatibility marks against the anchor). |
| Quick win 2: tension map | Done as a simplified Tension view (fiducial run per simulation, selectable reference redshift). |
| Quick win 3: observational coverage | Done (Coverage view). |
| Quick win 4: metadata | Four upstream citations corrected with the original kept (`provenance.upstreamCitation`); all 82 observational sources now have a survey or facility entry, drafted from titles, abstracts and compilation labels and not checked with the authors (two are simulation-calibrated theory curves and are labelled as such). |
| Quick win 5: literature extraction | Davé+20 gas fractions, Glowacki+20 BTFR fits, Rodriguez-Gomez+22 j*, FLARES V UV functions, Kannan+22, Furlong+15 and Bird+22 SFR density, Ma+18 UV functions. Others stored in `data/literature-backlog.json` as queued or skipped with the reason (Shen+24 and the ASTRID UV function are raster figures). |
| Quick win 6: authors' tables | Same as item 3. |

Limits to keep in mind: digitized records are as precise as the plotted line; the FIRE-2 UV function is the weighted zoom sample; the THESAN UV curves had a display offset of -(z-8) dex added back; the SIMBA BTFR table does not state the baryonic mass composition beyond the paper's definition; the Tension view compares each simulation's fiducial run, so an offset where definitions differ is not a verdict on the simulation.

### Update (2026-10-07, dataset v0.7.0: 1,460 records, 1,194 simulation, 51% of those digitized)

Queued papers were extracted or closed: Marszewski+24 (redshift-evolving FIRE-2 MZR), Baker+24 and Weinberger+17 (nothing that fits an existing relation; skipped with the reason). Sparse relations grew where a vector figure or table allowed it: SFR density now has six simulations, UV luminosity function three, baryonic Tully-Fisher four (adds SIMBA and an APOSTLE + EAGLE fit), HI and H2 fractions three each, specific SFR six, angular momentum five (adds COLIBRE and TNG). Still thin: stellar Tully-Fisher (two simulations), total cold gas fraction (two), black hole mass-dispersion (three). Papers that would help but could not be extracted honestly (raster figures, or fits without a stated range) are listed with the reason in `data/literature-backlog.json`: Thomas+19 (SIMBA M_BH-sigma), Ferrero+17 (EAGLE stellar Tully-Fisher), Shen+24 (THESAN sizes), Huppenkothen+26 (COLIBRE HI).

### Update (2026-10-07, later: dataset v0.9.0: 1,552 records, 1,286 simulation, 50% of those digitized)

Literature work continued from the backlog. Papers with published tables were transcribed rather than digitized (BlueTides Wilkins+17: six relations; FLARES Vijayan+21 UV functions), and vector figures were read for FLARES and Illustris SFR density, THESAN-ZOOM (mass function, UV function, SFR density), Illustris Tully-Fisher points and Horizon-AGN size and sSFR. Illustris now has baryonic and stellar Tully-Fisher points (per galaxy, not rankable), so stellar Tully-Fisher has three suites (EAGLE, NIHAO, Illustris) and baryonic Tully-Fisher five. 31 of 184 backlog papers are ingested; the remaining candidates are untriaged beyond their titles.
