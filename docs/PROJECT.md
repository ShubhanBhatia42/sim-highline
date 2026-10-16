# What sim-highline is for, and how we will know it is working

## Purpose

sim-highline lets a researcher put a galaxy-simulation result next to every published simulation and observation, and tells them which of those comparisons are fair. Two curves that look different may measure different things (a different aperture, IMF or population cut); every curve here carries the definitions that decide it.

## Who it is for

1. **A simulator** with a curve from their own run who wants to know how it sits against the field, and whether the comparison is legitimate.
2. **An observer or theorist** who needs what several simulations predict for one relation at one epoch, with sources they can cite.
3. **A student** learning what feedback does in a galaxy-formation model, who can turn the dials of two simulated universes and watch the galaxies change.

## Success measures

Each has a number and a review date. They are the only measures that count; page views and releases do not.

| # | measure | target | by |
|---|---|---|---|
| 1 | Outside people who complete the "check my run" flow unaided in under 5 minutes | 3 of 3 pilot users | 4 weeks after the pilot is sent |
| 2 | Researchers outside the project who say they would use it again, unprompted | at least 2 | 8 weeks |
| 3 | Digitized curves checked by someone who knows the source simulation | 60 sampled records, at least 2 checkers | 8 weeks |
| 4 | Corrections or new-curve requests from people we do not know | at least 3 | 12 weeks |
| 5 | A published citation or a mention in a paper, talk or software list | at least 1 | 6 months |

## Stopping rule

If at the 8-week review none of measures 1 to 3 has been met and nobody outside the project has opened an issue, the project is archived as a documented dataset (keeping the DOI and the live pages) and no further features are built. If measure 3 shows more than 10 % of sampled records wrong beyond the stated tolerance, the digitized curves are withdrawn from the public tables until fixed.

## What the project will not do

- It will not rank simulations or call one "best". Offsets are only verdicts where definitions agree.
- It will not synthesise a curve from a template or interpolate across missing epochs.
- It will not collect user data. "Your run" stays in the browser.
- It will not claim a scientific discovery from the studies; they describe what these data can and cannot show.
- It will not add more simulation suites faster than they can be checked.

## What the front page promises

"Put your simulated galaxy relation next to every published simulation and observation, and find out which of those comparisons are legitimate." Everything on the site either delivers that or supports it, or it is cut.
