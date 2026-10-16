"""Exploratory robustness checks of the all-at-once study, made after its registered run (so none of this is part of the registered result and none changes a verdict):
 (1) a second implementation of the distance: different optimiser (scipy L-BFGS-B, 40 random starts), features written out from the polynomial terms, weights built from the block layout, compared with the analysis' point distances;
 (2) other weightings of the outputs;
 (3) a different kind of emulator (RBF kernel ridge regression in the six parameters) for the same outputs, to see how much the distance depends on the polynomial form.
Needs scipy and scikit-learn. Writes data/analysis/joint-robustness.json and docs/ROBUSTNESS-joint-reachability.md. Usage: python3 scripts/explore_joint_robustness.py"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from sklearn.kernel_ridge import KernelRidge

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_joint_reachability as J
import export_retune_data as E

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20261018)


class Poly:
    """Collapsed polynomial at the fiducial cosmology: y(a) = sum_t coef[t] prod_j a[term_t]."""

    def __init__(self, emu):
        self.terms, self.coef = E.collapse(emu)

    def __call__(self, a, cols):
        f = np.array([np.prod([a[i] for i in t]) if t else 1.0 for t in self.terms])
        return f @ self.coef[:, cols]


class KRR:
    """RBF kernel ridge regression in the six parameters, one model per output (rows with a finite value), predicted at the fiducial cosmology. The fitted models are stacked into one matrix of dual weights so that all outputs are predicted from a single kernel vector."""

    def __init__(self, X, Y, cols, length, alpha):
        self.X, self.gamma = X, 1.0 / (2 * length ** 2)
        self.cols = list(cols)
        self.pos = {j: k for k, j in enumerate(self.cols)}
        self.W = np.zeros((len(X), len(self.cols)))
        self.mu = np.zeros(len(self.cols))
        for k, j in enumerate(self.cols):
            ok = np.isfinite(Y[:, j])
            self.mu[k] = Y[ok, j].mean()
            m = KernelRidge(alpha=alpha, kernel="rbf", gamma=self.gamma).fit(X[ok], Y[ok, j] - self.mu[k])
            self.W[ok, k] = m.dual_coef_

    def __call__(self, a, cols):
        x = np.concatenate([[0.0, 0.0], a])
        k = np.exp(-self.gamma * ((self.X - x) ** 2).sum(1))
        idx = [self.pos[j] for j in cols]
        return k @ self.W[:, idx] + self.mu[idx]


def pick_hyperparameters(X, Y, cols, scale):
    """Length scale and ridge penalty chosen by 5-fold cross-validation on the standardised error, over a few outputs."""
    sub = list(cols)[:: max(1, len(cols) // 25)]
    best = (np.inf, None)
    fold = RNG.permutation(len(X)) % 5
    for length in (0.6, 1.0, 1.6, 2.5):
        for alpha in (1e-3, 1e-2, 1e-1):
            e = 0.0
            for j in sub:
                for f in range(5):
                    tr, te = (fold != f) & np.isfinite(Y[:, j]), (fold == f) & np.isfinite(Y[:, j])
                    mu = Y[tr, j].mean()
                    m = KernelRidge(alpha=alpha, kernel="rbf", gamma=1.0 / (2 * length ** 2)).fit(X[tr], Y[tr, j] - mu)
                    e += np.mean(((m.predict(X[te]) + mu - Y[te, j]) / scale[j]) ** 2)
            if e < best[0]:
                best = (e, (length, alpha))
    return best[1]


def weights(blocks, idx_by_block, scale, keys, mode):
    """Squared weights per output of a set of blocks. block: every block the same total weight (the study's rule); output: every output the same; family: every family the same, split equally over its outputs."""
    cols, w = [], []
    if mode == "family":
        fam = {}
        for k in keys:
            fam.setdefault(k[0], []).append(k)
    for k in keys:
        js = idx_by_block[k]
        if mode == "block":
            wk = [1.0 / len(js)] * len(js)
        elif mode == "output":
            wk = [1.0] * len(js)
        else:
            nout = sum(len(idx_by_block[b]) for b in fam[k[0]])
            wk = [1.0 / nout] * len(js)
        cols += list(js)
        w += wk
    w = np.array(w)
    w = w / w.mean()
    cols = np.array(cols)
    return cols, w / scale[cols] ** 2


def distance(fT, fS, cols, w2, nstarts=40):
    def f(a8):
        d = fT(a8[:4], cols) - fS(a8[4:], cols)
        return float(np.mean(w2 * d * d))
    best = np.inf
    starts = [np.zeros(8)] + [RNG.uniform(-1, 1, 8) for _ in range(nstarts)]
    for x0 in starts:
        r = minimize(f, x0, method="L-BFGS-B", bounds=[(-1, 1)] * 8, options={"maxiter": 200})
        best = min(best, r.fun)
    return float(np.sqrt(best))


def main():
    t0 = time.time()
    data = J.load_galaxies()
    keep, blocks, _ = J.eligibility(data)
    emus, info = J.build_emulators(data, keep)
    scale = J.noise_scale(info)
    saved = json.loads((ROOT / "data" / "analysis" / "joint-reachability.json").read_text())
    ibb = {b: np.array(v) for b, v in blocks.items()}
    joint = [b for b in blocks if b[0] != "hmf"]
    fams = [f for f in J.JOINT_FAMILIES if any(b[0] == f for b in joint)]
    P = {s: Poly(emus[s]) for s in J.SUITES}
    out = {"registered": {"all": saved["point"]["all"]["D"], **{f: saved["point"]["fam:" + f]["D"] for f in fams}}, "reimplementation": {}, "weightings": {}, "emulator": {}}
    # (1) a second implementation, same weights as the study
    for name, ks in [("all", joint)] + [(f, [b for b in joint if b[0] == f]) for f in fams]:
        cols, w2 = weights(blocks, ibb, scale, ks, "block")
        out["reimplementation"][name] = distance(P["IllustrisTNG"], P["SIMBA"], cols, w2)
    # (2) other weightings of all outputs
    for mode in ("block", "output", "family"):
        cols, w2 = weights(blocks, ibb, scale, joint, mode)
        out["weightings"][mode] = distance(P["IllustrisTNG"], P["SIMBA"], cols, w2)
    for label, sel in (("redshifts 0 and 0.95 only", lambda b: b[1] in ("090", "062")), ("without the two black hole families", lambda b: b[0] not in ("bhocc", "bhms")), ("without the two densities and the halo-mass ratio", lambda b: b[0] not in ("rho", "shmr"))):
        ks = [b for b in joint if sel(b)]
        cols, w2 = weights(blocks, ibb, scale, ks, "block")
        out["weightings"][label] = distance(P["IllustrisTNG"], P["SIMBA"], cols, w2)
    # (3) a different emulator
    cols_all = np.array(sorted({j for b in joint for j in blocks[b]}))
    K = {}
    for s in J.SUITES:
        lh = data["suites"][s]["LH"]
        length, alpha = pick_hyperparameters(lh["X"], lh["Y"], cols_all, scale)
        K[s] = (KRR(lh["X"], lh["Y"], cols_all, length, alpha), length, alpha)
    out["emulator"]["hyperparameters"] = {s: {"length": K[s][1], "alpha": K[s][2]} for s in J.SUITES}
    for name, ks in [("all", joint)] + [(f, [b for b in joint if b[0] == f]) for f in fams]:
        cols, w2 = weights(blocks, ibb, scale, ks, "block")
        out["emulator"][name] = distance(K["IllustrisTNG"][0], K["SIMBA"][0], cols, w2, nstarts=12)
    out["runtime_s"] = round(time.time() - t0)
    (ROOT / "data" / "analysis" / "joint-robustness.json").write_text(json.dumps(out, indent=1) + "\n")
    (ROOT / "docs" / "ROBUSTNESS-joint-reachability.md").write_text(render(out, fams))
    print(f"robustness: registered {out['registered']['all']:.2f}, second implementation {out['reimplementation']['all']:.2f}, kernel-ridge emulator {out['emulator']['all']:.2f}; {out['runtime_s']} s")


def render(o, fams):
    N = J.FAMILY_NAMES
    H = o["emulator"]["hyperparameters"]
    hp = "; ".join(f"{c}: length {v['length']}, penalty {v['alpha']}" for c, v in H.items())
    edge = " The chosen length scale is the largest on the grid for both codes, which means the response is very smooth in the six parameters; a longer one was not tried." if all(v["length"] >= 2.5 for v in H.values()) else ""
    L = ["# Robustness of the all-at-once result (exploratory)", "",
         "Generated by `scripts/explore_joint_robustness.py` after the registered run. **Nothing here is part of the registered result and nothing changes its verdict**: these are the checks one would want to see before believing the headline, made once, reported whatever they gave. Distances are point estimates over all 1,000 simulations per code in noise units (the registered ones are uncorrected point distances, so the comparison is like for like).", "",
         "## 1. A second implementation of the distance", "",
         "Different optimiser (scipy L-BFGS-B from 40 random starts, where the study used projected gradient descent from the fiducial point and random starts) and the polynomial terms evaluated from the collapsed coefficients written out term by term. The page's in-browser search is a third implementation; the browser test requires it to give 4.85.", "",
         "| set | registered | second implementation |", "|---|---|---|", f"| all observables | {o['registered']['all']:.2f} | {o['reimplementation']['all']:.2f} |"]
    for f in fams:
        L.append(f"| {N[f]} | {o['registered'][f]:.2f} | {o['reimplementation'][f]:.2f} |")
    L += ["", "## 2. Other weightings of the outputs", "", "The study gives every block of outputs (a property at one redshift) the same weight. Other choices:", "", "| weighting | distance |", "|---|---|"]
    for k, v in o["weightings"].items():
        L.append(f"| {({'block': 'every block the same weight (the study)', 'output': 'every output the same weight', 'family': 'every property the same weight'}).get(k, k)} | {v:.2f} |")
    L += ["", "## 3. A different emulator", "", f"RBF kernel ridge regression in the six parameters, one model per output, length scale and penalty chosen by 5-fold cross-validation over a small grid ({hp}). Same weights and noise scale as the study.{edge}", "",
          "| set | polynomial (registered) | kernel ridge |", "|---|---|---|", f"| all observables | {o['registered']['all']:.2f} | {o['emulator']['all']:.2f} |"]
    for f in fams:
        L.append(f"| {N[f]} | {o['registered'][f]:.2f} | {o['emulator'][f]:.2f} |")
    L += ["", "## Reading", "",
          "The point of this page is how far the headline moves, and for which properties, when the machinery is changed. A property whose distance is far from the registered value under another emulator is one whose verdict leans on the polynomial form; the others are not. The emulators' own error is part of the noise scale in every column, so a kernel-ridge distance below the polynomial one does not by itself mean the polynomial was wrong.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
