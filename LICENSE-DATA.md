# Data licence

The sim-highline dataset (`data/curves/`, `data/export/`, `data/*.json`, and the documentation in `docs/`) is licensed under the **Creative Commons Attribution 4.0 International** licence (CC BY 4.0): <https://creativecommons.org/licenses/by/4.0/legalcode>.

The code (everything else, including `scripts/`, `highline/`, `site/`, `sim_highline.py`) is under the MIT licence in `LICENSE`.

## What the licence covers

- the curation: the selection, organisation, definitions, provenance fields, audit and export format;
- values the project transcribed from paper tables or read from published figures. These are facts reported by the original authors. The licence does not take credit for them: **cite the original paper** (every record carries `citation` and `doi`; `sim-highline-citations.bib` lists them).

## What it does not cover

Records whose `terms` field is set (a `terms` column in the exports) are the ones below; `sim_highline.open_terms(df)` filters them out.

- records ingested from third-party data releases keep the terms of those releases. The ones with stated terms are listed in `docs/SOURCE-TERMS.md`; where none is stated the values are treated as published results to be cited, and the owners were not asked;
- figures, text and images in the cited papers, which belong to their publishers and authors.

## How to attribute

Cite the dataset (see `CITATION.cff`, or the Cite box in the beta) and the original papers of the records you use. Where an author or collaboration publishes its own table, prefer it to a digitized record.
