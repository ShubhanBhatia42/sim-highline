# sim-highline in two minutes

**The problem.** When you publish a galaxy simulation you compare its curves with other simulations and with observations. But a curve is only comparable with another if they measure the same thing: the same stellar-mass aperture, the same assumed initial mass function, the same galaxies selected. Papers usually state some of this, not all, and reading values off figures takes an afternoon per paper.

**What this does.**
1. **A curated set of published curves**, simulations and observations, with the definitions that decide comparability beside every curve and a label for how each was obtained (official table, paper table, fit, or read from a figure).
2. **Check your own run.** Paste your curve and say what it measures. It shows which published curves are fair to compare with, the offsets against them, and a CSV and BibTeX for what you plotted. Nothing leaves your browser.
3. **A dials page.** Two well-known simulated universes, IllustrisTNG and SIMBA, each have four feedback dials. Move them and watch eleven galaxy properties respond (the curves are fast emulators fitted to 2,054 small simulations). Ask whether one universe can be made to look like the other: some properties yes, a few never.
4. **Four small studies** that use the data to ask what definitions can and cannot explain, with the rule written before the result and the limits stated.

**What it is not.** A ranking of simulations, a source more accurate than measuring a relation yourself from the catalogue, or finished: most of the simulation curves were read from figures by script and have not been checked by anyone who knows the simulation. It was built by one maintainer with an AI assistant (Claude); the reviews called independent in the protocols were made by a separate AI agent, not a human expert.

**What would make it great.** Outside researchers using it and saying so; experts checking a sample of the curves; the dials page showing a third simulation code; and a stopping rule honoured if none of that happens (docs/PROJECT.md).
