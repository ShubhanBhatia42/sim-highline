"""Design check run on 2026-10-14 before the protocol was committed, kept for the record (see section 8 and amendment A1 of docs/PROTOCOL-model-form.md). It loads the real CAMELS file and prints the fraction of simulations without star
formation, the seed scatter of the CV set and the 10-fold cross-validation error of the degree 2 and 3 emulators relative to it. Its output on the code of that day is data/analysis/model-form-design-check.log; the ridge
was corrected afterwards (A1), so a rerun gives slightly different numbers. It computes no parametric spread, offset, reachability distance or posterior."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import analyze_model_form as A
d = A.load_camels()
print("grid", A.CAMELS_Z[0], A.CAMELS_Z[-1], len(A.CAMELS_Z))
for suite in ("IllustrisTNG", "SIMBA"):
    names, X, Y = A.camels_arrays(d, suite, "LH")
    _, Xc, Yc = A.camels_arrays(d, suite, "CV")
    print("\n==", suite, "LH", X.shape, "CV", Yc.shape)
    nanf = np.isnan(Y).mean(axis=0)
    print("NaN fraction LH by z:", {float(z): round(float(f), 3) for z, f in zip(A.CAMELS_Z, nanf) if z in (0.1, 2.1, 4.1, 5.1, 6.1, 6.5, 7.1, 7.7, 8.1)})
    print("NaN fraction CV by z:", {float(z): round(float(f), 3) for z, f in zip(A.CAMELS_Z, np.isnan(Yc).mean(axis=0)) if z in (4.1, 6.1, 7.1, 8.1)})
    sn = A.seed_noise(Yc)
    print("seed noise by z:", {float(z): round(float(v), 3) for z, v in zip(A.CAMELS_Z, sn) if z in (0.1, 0.9, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1)})
    for deg in (2, 3):
        cv, n = A.cv_errors(X, Y, deg)
        print(f"degree {deg}: CV rmse/seed noise by z:", {float(z): round(float(v), 2) for z, v in zip(A.CAMELS_Z, cv / sn) if z in (0.1, 0.9, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1)}, "n_test", n)
    # LH design: parameter distribution
    print("LH design min/max by coordinate:", np.round(X.min(axis=0), 2), np.round(X.max(axis=0), 2), "mean", np.round(X.mean(axis=0), 2))
    print("sims within 0.5 of fiducial cosmology:", int(((abs(X[:, 0]) <= 0.5) & (abs(X[:, 1]) <= 0.5)).sum()))
