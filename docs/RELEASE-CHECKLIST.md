# Release checklist

Items marked **owner** need a decision only the maintainer can take; nothing here has been decided for them.

1. **Licence (owner).** None is chosen. The code and the dataset may need different licences (the dataset redistributes curves from published papers, official tables from collaborations, and compilations with their own terms: record each source's terms before choosing). Add `LICENSE` and a licence field to `CITATION.cff` and `data/release.json`.
2. **Source terms.** For each `official-table` and compilation source (THESAN, COLIBRE, Magneticum, velociraptor comparison data, Sharda+26), copy the stated terms into `docs/DATA-CARD.md`. Ask where none is stated.
3. **External check.** Send `docs/expert-audit-request.md` and record replies in `data/audit-outcomes.json`. State the number of externally checked records in the release notes.
4. **Author tables.** Send `docs/author-requests.md` wording to the first authors of the papers with most digitized records; replace records when tables arrive (tier `official-table`, checksum of the file).
5. **Verify.** The chain in `CONTRIBUTING.md`, then `python3 scripts/regress_digitizers.py` (all digitizers byte-exact).
6. **Version.** Bump `data/release.json`, add a `CHANGELOG.md` entry, rerun `node scripts/export-dataset.mjs`; the manifest SHA-256 values must match `data/export/`.
7. **DOI (owner).** Create a Zenodo deposit from the tagged release; add the DOI to `data/release.json` and `CITATION.cff`. `.zenodo.json` needs the licence from step 1, so it is not created yet.
8. **Announce small.** Five invited users (an observer, a simulator, a student, a modeller, a referee-minded colleague), one question each: what did you try to do, and where did you stop trusting it? Search ADS and GitHub before claiming "first".
