# Related work, and what that does to our claims

Written 2026-10-16 from web searches (five queries) whose results were summaries and abstracts. **I have not read the full text of these papers**, so every statement below is what the summary says; check the paper before quoting it.

## What exists

- **CAMELS itself** (Villaescusa-Navarro et al. 2021, [doi:10.3847/1538-4357/abf7ba](https://iopscience.iop.org/article/10.3847/1538-4357/abf7ba)). Reports that IllustrisTNG and SIMBA agree well within the range of variation for many quantities, including stellar mass functions and scaling relations. The data-release paper ([arXiv:2201.01300](https://arxiv.org/pdf/2201.01300)) reports similar distributions of galaxy properties over the parameter space but significantly different halo baryon fractions and baryonic effects on the matter power spectrum, and notes that the same nominal AGN parameter is implemented differently in the two codes.
- **Larger CAMELS suites** ([arXiv:2304.02096](https://arxiv.org/abs/2304.02096)): ASTRID and 28-parameter TNG and SIMBA suites, with shared random seeds across suites, which would let individual galaxies be matched between codes.
- **Galaxies from the two suites remain distinguishable** at the same parameters (about 85 % classification accuracy; [arXiv:2503.22654](https://arxiv.org/html/2503.22654)).
- **Cross-suite generalisation is uneven**: networks trained on one suite do worse on another ([arXiv:2411.13960](https://arxiv.org/pdf/2411.13960)); robustness to the choice of suite is an active topic ([arXiv:2502.13239](https://arxiv.org/pdf/2502.13239), TNG, SIMBA, ASTRID and EAGLE; field-level emulators across suites, [arXiv:2401.15891](https://arxiv.org/pdf/2401.15891)).
- **Matching CAMELS runs to observed scaling relations**: the CASCO series (Busillo et al., [arXiv:2308.14822](https://arxiv.org/pdf/2308.14822), [2412.00217](https://arxiv.org/pdf/2412.00217), [2502.13589](https://arxiv.org/pdf/2502.13589), and a 2026 extension to warm dark matter, [arXiv:2601.07543](https://arxiv.org/abs/2601.07543)) ranks CAMELS simulations by chi-squared against observed relations and recovers best-fitting parameters.

## What I did not find

No paper that asks our specific question: *over the whole CAMELS parameter box, how close can retuning make one code's galaxy population come to the other's, observable by observable and all at once?* I searched with several phrasings and found nothing, which is weaker than there being nothing: the search tool returns summaries, and the relevant statement could sit inside a paper whose abstract does not mention it. I also did not find a web tool that overlays published curves from many simulations with a definition check; again, absence in a search is not proof.

## What this changes

1. **The result is not a discovery.** That the two codes differ structurally is consistent with what CAMELS already reports. What our analysis adds is a *size* (in the observables' own units) and a *per-observable* answer to what retuning can close, with the rule written before the result. Pages must say so.
2. **We do not claim novelty of the question** until a reader who knows the CAMELS literature has looked at it.
3. **The closest neighbour is the CASCO method**, which fits simulations to observations; ours fits simulations to each other. Our "tune to observations" feature is that same idea applied to the emulators, and should cite them.
4. **A third code is the most useful next test.** CAMELS has an ASTRID suite; with it "two codes only" becomes "three codes".
