# Where things stand, and what to decide

Written 2026-10-16 at the end of the 200-task roadmap.

## In one paragraph

The project is now in much better shape than it was this morning: it is easier to start, more honest about its limits, and better tested. An independent review (by an AI agent, not a person) found a real bug in the downloadable files and several statements that went beyond the evidence; those are fixed or disclosed. What did not change is the thing that decides whether it is worth continuing: **nobody outside the project is known to have used it, and no outside expert has looked at a single curve.** More building will not change that. People will.

## What is done (175 of 200 tasks, 6 more partly; the full list is `docs/ROADMAP.md`)

- Trust: a data-quality page that says plainly how much of the data is solid and how much was read from figures; an audit packet ready to send; a corrections log; a plausibility screen.
- The first minute: plain page titles, a short guide in the Explorer, "try this" links that are tested, a one-page summary that prints on one sheet, a tour of the dials page, plain words in place of jargon, a one-sentence result and a plain paragraph on every study.
- Check your run and the dials page: more capable, with messy inputs tested; on a phone the dials page keeps a live copy of the chart under your thumb.
- The science, pressed harder after the registered run: a second implementation, another emulator, other weightings, a third code (Astrid), tuning to observations, a check on the emulators at the edge of the range. The headline held (4.8 noise units apart); it falls to 2.5 without the lowest-mass galaxies, and two properties stay apart at every setting tried (black hole occupation by a wide margin, gas metallicity by a small one).
- Sturdiness: every page at five widths, light, dark and print; keyboard only; broken data, no JavaScript, offline; a content security policy; a speed budget; the page's emulators checked against the analysis' emulators; a deterministic build; a lint. The offline checks take about four minutes (the slowest test went from ten minutes to under two).
- Ready to send: announcement, pilot script, forum post, talk outline, registry text, author emails and permission requests, prefilled feedback links on every page.

## What the independent review found, and what I did

See `docs/INDEPENDENT-REVIEW.md` (the report and a response table). The most important:

1. **A real bug in the downloadable files, there since version 0.8.0:** the `z` column of 91 curves and the points of four redshift-dependent fits were wrong in the CSV and JSON files. The Explorer and the studies were not affected. It is fixed and tested. **The Zenodo record of 0.23.0 still has it until a new version is deposited.**
2. **The project was made with an AI assistant and the "independent reviews" of two protocols were an AI agent, not a human expert.** The pages did not say so. They now do (Methods, FAQ, front page, summary, Explorer, README).
3. Wording that outran the evidence (a redshift range typed by hand, "no dial setting closes the gap", "documentation, not physics, is the binding constraint") was fixed.

## What is not done

- **Everything that needs a person** (10 tasks): send the audit packet to an expert, send the pilot to three people, ask a CAMELS team member to read the note, deposit the analysis data with a DOI, archive a new version on Zenodo, submit to registries, present it, and, on the review date, apply the stopping rule.
- **Merge to `main`.** Everything is on `claude/loving-noether-t977vy`. The live site is the old build: it does not have the FAQ, the one-page summary or any of the fixes above, and several links in the new pages point at documents that exist only on this branch. I did not push to `main`; say "push it" (or merge the branch) when you want it live. After that: check the live site, run `scripts/release.sh X.Y.Z "summary"`, tag, deposit on Zenodo.
- Never run here: Firefox and WebKit (configured, non-blocking in CI), the release script end to end, a human screen-reader check.
- Not fixed from the review: a bridge from a simulation snapshot to a curve; the size of the phone bottom sheet in "Your run"; the Google Fonts dependency (disclosed); a few cosmetic items.

## What to decide

1. **Merge now?** My recommendation: yes. The branch is verified from a clean checkout, and the live site currently has the unfixed export and the unqualified wording.
2. **Send the pilot this week** (`docs/outreach/PILOT.md`), and write the date at the top of `docs/REVIEW-DAY.md`. The stopping rule in `docs/PROJECT.md` then starts counting.
3. **Say whether you are comfortable with the AI disclosure** as written on the Methods and front pages. It is accurate as far as I can tell from the repository, but it is your project and your name on it.

## My honest view

The tool is competent and the statistics are careful, but the result it is built around is modest (the two codes differ, which CAMELS already reports; this adds a size and a per-property answer), the data is mostly unchecked, and there is no evidence yet that anyone wants it. If three simulation researchers try it and two would use it again, it is worth another round. If they shrug, the stopping rule you wrote is the right call, and the dataset and the pages are a reasonable thing to leave behind.
