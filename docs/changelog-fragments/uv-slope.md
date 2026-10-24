# Changelog fragment: uv-slope

Bullets for the changelog:

- New relations: the UV continuum slope beta against UV magnitude (`uvbeta`; the id was already registered in the schema and the comparability rules) and against stellar mass (`uvbetam`, new id). 37 records from 6 papers (3 transcription scripts and 2 digitizers): observations from the tables of Bouwens+12 and Bouwens+14 (HST, z ~ 4 to 8, 9 records), Topping+24 (JWST/JADES, binned medians and the paper's linear fits, 7 records) and, against stellar mass, Finkelstein+12 (5 records); simulations IllustrisTNG (Shen+20, z = 4, 5, 6, with all dust and without the resolved dust, 6 records) and SIMBA (Wu+20, z = 6: four dust treatments against M_1500, two boxes with the 1 sigma spread, four dust treatments against stellar mass, 10 records). The comparability rule makes the wavelength window or filters of the beta measurement and the dust treatment (attenuated or intrinsic) hard keys, so a simulation curve and an observed curve are compared only when both match; each source states its own window, so most pairs will show as not comparable on that key until more sources share one.
- The Explorer lists both relations under "Cosmic history"; each has a note (`data/relation-notes.json`), observation profiles for the five new observed sources, and four catalogue entries.
- Digitized figures (IllustrisTNG, SIMBA; 16 records, none rankable): axes calibrated on tick marks, with the minus signs of the tick labels taken from their vector paths; each figure is checked against numbers printed elsewhere (the Bouwens+12 and +14 points drawn in the same panels reproduce the tables of those papers, the Finkelstein+12 points reproduce its Table 5, legend line styles match their labels, bars end on their caps, the paper's own sentences about the flat no-dust slope hold), 40 checks in all.

Hand-written counts changed by this work (for whoever edits the changelog, README and docs):

- Evidence records validated by `scripts/validate-curves.mjs`: 1872 to 1909 (+37). Relations with a note: 43 to 45. Observational sources with a profile: 102 to 107 entries.
- `data/audit-known.json` gains one accepted finding (the combined SIMBA curves with other dust laws against the Calzetti curve of one box: a dust-law effect, not a disagreement).

Sources considered and not ingested, with the reason (internal reading only; no outside expert has reviewed this):

- Bouwens+14 z ~ 8.5 (one bin) and Finkelstein+12 Table 4 (beta against M_UV): the first is a single point, the second is binned in L/L* with M* from other papers, not in M_UV; not stored.
- Topping+24 F150W dropouts: stored as a one-point record because the paper gives one bin; the paper gives no fit for it.
- Dunlop+13 (HUDF12), Bouwens+09, Bhatawdekar & Conselice 2021, Rogers+14, Cullen+23, Nanayakkara+23, Austin+24, Topping+22: not read in enough depth to quote a definition and a table; at most their captions or table titles were looked at. Not rejected on the merits; open work.
- FLARES II (Vijayan+21, arXiv:2008.06057, `beta_lum_z5_10.pdf`, weighted median and 16 to 84 per cent band at z = 5 to 10 against M_1500, vector figure) and FLARES V (Wilkins+23, arXiv:2204.09431, `beta2.pdf`): both are vector figures that look usable and were not digitized for lack of time; FLARES V `beta.pdf` contains a raster image.
- BlueTides (Wilkins+16, arXiv:1605.05044; Wilkins+17, arXiv:1704.00954): the first gives the intrinsic slope against redshift only, the second has no UV slope; nothing against M_UV or stellar mass.
- FIRE-2 (Ma+19, arXiv:1902.10152): the figure files are PNG; no vector beta figure found.
- THESAN, SPHINX, Astrid, EAGLE, Illustris(TNG) other than Shen+20, Kannan-type papers: searched by title and abstract only; no beta against M_UV or M* table or vector figure was found, but the figures of these papers were not all opened.
- Shen+20 "without the resolved dust" curve: stored with its own dust label ("birth-cloud dust only") because the paper says the unresolved dust of the MAPPINGS-III library is always present, so it is not intrinsic in the sense of the other sources.
