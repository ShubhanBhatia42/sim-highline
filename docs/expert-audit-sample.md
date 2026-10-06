# Expert audit sample

Records for an independent check by someone who knows each suite. Selection is deterministic (two records per simulation source, different relations, digitized figures first, ordered by a hash of the id), so the list is stable between releases of the same data. 37 records from 19 sources.

For each record: open the cited figure or table, confirm (1) the curve is the one named (run, population, panel), (2) the axis values at two labelled ticks, (3) the definitions block (mass aperture, IMF, SFR timescale, halo definition), and (4) that the epoch is the published one. Report disagreements with the record id.

| source | record | relation | z | tier | citation |
|---|---|---|---|---|---|
| ASTRID | `bird22.astrid.shmr.z6` | shmr | 6 | digitized-figure | Bird et al. 2022, MNRAS 512, 3703, figure smhm (arXiv source numbering), z=6 |
| ASTRID | `bird22.astrid.zstar.z3` | zstar | 3 | digitized-figure | Bird et al. 2022, MNRAS 512, 3703, figure stellar_metal (arXiv source numbering), z=3 |
| BlueTides | `wilkins17.bluetides.ssfr.z10` | ssfr | 10 | published-table | Wilkins et al. 2017, MNRAS 469, 2517 (arXiv:1704.00954), Table physical (median sSFR) |
| BlueTides | `wilkins17.bluetides.shmr.z12` | shmr | 12 | published-table | Wilkins et al. 2017, MNRAS 469, 2517 (arXiv:1704.00954), Table DM_stellar |
| COLIBRE | `ludlow26.colibre.size.all-sf.z2` | size | 2 | digitized-figure | Ludlow et al. 2026, COLIBRE sizes and angular momentum (arXiv:2603.26200), size and j_star versus stellar mass at z=0 to 3 |
| COLIBRE | `ludlow26.colibre.jstar.cen-sf.z2` | jstar | 2 | digitized-figure | Ludlow et al. 2026, COLIBRE sizes and angular momentum (arXiv:2603.26200), size and j_star versus stellar mass at z=0 to 3 |
| EAGLE | `lagos17.eagle.jstar.z0.5` | jstar | 0.5 | digitized-figure | Lagos et al. 2017, MNRAS 464, 3850 (arXiv:1609.01739), j_stars-M_stars relation at several redshifts, z=0.5 |
| EAGLE | `furlong15.eagle-recal.gsmf.z0.5` | gsmf | 0.5 | digitized-figure | Furlong et al. 2015, MNRAS 450, 4486, Fig. 2 (arXiv source numbering) panel 2 |
| FIRE-2 | `ma18.fire2.uvlf.z12` | uvlf | 12 | digitized-figure | Ma et al. 2018, MNRAS 478, 1694 (arXiv:1706.06605), predicted luminosity functions at 1500 A, z=12 |
| FIRE-2 | `ma18.fire2.gsmf.z5` | gsmf | 5 | published-table | Ma et al. 2018, MNRAS 478, 1694, Table of stellar mass functions (Appendix) |
| FIREbox | `sharda26.firebox-firebox.mzr.z0` | mzr | 0 | published-table | Sharda et al. 2026, COLIBRE gas-phase MZR (data repository) |
| FLAMINGO | `schaye23.flamingo-gsmf.planck-nu0p24var.z0` | gsmf | 0 | digitized-figure | Schaye et al. 2023, MNRAS 526, 4978, SMF_2_Panel right panel (model variations) |
| FLAMINGO | `schaye23.flamingo-l1_m8.zstar.z0.1` | zstar | 0.1 | digitized-figure | Schaye et al. 2023, MNRAS 526, 4978, galaxy-properties figure (galaxy_props_z01), zstar |
| FLARES | `wilkins22.flares.uvlf.intrinsic.z13` | uvlf | 13 | digitized-figure | Wilkins et al. 2023, MNRAS 519, 3118 (arXiv:2204.09431), far-UV luminosity function at z=15 to 10, intrinsic, z=13 |
| FLARES | `vijayan21.flares.sfrd.obscured` | sfrd | 7.5 | digitized-figure | Vijayan et al. 2021, MNRAS (doi 10.1093/mnras/staa3715; arXiv:2008.06057), composite star formation rate density |
| Horizon-AGN | `kaviraj17.horizon-agn.gsmf.z5` | gsmf | 5 | digitized-figure | Kaviraj et al. 2017, MNRAS (doi 10.1093/mnras/stx126), Fig. 7 (arXiv source numbering; mf.ps), z=5 panel |
| Horizon-AGN | `dubois16.horizon-agn.size.z3` | size | 3 | digitized-figure | Dubois et al. 2016, MNRAS 463, 3948 (arXiv:1606.03086), size-mass relation of Horizon-AGN galaxies at different redshifts |
| Illustris | `genel14.illustris-1.gsmf-r2.z3` | gsmf | 3 | digitized-figure | Genel et al. 2014, MNRAS 445, 175, Fig. 3 (arXiv source numbering) |
| Illustris | `sparre15.illustris-lowres.sfms-median.z2` | sfms | 2 | digitized-figure | Sparre et al. 2015, MNRAS 447, 3548, main-sequence evolution figure (Fig81), z=2 |
| IllustrisTNG | `dave20.illustristng.ssfr.tng100-1.z0` | ssfr | 0 | digitized-figure | Dave et al. 2020, MNRAS 497, 146 (arXiv:2002.07226), specific star formation rate versus stellar mass at z=0 |
| IllustrisTNG | `habouzit21.tng3001.bh.z1` | bh | 1 | digitized-figure | Habouzit et al. 2021, MNRAS 503, 1940 (arXiv:2006.10094), median MBH-M* relation of all simulations, z=1 |
| Magneticum Pathfinder | `magneticum.box0mr.bhsigma.z0.official` | bhsigma | 0 | official-table | Dolag et al. 2025, Encyclopedia Magneticum |
| Magneticum Pathfinder | `magneticum.box0mr.gsmf.z0.official` | gsmf | 0 | official-table | Dolag et al. 2025, Encyclopedia Magneticum |
| NewHorizon | `dubois21.newhorizon.gas-n10.z1` | gas | 1 | digitized-figure | Dubois et al. 2021, A&A 651, A109 (arXiv:2009.10578), cold gas fraction versus stellar mass, z=1 |
| NewHorizon | `dubois21.newhorizon.size-galaxies.z2` | size | 2 | digitized-figure | Dubois et al. 2021, A&A 651, A109 (arXiv:2009.10578), effective radius versus stellar mass, z=2 |
| NIHAO zoom suite | `blank21.nihao.sfms-fit.z4` | sfms | 4 | digitized-figure | Blank et al. 2021 (NIHAO XXVI), MNRAS, SFR-M* figure (fig:sfr_mstar_zx4), z=4 panel |
| NIHAO zoom suite | `blank19.nihao-bh.shmr-fit.z2` | shmr | 2 | digitized-figure | Blank et al. 2019, MNRAS 487, 5476, Fig. 1 (arXiv source numbering), z=2 panel |
| Romulus25 | `ricarte19.romulus25.bhsigma-galaxies.z0.05` | bhsigma | 0.05 | digitized-figure | Ricarte et al. 2019, MNRAS 489, 802, SMBH mass vs velocity dispersion (msigma_2panel; arXiv source numbering), Romulus25 |
| Romulus25 | `ricarte19.romulus25.sfms-galaxies.z1` | sfms | 1 | digitized-figure | Ricarte et al. 2019, MNRAS 489, 802, SFMS figure (sfms; arXiv source numbering), Romulus25 panel z=1 |
| SIMBA | `habouzit21.m100n1024.bh.z0` | bh | 0 | digitized-figure | Habouzit et al. 2021, MNRAS 503, 1940 (arXiv:2006.10094), median MBH-M* relation of all simulations, z=0 |
| SIMBA | `dave19.simba-m100n1024.gsmf.z5.9` | gsmf | 5.9 | digitized-figure | Dave et al. 2019, MNRAS 486, 2827, Fig. 4 (arXiv source numbering), z=5.9 panel |
| SPHINX20 | `katz23.sphinx20.size.uv-1500A.z10` | size | 10 | catalog-derived | SPHINX20 public data release (Katz et al. 2023; Rosdahl et al. 2018, 2022); medians derived by sim-highline |
| SPHINX20 | `katz23.sphinx20.shmr.virial.z8` | shmr | 8 | catalog-derived | SPHINX20 public data release (Katz et al. 2023; Rosdahl et al. 2018, 2022); medians derived by sim-highline |
| THESAN-1 | `kannan22.thesan.uvlf.t1.z7` | uvlf | 7 | digitized-figure | Kannan et al. 2022, MNRAS 511, 4005 (arXiv:2110.00584), UV luminosity functions at z=6-10, z=7 |
| THESAN-1 | `kannan22.thesan.sfrd.t1` | sfrd | 10 | digitized-figure | Kannan et al. 2022, MNRAS 511, 4005 (arXiv:2110.00584), evolution of the star formation rate density |
| THESAN-zoom | `kannan25.thesanzoom.gsmf.z8` | gsmf | 8 | digitized-figure | Kannan et al. 2025, OJAp 8 (arXiv:2502.20437), galaxy stellar mass function, 7.5 <= z < 8.5 |
| THESAN-zoom | `kannan25.thesanzoom.uvlf.fiducial.z10` | uvlf | 10 | digitized-figure | Kannan et al. 2025, OJAp 8 (arXiv:2502.20437), UV luminosity function, 9.5 <= z < 10.5 |
