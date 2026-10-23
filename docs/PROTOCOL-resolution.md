# Protocol: how much does a model's published output change with resolution?

Status: **pre-specified**. Written on 2026-10-23 **before** any difference between two resolutions was computed for any curve (section 8 lists exactly what had been looked at). The analysis code (`scripts/analyze_resolution.py`) implements this text; every departure is listed under "Deviations" in `docs/ANALYSIS-resolution.md`, which the code generates and which reports whatever comes out. This is a sixth, smaller study. It is an internal check: no outside expert has reviewed this text, the code or the result. It does not amend any registered study and does not change their code, tests or outputs; it reads one saved result of the joint-reachability study and calls its noise functions unchanged.

## 1. The question

The joint-reachability and quenching-shape studies name resolution as their largest open weakness: CAMELS boxes are 25 Mpc/h with 256^3 dark matter and 256^3 gas elements, and nothing in the project measures how much a model's output changes when only the resolution changes. CAMELS is not run at a second resolution, so that cannot be measured on CAMELS itself. What can be measured is how published curves of other models change between resolutions of the same model, using the dataset's own records, and how large that change is next to two numbers the project already has:

* the **seed noise** of the CAMELS observables (the scale in which the joint-reachability study states every distance), and
* the **distance between IllustrisTNG and SIMBA** that the joint-reachability study reports for the same kind of observable.

Questions:

* **P1 (how many curves are converged).** Over the pairs of resolutions that differ in nothing else that the records state, how many are converged, resolution-dependent or cannot be told, by the rule of section 4?
* **P2 (resolution shift against the code difference; the primary comparison).** For the pairs whose observable has a counterpart in the joint-reachability study, is the resolution shift, in the same noise units, smaller or larger than the TNG-SIMBA distance of that observable?
* Reported beside them, not decided by them: the dex shifts for every pair that can be built (section 3), the size of the step from the coarser to the finer rung of each ladder (does it shrink?), and the pairs that could not be built and why.

What this study cannot say is stated in section 9: it is not a convergence test of CAMELS, of IllustrisTNG or of SIMBA at CAMELS resolution, and different papers use different galaxy finders and apertures.

## 2. Data and the rule that decides which pairs exist

### 2.1 Records

All records of `data/curves/*.json` with `kind` = simulation and a `points` representation (parametric fits are not evaluated). Nothing is added to the dataset by this study. Rungs and pairs come from the record `id` and `run` strings of the ladder table (2.3) and are checked against the record fields.

### 2.2 Inclusion rule

Two records A (coarser rung) and B (finer rung) of one ladder form an **epoch-pair** if all of the following hold:

1. their ids are equal after the rung token (and, where listed, the box token) is replaced by `*` (this fixes the relation, variant, figure and panel);
2. the ladder lists the rung of A as immediately coarser than the rung of B (adjacent pair), or A and B are the first and the last rung of a ladder with three rungs (span pair);
3. `relation` is equal and `|zRepresentative(A) - zRepresentative(B)| <= 0.1` (comparable epoch);
4. `axes` (the two definitions and the two units) are equal;
5. `definitions` are equal, with one listed exception: the free-text `dustCorrection` of the THESAN ladder (the THESAN-2 text says "same dust scaling" where the THESAN-1 text spells the scaling out; they describe the same correction);
6. both curves have at least 3 points inside their common x range (otherwise the epoch-pair is listed as built but not evaluated).

A **unit** is the set of epoch-pairs that share the ladder, the two rungs (and the two boxes, in the ladder where the same rung exists in two boxes), the relation and the id with the epoch removed. Units, not epoch-pairs, are what is counted: the epochs of one ladder are not independent. Adjacent-step units are counted in the primary outcomes; span units are reported beside them.

### 2.3 Ladders (written before any shift was computed)

Rung order is coarse to fine. "Box" and "parameters" are what the records or the registry (`data/simulations.json`, `data/model-variants.json`) say; where they say nothing the entry is *not stated*, never inferred.

| ladder | ids (rung token in braces) | rungs | box | parameters | relations |
|---|---|---|---|---|---|
| `tng-l25n` | `pillepich18.tng-l25n{128,256,512}.fiducial.sfrd` | n128, n256, n512 | same: 25 Mpc/h, one shared initial-condition realization (record warning) | unchanged: "resolution only" (record warning) | sfrd |
| `illustris-l25n` | `pillepich18.illustris-model-l25n{...}.fiducial.sfrd` | n128, n256, n512 | same (as above) | unchanged: "resolution only" | sfrd |
| `colibre-l025-gsmf` | `chaikin26.colibre.l025m{7,6,5}.gsmf.z*` | m7, m6, m5 | same: L025 (run strings) | recalibrated at each resolution (`model-variants.json`: "subgrid parameters recalibrated to the same data at each resolution ... weak convergence") | gsmf |
| `flamingo-l1` | `schaye23.flamingo-l1_m{10,9,8}.*` | m10, m9, m8 | same: 1 cGpc (record warnings) | recalibrated by the authors (`model-variants.json`) | gsmf, shmr, bh, sfrd, quenched, ssfr, zstar, size |
| `thesan` | `kannan22.thesan.{sfrd,uvlf}.t{2,1}[.z*]` | THESAN-2, THESAN-1 | same: one box in the registry (95.5 cMpc) | not stated | sfrd, uvlf |
| `colibre-boxes` | `schaye25.colibre.{sfrd,ssfr,shmr}.m{7,6,5}-l*[.z0]` | m7, m6, m5 | differs (L400, L200, L025) | recalibrated | sfrd, ssfr, shmr |
| `colibre-quenched` | `chaikin26.colibre.quenched.m{7,6,5}.z*` | m7, m6, m5 | differs (L400, L200, "L025, L050 or L100") | recalibrated | quenched |
| `colibre-mzr` | `sharda26.colibre-{m7,m6,m5--l025}.mzr.z*` | m7, m6, m5 | not stated for m6 and m7 | recalibrated | mzr |
| `eagle-furlong15`, `eagle-schaye15`, `eagle-crain17`, `eagle-lagos15`, `eagle-mzr` | EAGLE Ref-L100N1504 and Recal-L025N0752 (ids by paper, see the code) | Ref, Recal | differs (L100, L025) | not stated (the run name is "Recal") | gsmf, quenched, bh, ssfr, stfr, hi-fraction, h2-fraction, mzr |
| `tng-donnari21`, `tng-mzr` | TNG300-1 and TNG50-1 | TNG300, TNG50 | differs by name | not stated | quenched, mzr |
| `magneticum` | `magneticum.box{0mr,2hr,2bhr,3uhr,4uhr}.*` | mr (Box0), hr (Box2, Box2b), uhr (Box3, Box4) | differs by name | not stated | bh, bhsigma, gsmf, jstar, sfms, shmr, size, zstar |
| `illustris-sparre15` | `sparre15.illustris-{lowres,1}.*` | "low resolution" (run not named in the record), Illustris-1 | not stated | not stated | sfms, ssfr |

**Tier A** is the first five ladders: the box is stated to be the same, so the shift is resolution (and, where the parameters were recalibrated, the effect of the authors' recalibration, which is how those models are meant to be used: weak convergence). **Tier B** is every other ladder: box, sample or run is different or not stated, so a shift cannot be attributed to resolution alone. The verdict rule treats the two tiers differently (section 4).

Expected structure, enumerated before any shift was computed (epoch-pairs with comparable epoch, equal axes; definitions equal except the one listed exception): `tng-l25n` 2 adjacent, `illustris-l25n` 2, `colibre-l025-gsmf` 18, `flamingo-l1` 22, `thesan` 6, `colibre-boxes` 7, `colibre-quenched` 12, `colibre-mzr` 12, EAGLE 24, TNG300/TNG50 12, `magneticum` 130, `illustris-sparre15` 8 (adjacent pairs only; span pairs are added for the three-rung ladders).

### 2.4 Examined and not built (reported as such)

* FIREbox (one resolution in the dataset), FIRE-2, Romulus25, BlueTides, ASTRID, SPHINX, FLARES: no second resolution of the same model.
* Horizon-AGN and NewHorizon: the dataset registers them as separate families (NewHorizon with its own exclusions in `model-variants.json`); the records do not state that the model is unchanged.
* NIHAO zoom suite and NIHAO-UHD: different galaxy samples and different definitions.
* DARWIN-1 (box) and DARWIN-2 (selected zoom-ins): different galaxy samples and different ids.
* SIMBA `m100n1024` against `hires` (Glowacki+20 fits): parametric records, not evaluated.
* EAGLE colour counts (Ref-L0025N0376, Ref-L0100N1504, Recal-L0025N0752): one point per record, no curve.
* THESAN-SDAO-2 is a different dark matter model, not a resolution.
* TNG100 against TNG50 or TNG300 and Illustris-2/-3: no record pairs them with equal definitions.

### 2.5 A second source of one model at two resolutions

Checked on 2026-10-23 (no account, key or password used):

* IllustrisTNG data pages: "In order to access any Illustris[TNG] data, you need to first Login." Not used.
* EAGLE public database: "Access to both the database and particle data require only a single account, which you can register for below." Not used.
* FLAMINGO: the page links to a separate data portal and lists lightcone particle data and maps; no credential-free galaxy catalogue was found. Not used.
* THESAN: the project page has no data statement. Not used.
* COLIBRE paper data: `https://colibre.strw.leidenuniv.nl/paper_data/2509.07960.yml` is served without credentials, and the file is already in the repository as `data/raw/2509.07960.yml` (the source of the dataset's COLIBRE mass functions, SHA-256 recorded in those records). It holds the galaxy stellar mass function (`gsmf_raw`) of COLIBRE at m5, m6 and m7 in the boxes L025, L050 and L100, at m6 and m7 in L200 and at m7 in L400. The dataset holds L025 at m5, m6, m7 and single other members. This study therefore reads, as a **supplementary set** that is reported separately and does not enter the counts of section 5, the three-rung ladders of L050 and L100 and the two-rung ladder of L200 from that file with the reduction of `scripts/ingest_colibre_gsmf.py` (bins whose lower edge exceeds 100 baryonic particle masses, Poisson intervals from the published counts). They repeat the L025 comparison in other volumes. Nothing is added to `data/curves`.

## 3. Metric

All quantities are computed for each epoch-pair and aggregated per unit.

* **Shift.** With y_coarse and y_fine the y values of the coarser and the finer rung, the shift is d(x) = y_fine(x) - y_coarse(x) at points x of the common x range. The other curve is read by linear interpolation inside its own x range (no extrapolation). Units: dex for a log y (every y whose unit contains `log`), the fraction itself otherwise. A shift of d dex is a factor 10^d.
* **Own-point grid (dex statistics).** The points of the coarser curve inside the common range; if the coarser curve has fewer than 3 there, the points of the finer curve. Reported: rms, mean (signed) and largest absolute shift, and the number of points. These are reported for every epoch-pair that has at least 3 points.
* **Reference noise.** The noise scale s_k of the joint-reachability study, `s_k^2 = sigma_TNG,k^2 + sigma_SIMBA,k^2 + e_TNG,k^2 + e_SIMBA,k^2` with a floor of 0.02 (`analyze_joint_reachability.noise_scale`), computed with the unchanged functions `load_galaxies`, `eligibility` and `build_emulators` on `data/ensembles/camels-galaxies.json`, with the emulator degrees stored in `data/analysis/joint-reachability.json`. The relation-to-family map is fixed here: gsmf to gsmf, quenched to qf, ssfr to sfms, mzr to mzr, zstar to zstar, size to size, bh to bhms (all in bins of 0.25 dex in M* between 10^9 and 10^11.5, at bin centres), shmr to shmr (bins of 0.25 dex in M200c between 10^11 and 10^13), sfrd to the SFR density output of rho and smd to its stellar mass density output (evaluated at the snapshot redshifts). Every other relation has no counterpart. The CAMELS definitions differ from those of the compared records (for instance, CAMELS M* is the total bound stellar mass, the compared records often use an aperture; the CAMELS `sfms` is the median sSFR of galaxies with SFR > 0): s_k is used as a *unit*, not as a claim that the compared records have this scatter.
* **Reference grid.** For an epoch-curve, the CAMELS snapshot is the one with |z - zRepresentative| <= 0.15 (z = 0, 0.95, 2.15, 3, 4; the closest; of several epoch-curves of one unit that map to the same snapshot only the closest to it, the lower z in a tie, is a reference epoch-curve). The evaluation points are the centres of the eligible CAMELS bins of that block that lie in the common range (for sfrd and smd, the snapshot redshifts inside the common range); the epoch-curve is a reference epoch-curve only if there are at least 3. Every other epoch-curve is evaluated with the yardstick.
* **Yardstick.** Y0 = the median of s_k over all 186 eligible outputs of the joint-reachability study, used as a uniform noise scale on the own-point grid for relations without a counterpart or without enough eligible bins. It is "a typical CAMELS seed-to-seed difference of one output", nothing more.
* **Digitization.** delta = sqrt(u_A^2 + u_B^2) with u = the record's `provenance.digitizationUncertaintyDex` where present, 0.02 for a digitized figure without it, 0 for a table.
* **Noise-unit shift of a unit.** R^2 = the mean over its counted epoch-curves (reference epoch-curves if the unit has any, otherwise all, with the yardstick) of the mean over the evaluation points of (d/s)^2, equal weight to each epoch-curve; the corrected R_c^2 = max(0, R^2 minus the same mean of (delta/s)^2) (the digitization noise removed in quadrature, as the emulator variance was in the joint-reachability study). R is in the same unit as the joint-reachability distance: one unit is the standard deviation of the difference between one run of each of the two CAMELS codes.

## 4. Labels

For a unit with at least one counted epoch-curve, with the margin m = 1 noise unit (the margin of the joint-reachability study):

* **Tier A:** *converged* if R < m; *resolution-dependent* if R_c > m; otherwise *cannot tell*.
* **Tier B:** *converged* if R < m (the box also differs, so a small shift means that both effects are small unless they cancel; the label carries the qualifier "box also differs or not stated"); otherwise *cannot tell* (a large shift cannot be attributed to resolution).
* A unit without a counted epoch-curve is *cannot tell* (too few points).

The basis of the label (reference noise or yardstick) is always reported; a yardstick label is a label of the shift against a typical CAMELS noise and is not part of P2. The labels are not significance tests: the only uncertainty in R is the digitization, and R_c is the lower end of that range.

## 5. Outcomes

* **P1.** The counts of the three labels over the adjacent-step units of tier A, in total and per ladder, with the number of units that rest on the reference noise.
* **P2 (primary comparison).** For each tier A adjacent-step unit with a counted reference epoch-curve and a counterpart family f: the ratio of R_c to the TNG-SIMBA distance of f in `data/analysis/joint-reachability.json` (`point` of `fam:f`, field `D_fiducial` for a ladder whose parameters are *unchanged*, field `D` for *recalibrated* or *not stated*; both ratios are reported for every unit). The primary result is the number of such units with a ratio of at least 1 (the shift between two resolutions is at least as large as the distance between the two codes), the median ratio, and the list.
* **Reported whatever they show:** every unit of every ladder with its label and its dex statistics, including tier B and the units that could not be evaluated; the span units; for each three-rung ladder and relation the ratio of the finer step's R_c to the coarser step's (below 1: the step shrinks); the supplementary COLIBRE boxes; the pairs examined and not built (2.4); the sources that could not be used (2.5). No unit is dropped after its shift is known.
* The TNG model at L25n256, the CAMELS resolution (25 Mpc/h with 256^3 elements), to L25n512 is reported as a named unit, because it is the one step that starts at CAMELS resolution; the Illustris model likewise.

## 6. Checks (reported; a failure is stated with the qualification, and no noise-unit number is reported if the first one fails)

* **C1.** The reference reproduces the saved study: the median seed noise of each code from the rebuilt emulators equals the stored one to 1e-9.
* **C2.** The SHA-256 of `data/raw/2509.07960.yml` equals the checksum in the dataset's COLIBRE mass-function records.
* **C3.** The code run on a curve against itself gives zero shift, and on a curve shifted by a known amount returns it (also in `scripts/test_resolution.py`).

## 7. Sensitivity (reported, not used to choose)

S1 the dex statistics on the finer curve's own points in place of the coarser's; S2 the label counts at the margins 0.5 and 2; S3 the label counts without the epochs with z > 2.

## 8. What had been looked at before this was written

* The run names, relations, epochs, x ranges, numbers of points, tiers, definitions and notes of the records of the ladders above, and the ladders' presence or absence. No y value of any ladder was compared with another, and no shift or ratio was computed for any pair.
* The structure of `data/raw/2509.07960.yml` (the names of its runs and its redshift keys), not its values.
* From the joint-reachability result: the per-family distances (`point`), the headline, the noise summary, and, from a test of the reference (rebuilt emulators of fixed degree), the median seed noise (equal to the stored one), the median noise scale over the 186 eligible outputs (0.065) and the noise scales of the first three blocks (0.07 to 0.37). These say how large a noise unit is; none concerns a resolution.
* Expectation written down before the run, not strong: the tier A pairs whose parameters were recalibrated are close, in the range above each run's own resolution limit, because the authors recalibrate to the same data; the TNG and Illustris-model star formation histories at fixed parameters differ more at high redshift than at low redshift; the code difference is larger than most resolution shifts for observables where the joint-reachability distance is large (metallicities, black hole occupation) and not for those where it is small (the mass function, the quenched fraction, the densities). A different result will be reported as it comes out.

## 9. Limitations declared in advance

1. **Internal check, nothing external.** No outside expert has reviewed this protocol, the code or the result.
2. **CAMELS is not tested at a second resolution.** The shifts are those of other models (TNG and the Illustris model in a 25 Mpc/h box, COLIBRE, FLAMINGO, THESAN and others), taken from the papers' curves. They show how large such shifts are; they do not say what CAMELS IllustrisTNG or SIMBA would do at a higher resolution, and SIMBA has no evaluable pair in the dataset.
3. **Different papers, finders and apertures.** A pair compares two curves of one paper, so the galaxy finder, aperture and mass definition are those of that paper. The noise unit is from CAMELS Subfind catalogues with total bound masses and is applied as a unit to curves with other definitions. Nothing here compares across papers.
4. **Curves are cut at the authors' resolution limits.** Most records keep only the part of a curve above a resolution limit (for the COLIBRE tables, bins above 100 baryonic particle masses; for FLAMINGO, "the solid segment only ... above the resolution-dependent lower mass limit"). The common range is therefore above the limit of the coarser run, which is where convergence is best. The shifts below the limit, where resolution matters most, are not in the data; this study underestimates the effect there by construction.
5. **Recalibration.** Where the authors recalibrate at each resolution, a small shift is the result of that recalibration and is not a statement about the unchanged model.
6. **Shared initial phases.** Rungs in one box share their initial conditions where the records say so; the shift then excludes sample variance and is not the difference between two independent boxes.
7. **Digitized figures.** Most curves are vector-path extractions of figures (tier digitized-figure, not rankable), accurate to the plotted line; linear interpolation between their points is assumed.
8. **Few independent ladders.** There are five tier A ladders; epochs and relations within a ladder are correlated. Counts of units are counts of reported rows, not independent tests, and no p-value is given.
9. **Noise units are a convention.** A shift of one unit is not a physical tolerance; R, R_c and the dex statistics are given so that other readings can be made.

## 10. Amendments

None yet. Any amendment will be dated and made before the first result file exists.
