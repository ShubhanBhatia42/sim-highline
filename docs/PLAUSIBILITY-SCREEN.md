# Plausibility screen

`scripts/screen_outliers.py` writes `data/analysis/plausibility-screen.json`. It compares every curve with the median of the curves other sources publish for the same relation, units, metallicity quantity and redshift (within 0.15), at the curve's own x values, using peers only inside their published range and only where at least three other sources contribute. A curve is flagged when its median offset is at least 0.7 dex and at least 3 robust standard deviations from the relation's offsets.

It is a screen, not a check. It reads no source paper, so it cannot tell a transcription error from a real simulation difference or from a definition difference. Nothing is corrected or removed. A flag is a lead for someone who has the paper open.

## What it found (v0.20.0 data, 775 curves screened, 9 flagged)

| Record | Offset (dex) | What the record itself says |
|---|---|---|
| `dubois21.newhorizon.bh-mbh.z1` | -2.4 | Per-black-hole points within 2 R_eff, seed-mass floor near 1e4 Msun, zoom region. Peers are population medians. Expected: not like for like. |
| `diemer19.tng300.h2-fraction.z0` | -1.3 | Median over galaxies above the detection threshold only, band is the spread across nine HI-H2 transition models. Not explained by the record; check against the paper. |
| `schaye23.flamingo-l1_m10.gsmf.z0` | -1.2 | Includes 0.3 dex mock scatter and covers only the high-mass solid segment, where a steep exponential tail makes the offset large. Expected. |
| `baker25.qsmf.z2.5-3` | -0.8 | Quiescent-only mass function, flagged "not comparable with total GSMFs" in the record. Expected. |
| `katz23.sphinx20.size.uv-1500A.z5-7` | -0.8 | UV-1500A size against half-mass radii in the peers. Different size definition; the only source and relation the screen finds wholly offset. Expected. |
| `magneticum.box2hr.jstar.z0.official` | -0.7 | Morphology and aperture not specified in the table header. Not explained; a real lead for the Magneticum authors. |
| `schaye23.flamingo-l1_m10.size-active-ap100.z0.1` | +0.7 | Projected half-mass radius in a 100 kpc 2D aperture, active galaxies. Probably a definition difference. |

The Magneticum star-formation main sequence, flagged as suspect in an earlier review, is **not** flagged: its median offset from the other simulations at the same epoch is inside the thresholds. That is weak evidence against a gross error (a wrong unit, a shifted axis) and none against a subtler one, so it stays a context-only record until it is compared with the released source table.

## A bug the screen found in its own first run

ASTRID stellar metallicity is stored as 12 + log10(O/H), the other stellar-metallicity records as log10(Z/Zsun); both carry the unit "dex" and sat 8.6 dex apart. The records are correct (their `yDefinition` says which quantity). The screen now groups by metallicity quantity so they are no longer compared. Anyone mixing the two by unit alone would be wrong by 8.6 dex, so the quantity must be read from the definition, not the unit.

## Limits

- Needs three peer sources at the same epoch, so sparse relations (stellar Tully-Fisher, gas fraction, BH-sigma at most epochs) are largely unscreened.
- A shared systematic across all sources, or a consensus that is itself wrong, passes.
- Thresholds are conventions, not tuned on known errors.
