# What a sceptic would say, and the answers

Each objection is stated as strongly as a careful reader would put it. The answer says what the project actually did, and whether the objection still stands. *Stands* means we have no answer that would satisfy the objector.

**1. "The distance is just the emulators being wrong at the edge of the box."**
The minimiser does sit at the edge, where emulators are least constrained. The emulators' own error is part of the noise unit, the variance at the minimiser is removed in quadrature (amendment A1, registered), two halves of the same code come out 0.00 apart under the same search, and a different kind of emulator (kernel ridge) gives 4.91 against 4.85. A second implementation of the search gives 4.85. *Answered*, as far as emulator choice goes; a direct check against a new simulation at the minimiser would be better and has not been done (it needs runs CAMELS does not provide).

**2. "Four dials are not all the freedom the models have, so 'cannot be closed' only means 'cannot be closed with these four'."**
Correct, and the pages say so. The claim is about the four CAMELS dials of each code. *Stands* as a limit on what the result means; it is not something analysis of this data can remove.

**3. "Black hole occupation is a seeding rule, not feedback. Of course dials do not change it."**
Agreed, and the dials page says the same in its explanation of that property. The result without it is still 3.7 noise units (registered sensitivity), so the headline does not rest on it alone. *Answered.*

**4. "A noise unit is arbitrary."**
It is a convention: the scatter between one run of each code. It is not a physical tolerance. Distances are also given in dex and fractions beside it, and one noise unit is between 0.04 and 0.18 dex depending on the property. A reader with a different tolerance can read it off. *Answered by transparency, not by argument.*

**5. "CAMELS resolution is too coarse."**
The result is stated for CAMELS resolution only. Cutting the two lowest mass bins takes 4.8 to 2.5, the biggest sensitivity of any (`docs/RESOLUTION.md`). No higher-resolution runs were analysed. *Stands.*

**6. "Two codes only."**
A third code (Astrid) was added afterwards, exploratory: on the 97 outputs usable in all three, TNG–SIMBA is 3.9, SIMBA–Astrid 3.4, TNG–Astrid 1.5, and black hole occupation separates SIMBA from the other two. That says the headline is closer to 'SIMBA stands apart' than 'TNG versus SIMBA'. It is still three codes from one project, one box size, one set of dials. *Partly answered.*

**7. "This is already known."**
CAMELS reports that the codes differ and which quantities; classifier and cross-suite papers show the codes are distinguishable (`docs/RELATED-WORK.md`). What was not found in the searches is a per-property answer to 'what can retuning close', but those searches read summaries, not papers. The project does not claim to be first. *Stands until someone who knows the literature looks.*

**8. "Pre-registration by one person with git dates is theatre."**
The rule was committed before the result existed, and the dated trail is on the site (`data/registration-trail.json`). Git dates are set by whoever commits and can be forged, so this is not independent proof. A deposit with a DOI (task 5.17, needs the maintainer) or any third-party timestamp would be. *Stands until deposited.*

**9. "The robustness checks were made after the run, so you looked until it held."**
The sensitivity analysis was registered; the second implementation, the other weightings and the other emulator were made once after the run and are reported as exploratory with their results whatever they were (they agree, but one run of an exploratory check is what it is). The third-code and observation checks likewise. *Answered by disclosure.*

**10. "Equal weight per block is a choice."**
Yes. Other weightings give 4.5 to 5.4 (`docs/CHOICES-joint-reachability.md`). *Answered.*

**11. "Subfind subhaloes are not observed galaxies."**
Declared in the protocol. The comparison is simulation against simulation, deliberately without aperture or survey effects, so it cannot be used as an observational test. *Stands as a scope limit.*

**12. "Tuned to observations, either code fits the mass function. So what?"**
Agreed: a smooth curve is easy to fit with four dials, and the observation-tuning table (`docs/ANALYSIS-tune-to-observations.md`) says so. The informative outcome is where neither code can get near: black hole mass (two curves; the better code is 2.5 to 3.6 noise units away), and single curves of specific star formation rate and the quiescent mass function at z = 2.15 and of stellar metallicity. These rest on few curves with few bins each. It is not a test of either code, because observed and simulated curves are defined differently. *Answered.*

**13. "The digitised curves in the Explorer may be wrong."**
Possible. 1,960 records, 54 % of simulation curves taken from vector paths in figures, and only one digitised curve has an independent table check (`docs/DATA-QUALITY.md`). The all-at-once study does not use them; it uses CAMELS catalogues. The Explorer's evidence panel says how sure we are for each curve. *Stands for the Explorer until more are checked; an audit packet is ready to send (task 1.15/1.16).*

**14. "Who has reviewed it?"**
No one outside the project. The reviews that preceded the model-form and all-at-once runs (recorded in the protocols) were internal, not by an outside expert, and the pages say so. *Stands: this is the largest gap, and the reason the audit packet and the pilot exist.*

**15. "The best setting sits at the edge of the dials' range, where emulators are least tested."**
True: at the minimum, 4 of the eight dial coordinates sit exactly on the bounds. The emulators are validated on simulations within 0.5 of the fiducial cosmology, which is not the same as validated at the corner of the dial box. The emulators' variance at the minimiser is removed from the distance (amendment A1), a different kind of emulator gives 4.91, and the verdict holds with the range cut to 75%. But no simulation has been run at the minimiser. A partial check was made afterwards (`docs/ANALYSIS-minimiser-check.md`): the 15 simulations nearest each code's minimising setting were held out and predicted as well as random ones (0.73 and 0.74 noise units against 0.82 and 0.81; about 0.7 is the floor from a single run's own scatter). They are 0.45 and 0.67 away from the minimum in dial coordinates, not at it. *Partly answered: no simulation has been run at the minimum, and CAMELS' extreme-parameter runs have not been compared.*

**16. "The structural and conflict split depends on the third decimal; the calibration injects into one family."**
Both true. The ratio of the joint distance to the separate-families distance is 2.7442 against a same-code 95th percentile of 2.7443: the registered rule calls it "not above the null", and that is a knife edge, so no conflict between properties is claimed. All 27 synthetic calibration runs inject their difference into one family (black hole occupation) or offset all outputs equally, so the rule's behaviour on other structures is untested. *Stands.*

**17. "Pre-registration within one day by one person."**
The protocol for the harmonization study was committed at 10:46, an amendment at 11:11 and the result at 11:21 on the same day (git dates only). That is a rule written before the result, but not by a margin that independent timestamping would make convincing. *Stands until a third-party deposit exists.*

**18. "The pages load Google Fonts."**
They do, which sends the reader's address to Google. Your own curve in "Your run" never leaves the browser. Stated on the Methods page. Self-hosting the fonts would remove it. *Open.*
