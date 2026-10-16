# The numbers to look at on the review date

`docs/PROJECT.md` sets the success measures and the stopping rule. This page says exactly where each number comes from, so the review takes ten minutes and nobody argues about what counts. **The clock starts the day the pilot is sent** (write that date here when it happens: `____-__-__`). Review at 4, 8 and 12 weeks, and at 6 months.

| # | measure | where to count it | today |
|---|---|---|---|
| 1 | Outside people who complete "check my run" unaided in under 5 minutes (target 3 of 3, 4 weeks) | the pilot log, `docs/outreach/pilot-log.md`, task 3 of `docs/outreach/PILOT.md` | 0 sessions held |
| 2 | Researchers outside the project who say unprompted they would use it again (target 2, 8 weeks) | the pilot log, question 1 and 5; any reply to the announcement | 0 |
| 3 | Digitized curves checked by someone who knows the source simulation (60 sampled records, 2 checkers, 8 weeks) | replies to `docs/audit-packet/COVER-NOTE.md`; `docs/CORRECTIONS.md` | 0 checked (the packet is ready, not sent) |
| 4 | Corrections or new-curve requests from people we do not know (target 3, 12 weeks) | GitHub issues from accounts that are not the maintainer: `https://github.com/ShubhanBhatia42/sim-highline/issues?q=is%3Aissue+-author%3AShubhanBhatia42` | 0 |
| 5 | A published citation or mention (target 1, 6 months) | `data/used-in.json` (filled from the "used in" form); a search of the DOI on ADS and Google Scholar | 0 |

Things that do **not** count, on purpose: page views, stars, downloads of the files, releases, tests, features.

## Also look at

- Zenodo: views and downloads of the record (context only).
- The weekly rot check: has it opened an issue (broken links, a failing chain)?
- `docs/ROADMAP.md`: what is still blocked on a person.

## The decision

Apply `docs/PROJECT.md` as written. In short: at 8 weeks, if none of measures 1 to 3 is met and nobody outside has opened an issue, archive it as a documented dataset (keep the DOI and the live pages) and build nothing more. If more than 10% of sampled records are wrong beyond the stated tolerance, withdraw the digitized curves until fixed. Write the decision and the date at the bottom of this page.

Decision: ______________________   Date: __________
