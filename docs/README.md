# Documents

Fifty documents is too many to find anything in, so here they are by what you want to do. Files marked *generated* are written by a script and must not be edited by hand; *dated* files say what was true on the day they were written.

## If you have two minutes

- [OVERVIEW.md](OVERVIEW.md): the problem, what the project does, and what it does not claim.
- [DATA-CHANGES.md](DATA-CHANGES.md) *(generated)*: what was changed in the data and what was not (IMF, cosmology, axis units, the observation compilation).
- [CORRECTIONS.md](CORRECTIONS.md): every fix to the data, an analysis or a claim, newest first.
- [SCEPTIC.md](SCEPTIC.md): eighteen objections a sceptic would raise, with the answers.

## Using the data

- [METHODS.md](METHODS.md): where numbers come from, units, definitions, how curves are compared.
- [DATA-CARD.md](DATA-CARD.md): what is in the dataset, licences and intended use.
- [DATA-QUALITY.md](DATA-QUALITY.md) *(generated)*: how the curves were obtained, how many were read from figures, how well they check out.
- [UNDOCUMENTED-DEFINITIONS.md](UNDOCUMENTED-DEFINITIONS.md) *(generated)*: definitions no paper states, and which papers were read for them.
- [CONVERSIONS.md](CONVERSIONS.md) *(generated)*: what changes, measured in three codes, when an aperture or a weighting changes (stellar mass, SFR, metallicity, halo mass).
- [PLAUSIBILITY-SCREEN.md](PLAUSIBILITY-SCREEN.md) *(generated)*: curves that look odd next to the others.
- [SOURCE-TERMS.md](SOURCE-TERMS.md): terms of the third-party inputs.
- [EXPANDING-COVERAGE.md](EXPANDING-COVERAGE.md): adding catalogue-based sources on your own machine.
- [SUBMIT-A-CURVE.md](SUBMIT-A-CURVE.md): give us your published numbers as a table (a folder under `submissions/`, checked automatically).
- [literature-candidates.md](literature-candidates.md) *(dated)*: papers found by search and not added.

## The four studies (each: protocol written first, then the analysis)

| question | protocol | analysis | calibration / extras |
|---|---|---|---|
| How much of the disagreement is just definitions? | [PROTOCOL-harmonization.md](PROTOCOL-harmonization.md) | [ANALYSIS-harmonization.md](ANALYSIS-harmonization.md) *(generated)*, [ANALYSIS-definition-budget.md](ANALYSIS-definition-budget.md) *(generated)* | |
| What can retuning change in a simulated universe? | [PROTOCOL-model-form.md](PROTOCOL-model-form.md) | [ANALYSIS-model-form.md](ANALYSIS-model-form.md) *(generated)* | [POWER-model-form.md](POWER-model-form.md) |
| Can two simulated universes agree on everything at once? | [PROTOCOL-joint-reachability.md](PROTOCOL-joint-reachability.md) | [ANALYSIS-joint-reachability.md](ANALYSIS-joint-reachability.md) *(generated)* | [POWER-joint-reachability.md](POWER-joint-reachability.md), [CHOICES-joint-reachability.md](CHOICES-joint-reachability.md), [RESOLUTION.md](RESOLUTION.md) |
| (the same, checked after the registered run; exploratory) | | [ROBUSTNESS-joint-reachability.md](ROBUSTNESS-joint-reachability.md), [ANALYSIS-third-code.md](ANALYSIS-third-code.md), [ANALYSIS-tune-to-observations.md](ANALYSIS-tune-to-observations.md), [ANALYSIS-minimiser-check.md](ANALYSIS-minimiser-check.md), [RANKING-observables.md](RANKING-observables.md) *(all generated)* | [RESEARCH-NOTE.md](RESEARCH-NOTE.md), [RELATED-WORK.md](RELATED-WORK.md) |

## How the project works

- [ARCHITECTURE.md](ARCHITECTURE.md): how the pieces fit, in one page.
- [DECISIONS.md](DECISIONS.md): what was decided, why, and what would reverse it.
- [PROJECT.md](PROJECT.md): purpose, success measures and the stopping rule.
- [QUESTIONS.md](QUESTIONS.md): the ten questions a researcher brings; each is a test.
- [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md): what a release needs, and which parts only the maintainer can do.

## Reviews and plans (all dated)

- [INDEPENDENT-REVIEW.md](INDEPENDENT-REVIEW.md): a separate review of the whole project on 2026-10-16 and what was done about each finding.
- [REVIEW.md](REVIEW.md): the first candid review, at v0.5.0. Superseded by the line above and by DATA-QUALITY.md; kept as history.
- [ROADMAP.md](ROADMAP.md) *(generated)*, [RETROSPECTIVE.md](RETROSPECTIVE.md), [NEXT.md](NEXT.md), [INVENTORY.md](INVENTORY.md), [LANDSCAPE.md](LANDSCAPE.md): the 200-task plan, what it did and did not do, what would matter next, which pages stay, and what researchers do today.
- [REVIEW-DAY.md](REVIEW-DAY.md): the numbers to look at on the review date.

## Reaching other people

- [author-heads-up.md](author-heads-up.md), [author-requests.md](author-requests.md): drafts for the authors of the source papers.
- [expert-audit-request.md](expert-audit-request.md), [expert-audit-sample.md](expert-audit-sample.md), [audit-packet/](audit-packet/): the packet for an outside check of the digitized curves.
- [outreach/](outreach/) *(generated)*: pilot and announcement texts.
- [DEMO-SCRIPT.md](DEMO-SCRIPT.md): a 90-second demonstration of the dials page.
