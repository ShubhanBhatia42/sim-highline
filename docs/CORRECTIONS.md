# Corrections

Every change that fixed something wrong in the data, an analysis or a claim, newest first. A correction that changes a number someone may have used is listed here and in the changelog. To report one, open an issue (the curve-error form).

| release | what was wrong | what changed |
|---|---|---|
| 0.23.0 | The dials page and the all-at-once study stated the distance only in noise units, which hides how large it is in the units of each property. | Gaps are shown in dex and fractions beside the noise units; one noise unit is 0.04 to 0.18 dex depending on the property. |
| 0.22.0 | The harmonization analysis (0.21.0) applied the site's IMF offsets as if they were a definitional difference between simulations. They are a convention for comparing a simulation with an observation. | The framing is withdrawn; the later analysis applies no IMF conversion to simulated quantities. The conclusion (not detected) did not change. |
| 0.21.0 | The EAGLE aperture figure's legend says 10, 30 and 100 pkpc while its caption says 30, 50 and 100. | The legend, which is what is drawn, is used, and the records say so. |
| 0.20.0 | The NewHorizon all-galaxy mass-function squares were drawn 0.15 dex off the data bins. | The offset is removed and asserted on every bin. |
| 0.20.0 | The plausibility screen compared ASTRID stellar metallicity (12 + log O/H) with other suites (log Z/Zsun) because both are labelled "dex", 8.6 dex apart. | The screen groups by metallicity quantity. The records were correct. |
| 0.20.0 | The definition-budget analysis picked a different group on ties depending on the Python hash seed. | Ties resolve in sorted order, which is what the earlier data produced; no result changed. |
| 0.20.0 | The digitizer regression reported every record with a sourced definition fill as different. | It ignores exactly the definition keys the committed record carries; all 82 digitizers now reproduce their records. |
