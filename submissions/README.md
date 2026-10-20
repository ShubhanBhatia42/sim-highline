# Submissions

One folder per curve, containing `metadata.json` and a CSV (`x,y` and optionally `yLow,yHigh`). Copy `_template/`, fill it in, and open a pull request that changes only files under `submissions/`. A check runs on the pull request (`node scripts/submission.mjs check submissions/<folder>`) and tells you what is missing or implausible. A maintainer reviews the numbers against the source and merges the record into the dataset; the folder is then removed.

Read `docs/SUBMIT-A-CURVE.md` first: what is accepted (numbers from a table or a data release; not curves read from a figure), which definitions you must state, and what happens to your numbers.
