# Data card: sim-highline scaling-relation evidence

**What it is.** A curated set of galaxy scaling-relation curves from cosmological simulations (and observational references) with exact epochs, native axis definitions, structured definitions, provenance and a rankable flag. Exports: `data/export/` (records and points tables, full JSON, BibTeX, manifest with checksums); loader: `sim_highline.py`.

**Composition.** Counts by suite, relation and tier are generated, not typed here: `data/coverage-report.json` (coverage), `data/audit-report.json` (quality checks), `data/export/sim-highline-manifest.json` (records, points, version, checksums). `data/sources-catalogue.json` lists every source and its status.

**How it was collected.** Public tables and catalogues where they exist; otherwise values transcribed from paper tables or read from the vector paths of the published figures (see `METHODS.md`). Nothing was simulated, fitted or interpolated by sim-highline. Missing epochs stay missing.

**Intended uses.** Seeing what each simulation predicts for a relation and redshift, checking whether two curves are comparable, pulling a consistent table into pandas for analysis, and finding where evidence is missing.

**Not intended for.** Ranking simulations with digitized-figure records, treating zoom selections as volume complete, or merging curves with different definitions into one number without reading the compatibility notes.

**Known biases and gaps.** Suites differ in resolution, volume, mass aperture, IMF and SFR timescale. Observations carry their own selection. Coverage is uneven: catalogue-level TNG and EAGLE runs, Magneticum boxes beyond Box4/uhr and several zoom suites remain open (`CLAUDE.md`, `data/literature-backlog.json`). UV luminosity functions (five simulations) and the cosmic SFR density (nine) are recent additions, and the UV functions of the simulations differ in dust treatment.

**Quality control.** Calibration assertions in every digitizer, in-script spot checks against published numbers, a repository-wide audit with an accepted-issues file, deterministic regeneration of every digitized record, unit tests for the extraction helper, the exporter and the loader, and a stable expert-audit sample.

**Versioning.** `data/release.json` holds the dataset version; `CHANGELOG.md` records changes. A DOI is not yet minted.

**Licence and citation.** Code MIT (`LICENSE`), dataset CC BY 4.0 (`LICENSE-DATA.md`); inputs from third-party data releases keep their own terms (`docs/SOURCE-TERMS.md`). Records reproduce values from the cited papers and data releases: cite those (the `citation` and `doi` columns, `sim-highline-citations.bib`) together with this dataset (`CITATION.cff`).
