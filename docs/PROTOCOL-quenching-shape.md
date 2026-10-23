# Protocol: does the shape of the star-formation distribution separate two feedback models?

Status: **pre-specified**. Written on 2026-10-23 **before** the per-simulation distribution summaries of the Latin-hypercube simulations were ingested and before any distance, verdict or emulator for them was computed (section 8 lists exactly what had been looked at). The analysis code (`scripts/analyze_quenching_shape.py`) implements this text; every departure is listed under "Deviations" in `docs/ANALYSIS-quenching-shape.md`, which the code generates and which reports whatever comes out. This is a follow-up to the registered study of `PROTOCOL-joint-reachability.md` (S4) and uses its estimators unchanged; it is a fifth, smaller study, not an amendment of S4.

## 1. The question

S4 asked whether retuning four feedback parameters can make IllustrisTNG and SIMBA agree on every galaxy observable at once, and answered that they cannot (structural, 4.8 noise units apart), with the main weight on black hole seeding. Its star-formation outputs were two numbers per mass bin: the **quenched fraction** (specific SFR below 1e-11 per yr) and the **median specific SFR of galaxies with SFR > 0**. The distribution of galaxies around a main sequence has more structure than that: how many galaxies are *between* the blue cloud and the red sequence (the green valley), and how wide the blue cloud is.

Define two new outputs per stellar-mass bin (section 3), the **green-valley fraction** (`gv`) and the **width of the star-forming sequence** (`sfw`). Questions:

* **Q1 (shape alone).** Is the distance between the two codes, for the shape outputs alone, structural (above the noise and the same-code controls), removable (below the margin) or neither?
* **Q2 (shape beyond the usual two).** Does adding the shape outputs to the quenched fraction and the star-forming main sequence raise the distance between the codes by more than the split-to-split spread? That is: is there information about the codes in the shape that the median and the quenched fraction do not already carry?
* **Q3 (shape in the joint set).** The same, adding the shape outputs to all of S4's joint set.

## 2. Data

`data/ensembles/camels-distshape.json`, written by `scripts/ingest_camels_distshape.py` from the public CAMELS Subfind catalogues by HTTP range reads of three arrays (`SubhaloMassType`, `SubhaloLenType`, `SubhaloSFR`; the SHA-256 of their bytes is stored per simulation and snapshot): IllustrisTNG and SIMBA, the 1000 Latin-hypercube simulations (LH) and the 27 cosmic-variance simulations (CV) of each, at z = 0, 0.95 and 2.15. Simulation names, parameters and seeds are those of `camels-galaxies.json`. The other snapshots of S4 are not used: at z = 3 and 4 almost no S4 output was eligible.

## 3. Outputs

Galaxies are Subfind subhaloes with at least one star particle; M* is the total bound stellar mass; bins of 0.25 dex in M* from 10^9 to 10^11.5 Msun (ten, as in S4); specific SFR is the instantaneous SFR of all gas in the subhalo over M*, and a galaxy with zero SFR counts as quenched (below 1e-11). In each bin with at least 10 galaxies:

* `gv`: the fraction of the bin's galaxies with log10 sSFR between -11.0 and -10.5 (the two quenching thresholds already used elsewhere in the dataset);
* `sfw`: the 84th minus the 16th percentile of log10 sSFR among the bin's galaxies with log10 sSFR above -10.5 and SFR > 0, if there are at least 10 of them.

A bin that fails the count is missing (not zero). **Eligibility** is S4's: an output enters if it is finite in at least 90 % of the LH simulations of each code and in at least 20 of the 27 CV simulations of each code; a block (output family at one snapshot) enters with at least 3 eligible outputs.

## 4. Estimators

Exactly those of S4 (`PROTOCOL-joint-reachability.md` section 4 with amendment A1): per-code polynomial ridge emulators (degree chosen by cross-validation), the noise scale from the 27 CV simulations plus the emulator error, the distance minimised over both codes' four astrophysical parameters, matched-size splits with 100 random splits per set, the margin m = 1 noise unit, the emulator-variance correction at the minimiser, and the verdict rule (structural if the 5th percentile of the between-code distances exceeds both the 95th percentile of the pooled same-code controls and m; removable if the 95th percentile is below m; otherwise unresolved). The code reuses the functions of `analyze_joint_reachability.py` and does not change them. The sets are:

| name | blocks |
|---|---|
| `shape` | all eligible `gv` and `sfw` blocks |
| `sf2` | the eligible `qf` and `sfms` blocks of S4 |
| `sf2+shape` | `sf2` and `shape` |
| `joint` | S4's joint set (all eligible blocks of its 11 families, without `hmf`) |
| `joint+shape` | `joint` and `shape` |
| `hmf` | the S4 negative control |

* **Q1** is the verdict of `shape`.
* **Q2** compares `sf2+shape` with `sf2` **in the same splits**: for each split, the difference of the between-code raw distances D(sf2+shape) − D(sf2); "shape adds separation" if the 5th percentile of that difference exceeds 0 and the verdict of `sf2+shape` is at least as strong as that of `sf2`; "shape adds nothing detectable" if the 95th percentile of the difference is below 0.1 noise units; otherwise unresolved. The same differences are computed for the two same-code controls and reported beside it.
* **Q3** is the same with `joint+shape` against `joint`.

## 5. Validations (must hold for a conclusion without qualification; failures are reported with the qualification)

* **V1 (emulators).** The cross-validation error of the emulator is at most 1.5 times the seed noise for at least 80 % of the eligible shape outputs of each code.
* **V2 (negative control).** `hmf` is removable, as in S4 (the pipeline does not produce structural distances where there is none).
* **V3 (counts).** The share of eligible shape outputs that rest on fewer than 30 galaxies per bin in the median CV simulation is reported; if more than 25 % do, the verdicts of `shape` are stated as resolution-limited.
* **V4 (numerical stability).** Rerunning the point distance of `shape` with 8 instead of 4 random starts changes it by less than 5 %.

## 6. Calibration

The estimators are S4's, calibrated in `POWER-joint-reachability.md` on synthetic worlds with S4's block layout; no new calibration is done, and the shape blocks have a different layout (two families, up to three snapshots). This is a limitation (section 9), not a result.

## 7. Sensitivity analyses (reported, not used to choose)

S1 without the two lowest mass bins of each family (lower resolution); S2 `gv` alone and `sfw` alone; S3 the thresholds -11.5 and -10.5 in place of -11.0 and -10.5 for `gv` (this needs a second ingest of the same arrays and is reported if it is made).

## 8. What had been looked at before this was written

* The fiducial-parameter (CV) distributions of specific SFR in both codes, pooled over the 27 seeds (`data/ensembles/camels-distributions.json`, the Distribution view): in these, at the fiducial parameters, SIMBA has a larger quenched fraction than IllustrisTNG above 10^10 Msun and the median specific SFR of all galaxies falls lower. That is one point of the parameter space and says nothing about the reach of either code.
* S4's results (the joint distance is structural, with black hole occupation and mass carrying most of it; the star-formation families were not structural alone).
* Nothing about `gv` or `sfw` for any LH simulation, and nothing about any emulator of them.
* Expectation written down before the run: none strong. If SIMBA's jet-mode feedback leaves a different population in the green valley than TNG's kinetic mode at any parameters, `shape` would be structural; if the two codes can be tuned to each other's quenched fraction they probably can be tuned to each other's green-valley fraction. A different result will be reported as it comes out.

## 9. Limitations declared in advance

1. The limitations of S4 apply (two codes, 25 Mpc/h boxes at 256^3, the four parameters per code the CAMELS team chose, Subfind subhaloes rather than observed galaxies, differences in more than feedback).
2. Resolution: at the lower edge of the mass range a bin has a few hundred galaxies in the fiducial simulations and each galaxy has about 60 to 300 star particles; the green-valley fraction of a bin near the resolution limit may be driven by single particle events. Sensitivity S1 and validation V3 report this; the instantaneous SFR is noisy for the same reason.
3. Instantaneous SFR and zero-SFR galaxies: a galaxy with zero SFR is counted as quenched, so the quenched share and the green-valley share both depend on how often a code assigns exactly zero.
4. A distribution has more summaries than two. The choice of `gv` and `sfw` is made here, before the data, and a different choice (the position of the red peak, the colour) is a different study.
5. The estimators are not calibrated on this block layout (section 6).

## 10. Amendments

None.
