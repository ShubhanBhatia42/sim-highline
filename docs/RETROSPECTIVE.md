# Retrospective: what the 200-task push did and did not do

Written 2026-10-16, at the end of the roadmap in `docs/ROADMAP.md`. It is an account of what is true, not a pitch. The numbers are counted from `data/roadmap-status.json`.

## What was asked

After the project was judged "ok and nowhere close to great", the request was: draft a ten-step plan and two hundred tasks of varying effort, tier them, and do them. The plan had one idea underneath it: the project had been built far more than it had been used, so the work should make it trustworthy, easy to start, and ready to put in front of people, and should say plainly what a decision to continue or stop would rest on.

## What changed, in plain terms

- **The data is more honest about itself.** A data-quality page states that 55% of simulation curves were read from published figures by one person, that only one of them has an independent table to check against, and that nobody outside the project has reviewed any record. A plausibility screen flags curves that sit far from their peers; a corrections log exists; an audit packet and a cover note are ready to send to an expert.
- **The first minute works.** Plain page titles, a one-time guide in the Explorer, "try this" links that are tested to land where they say, a one-page summary that prints on one sheet, a five-step tour of the dials page, plain words for the jargon (rankable, tier, tension, spread), and a plain-words paragraph with a one-sentence result at the top of every study.
- **The dials page and "check your run" do more and break less.** Fit the dials to your own curve or to an observation, hold one property fixed, share a link, export numbers and a figure; messy inputs are tested.
- **The science was pressed harder, and held.** A second implementation of the distance, another kind of emulator and other weightings all gave about the same answer (4.85, 4.91, 3.8 to 5.4). A third code (Astrid) shows the headline is closer to "SIMBA stands apart on black hole occupation" than "TNG against SIMBA". Without the two lowest mass bins the headline falls from 4.8 to 2.5, so it leans on the faintest galaxies. All of this is in `docs/ROBUSTNESS-joint-reachability.md`, `docs/CHOICES-joint-reachability.md`, `docs/SCEPTIC.md` and `docs/RESEARCH-NOTE.md`, and on the study page under "Checks made after the run".
- **It is sturdier.** Pages are tested at five widths in light, dark and print; by keyboard only; with broken data, no JavaScript, no network and reduced motion; under a content security policy; on a slow phone with a speed budget. The offline checks run in about four minutes from scratch (the joint-reachability test alone used to take ten). The emulators the page evaluates are tested against the full analysis emulators. The build is deterministic. A lint found and fixed a real defect (an invalid number in a JSON file).
- **It is ready to send.** Announcement, pilot script, forum post, talk outline, registry and software-catalogue text, author emails and permission requests are drafted from the data. Every page has a prefilled feedback link.

## What did not change

- **Nobody outside the project is known to have used it.** That is the single fact that decides whether this is worth continuing, and nothing in this push changed it. The success measures in `docs/PROJECT.md` are all still at zero.
- **No record has been checked by an outside expert.** The audit packet exists; sending it needs the maintainer.
- **The headline result is modest and for two codes at CAMELS resolution.** It is a careful measurement of something the CAMELS papers already report in outline (the codes differ), with a size and a per-property answer added. Whether that is new to the field has not been established by anyone who knows the literature.
- **Several tasks need a person, not code**: sending the audit packet, the three pilot testers, a CAMELS team member's read of the note, a DOI for the analysis data, registry submissions, presenting it, tagging a release after the merge.
- **Not everything was verified where it matters.** Firefox and WebKit are in the CI configuration but were never run here; the release script's file edits were tested on a copy but the script was not run end to end; the full re-run of the two registered analyses from the saved catalogues was not repeated in this push (the saved outputs are tested for staleness every time).

## What went wrong along the way

- Early in the push the wrong question was answered twice (a push, then one study) when the question was about the whole project, and shorthand the maintainer does not remember was used. The pages and notes are now written for someone who has not read the code.
- At least one wrong claim had to be corrected (a noise unit is not about 0.04 dex everywhere; it is 0.04 to 0.18 dex). Several features were built first and then found to break an existing test, mostly because a new piece of text repeated a button's name or a new element was nested in the wrong container; the layout test caught a long DOI overflowing at 320 px. All were fixed before commit, but they are a reminder that the tests, not a reading of the code, are what catches these.
- A review of the whole project after the plan was finished found what the tests did not: the downloadable files had carried a wrong redshift for 91 curves since version 0.8.0, the abstracts quoted a redshift range that was typed by hand and wrong, and several sentences said more than the evidence allowed. These are fixed (see `docs/INDEPENDENT-REVIEW.md` and `docs/CORRECTIONS.md`). The lesson is that a green test suite is not a review.
- The tests grew faster than the evidence of use. That is the central risk of the project: it is easy to keep improving what has no audience.

## Counts

See the table at the end of `docs/ROADMAP.md` for done, partial, blocked and skipped by tier. The tier-4 tasks, which are the ones that put the project in front of people, are the ones that remain.

## What I would do next, in order

1. Send it to three people who run or compare simulations this week, using `docs/outreach/PILOT.md`, and write down what happens. Nothing else is as informative.
2. Send the audit packet (`docs/audit-packet/COVER-NOTE.md`) to one expert who knows one of the simulations.
3. Merge the branch to `main` so the live site matches this work (then check it, tag the release, deposit the analysis data for a DOI).
4. Apply the stopping rule in `docs/PROJECT.md` on the review date, whatever it says.
