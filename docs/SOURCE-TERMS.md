# Terms of third-party inputs

Records from sources with their own terms carry them in `provenance.terms` (a `terms` column in the exports; `data/source-terms.json` holds the rules and `scripts/annotate-definitions.mjs` applies them). A record with no `terms` is under the dataset licence (CC BY 4.0). In Python, `sim_highline.open_terms(df)` keeps only the records without third-party terms.

Flagged today: 88 records from the Sharda+26 release (GPL-2.0), 142 binned from the Garcia+24 catalogues (no licence file), 99 from the COLIBRE plot-data YAML and 3 from the FIRE-2 tables (both CC BY 4.0, compatible).

Sources whose terms are stated by their owners, as recorded in `data/sources-catalogue.json` and `data/ingestion-manifest.json`. For every other source no terms were found; the values reproduced are published results, cited per record.

| Source (catalogue id) | Stated terms | Note |
|---|---|---|
| Sharda+26 mass-metallicity data release (`sharda26-mzr`) | GPL-2.0 | Redistributed under its own terms, not CC BY. Records can be found by `Sharda` in the citation column. Consider asking the authors or excluding these records from a CC BY release. |
| COLIBRE stellar mass function YAML (`colibre-gsmf-chaikin26`) | CC BY 4.0 | Compatible with the dataset licence. |
| FIRE-2 tables, Wetzel+23 (`fire2-wetzel23-tables`) | CC BY 4.0 (paper tables) | Compatible. |
| Garcia+24 FMR catalogues (`garcia24-fmr-catalogues`) | none (repository has no licence file) | Cite the paper and repository; the owners should be asked before a public release. |

Official tables from collaborations (THESAN, Magneticum, velociraptor comparison data and others) are listed in `docs/RELEASE-CHECKLIST.md` step 2: copy each source's stated terms here when found.
