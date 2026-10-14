"""How much of the disagreement between simulated z ~ 0 stellar mass functions can documented definitions explain?

Implements docs/PROTOCOL-harmonization.md (read it first; this file follows it section by section and reports every departure as a deviation).
Coordinate: the stellar mass at fixed abundance, m(phi). Operators: IMF (standard offsets) and stellar-mass aperture (maps measured inside single runs).
Writes data/analysis/harmonization.json and docs/ANALYSIS-harmonization.md. Nothing here changes a stored record."""
import itertools
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_definition_budget as adb

ROOT = adb.ROOT
SEED = 20261014
PHI = np.round(np.arange(-2.0, -4.5001, -0.25), 2)
PHI_FINE = np.round(np.arange(-2.0, -4.5001, -0.05), 2)
MAX_GAP = 0.6
MIN_SUITES = 4
REF = "30"
Z_MAX = 0.2
NBOOT, NPERM, NRAND, NINJ, NINJ_BOOT = 2000, 2000, 200, 100, 200
LAMBDAS = (0.0, 0.5, 1.0, 2.0)
# the within-run aperture comparisons (docs/PROTOCOL-harmonization.md, section 3): suite -> aperture class -> record id
LIBRARY = {
    "EAGLE": {"10": "schaye15.eagle-ref-l100n1504.gsmf-ap-10pkpc.z0.1", "30": "schaye15.eagle-ref-l100n1504.gsmf-ap-30pkpc.z0.1", "100": "schaye15.eagle-ref-l100n1504.gsmf-ap-100pkpc.z0.1",
              "petrosian": "schaye15.eagle-ref-l100n1504.gsmf-ap-petrosian.z0.1", "total": "schaye15.eagle-ref-l100n1504.gsmf-ap-all-bound.z0.1"},
    "COLIBRE": {"30": "chaikin26.colibre.l200m6.gsmf-ap-30pkpc.z0", "50": "chaikin26.colibre.l200m6.gsmf-ap-50pkpc.z0", "100": "chaikin26.colibre.l200m6.gsmf-ap-100pkpc.z0",
                "total": "chaikin26.colibre.l200m6.gsmf-ap-all-bound.z0"},
    "Illustris": {"2rhalf": "genel14.illustris-1.gsmf-r2.z0", "30": "pillepich18.illustris.gsmf.z0", "total": "genel14.illustris-1.gsmf-full.z0"},
}
LIB_IDS = {i for cs in LIBRARY.values() for i in cs.values()}
LIB_CLASSES = ["10", "30", "50", "100", "total", "2rhalf", "petrosian"]
CLASS_OF = {"aperture-10pkpc": "10", "aperture-30pkpc": "30", "aperture-50pkpc": "50", "aperture-100pkpc": "100", "total-subhalo": "total", "total-bound-subhalo": "total",
            "aperture-2rhalf-stars": "2rhalf", "petrosian-2D": "petrosian"}
ID_SUBLIBRARY = re.compile(r"\.gsmf-ap-")


def imf_dex():
    body = re.search(r"const IMF_DEX=\{(.*?)\}", (ROOT / "compare.js").read_text()).group(1)
    return {k: float(v) for k, v in (kv.split(":") for kv in body.split(","))}


IMF_DEX = imf_dex()


def imf_shift(imf, extra=0.0):
    """Dex to add to a stellar mass to express it in a Chabrier IMF (the website's standard offsets); unstated IMFs stay as published."""
    if imf not in IMF_DEX:
        return 0.0
    base = IMF_DEX["chabrier03"] - IMF_DEX[imf]
    return base + (extra if imf != "chabrier03" and abs(base) > 1e-12 else 0.0)


# ---------------------------------------------------------------- the website's choice of one curve per suite (highline/logic.js)
def _js_regex(src):
    m = re.fullmatch(r"/(.*)/([a-z]*)", src.strip(), re.S)
    return re.compile(m.group(1), re.I if "i" in m.group(2) else 0)


def fiducial_rules():
    src = (ROOT / "highline" / "logic.js").read_text()
    variant = _js_regex(re.search(r"const VARIANT = (/.*?/[a-z]*);", src).group(1))
    block = re.search(r"const FIDUCIAL = \{(.*?)\};", src, re.S).group(1)
    fid = {k: _js_regex(v) for k, v in re.findall(r'"([^"]+)":\s*(/.*?/[a-z]*)(?=,\s*"|\s*$)', block.strip())}
    tier = {k: int(v) for k, v in re.findall(r'"([a-z-]+)":\s*(\d)', re.search(r"const TIER_RANK = \{(.*?)\};", src).group(1))}
    return variant, fid, tier


def primary_units(records):
    """Port of SimHighlineLogic.primaryUnits: one unit (source|run) per source, preferring the explicit fiducial runs, then non-variants, then more epochs, then better tier."""
    variant, fid, tier = fiducial_rules()
    by = {}
    for r in records:
        u = by.setdefault(r["source"], {}).setdefault(f'{r["source"]}|{r.get("run") or ""}', {"u": f'{r["source"]}|{r.get("run") or ""}', "run": r.get("run") or "", "z": set(), "tier": 9})
        u["z"].add(r["epoch"]["zRepresentative"])
        u["tier"] = min(u["tier"], tier.get(r["provenance"].get("tier"), 9))
    out = set()
    for src, units in by.items():
        f = fid.get(src)
        best = sorted(units.values(), key=lambda a: (0 if f and f.search(a["run"]) else 1, 1 if variant.search(a["run"]) else 0, -len(a["z"]), a["tier"], a["run"]))[0]
        out.add(best["u"])
    return out


# ---------------------------------------------------------------- the coordinate
def points(rec):
    return sorted((p["x"], p["y"]) for p in rec["representation"]["points"] if isinstance(p.get("x"), (int, float)) and isinstance(p.get("y"), (int, float)))


def mass_at(pts, phis):
    """m(phi): the largest x at which the curve crosses phi from above (linear between points no more than MAX_GAP apart); NaN where the curve never gets there."""
    x = np.array([p[0] for p in pts], float)
    y = np.array([p[1] for p in pts], float)
    out = np.full(len(phis), np.nan)
    for k, phi in enumerate(phis):
        for i in range(len(x) - 1, 0, -1):
            if y[i - 1] >= phi > y[i] and x[i] - x[i - 1] <= MAX_GAP:
                out[k] = x[i - 1] + (phi - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1])
                break
    return out


# ---------------------------------------------------------------- the aperture library
class Library:
    """Aperture maps delta_A->B(M) = m_B(phi) - m_A(phi) at M = m_A(phi), measured inside single runs by abundance matching.
    reflect and signs build the counterfactual worlds of the E2 null (maps mirrored in mass, or sign-flipped per source class)."""

    def __init__(self, curves, reflect=False, signs=None):
        self.curves, self.reflect, self.signs, self._cache = curves, reflect, signs or {}, {}

    def classes(self):
        return sorted({c for cs in self.curves.values() for c in cs})

    def direct(self, a, b):
        if (a, b) not in self._cache:
            out = []
            for s, cs in sorted(self.curves.items()):
                if a in cs and b in cs:
                    ma, mb = mass_at(cs[a], PHI_FINE), mass_at(cs[b], PHI_FINE)
                    ok = np.isfinite(ma) & np.isfinite(mb)
                    if ok.sum() >= 5:
                        order = np.argsort(ma[ok])
                        M, d, phi = ma[ok][order], (mb - ma)[ok][order], PHI_FINE[ok][order]
                        if self.reflect:
                            d = np.interp(M[0] + M[-1] - M, M, d)
                        out.append((s, M, d * self.signs.get(a, 1), phi))
            self._cache[(a, b)] = out
        return self._cache[(a, b)]

    def evaluate(self, a, b, x, by="mass"):
        """Mean map of the library suites that define it at x (mass in dex, or abundance phi): (mean, number of suites, between-suite sd). Composed through the reference class when no suite measured the pair."""
        x = np.asarray(x, float)
        ents = self.direct(a, b)
        if not ents:
            if REF in (a, b) or not self.direct(a, REF) or not self.direct(REF, b):
                return np.full(x.shape, np.nan), np.zeros(x.shape, int), np.full(x.shape, np.nan)
            m1, n1, s1 = self.evaluate(a, REF, x, by)
            m2, n2, s2 = self.evaluate(REF, b, (x + m1) if by == "mass" else x, by)
            return m1 + m2, np.minimum(n1, n2), np.sqrt(np.nan_to_num(s1) ** 2 + np.nan_to_num(s2) ** 2)
        vals = np.full((len(ents), x.size), np.nan)
        for i, (_, M, d, phi) in enumerate(ents):
            if by == "mass":
                vals[i] = np.interp(x, M, d, left=np.nan, right=np.nan)
            else:
                o = np.argsort(phi)
                vals[i] = np.interp(x, phi[o], d[o], left=np.nan, right=np.nan)
        n = np.isfinite(vals).sum(axis=0)
        mean = np.where(n > 0, np.nansum(vals, axis=0) / np.maximum(n, 1), np.nan)
        sd = np.where(n > 1, np.sqrt(np.nansum((vals - mean) ** 2, axis=0) / np.maximum(n - 1, 1)), np.nan)
        return mean, n, sd


def harmonize(m_raw, imf, cls, lib, ref=REF, imf_extra=0.0, by="mass", phi=PHI):
    """Express one suite's m(phi) in a Chabrier IMF and the reference aperture. Returns the harmonized masses and where an aperture map was applied."""
    m = np.asarray(m_raw, float) + imf_shift(imf, imf_extra)
    done = np.zeros(m.shape, bool)
    if cls is not None and cls != ref:
        d, _, _ = lib.evaluate(cls, ref, m if by == "mass" else phi, by)
        done = np.isfinite(d) & np.isfinite(m)
        m = np.where(done, m + d, m)
    return m, done


# ---------------------------------------------------------------- dispersion
def level_variance(X, axis=0, min_n=MIN_SUITES):
    """Unbiased variance across suites at each level, NaN where fewer than min_n suites define it. X has suites on `axis`."""
    ok = np.isfinite(X)
    n = ok.sum(axis=axis)
    mean = np.nansum(X, axis=axis) / np.maximum(n, 1)
    ss = np.nansum((X - np.expand_dims(mean, axis)) ** 2, axis=axis)
    var = ss / np.maximum(n - 1, 1)
    return np.where(n >= min_n, var, np.nan)


def reduction(M_raw, M_h, levels=None):
    """R = 1 - V_harmonized / V_raw, each the mean over the levels that at least MIN_SUITES suites define."""
    vr, vh = level_variance(M_raw), level_variance(M_h)
    use = np.isfinite(vr) & np.isfinite(vh) & (levels if levels is not None else True)
    return float(1.0 - vh[use].mean() / vr[use].mean()) if use.any() and vr[use].mean() > 0 else float("nan")


def bootstrap_reduction(M_raw, M_h, rng, nboot=NBOOT, levels=None):
    """Cluster bootstrap over suites: R recomputed on suites resampled with replacement."""
    n = M_raw.shape[0]
    idx = rng.integers(0, n, size=(nboot, n))
    vr, vh = level_variance(M_raw[idx], axis=1), level_variance(M_h[idx], axis=1)
    use = np.isfinite(vr) & np.isfinite(vh) & (levels if levels is not None else True)
    num = np.where(use, vh, 0).sum(axis=1)
    den = np.where(use, vr, 0).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(den > 0, 1.0 - num / den, np.nan)
    return r[np.isfinite(r)]


def ci95(v):
    return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]


# ---------------------------------------------------------------- the suites
def is_eligible(r, include_ambiguous=False):
    pts = r["representation"].get("points") or []
    u = r["axes"]["yUnit"]
    return (r["kind"] == "simulation" and r["relation"] == "gsmf" and r["representation"].get("type") == "points" and len(pts) >= 5 and r["epoch"]["zRepresentative"] <= Z_MAX
            and r["definitions"].get("population") in ("all", "all galaxies") and ("dex^-1" in u or (include_ambiguous and u == "log10(Mpc^-3)")))


def unit_of(r):
    return f'{r["source"]}|{r.get("run") or ""}'


def choose_suites(recs, include_ambiguous=False, pick=None):
    """One curve per suite: the website's fiducial unit, then its eligible record nearest z = 0. pick(source, {run: records}) replaces the unit (sensitivity S5).
    Returns the chosen records and, for every suite that has a z <= 0.2 mass function but is not used, the reason."""
    sims = [r for r in recs if r["kind"] == "simulation" and r["relation"] == "gsmf" and not ID_SUBLIBRARY.search(r["id"])]
    units = primary_units(sims)
    variant = fiducial_rules()[0]
    out, excluded = {}, {}
    for src in sorted({r["source"] for r in sims}):
        mine = [r for r in sims if r["source"] == src]
        near = [r for r in mine if r["epoch"]["zRepresentative"] <= Z_MAX]
        if not near:
            continue
        if pick is None:
            unit = next(u for u in units if u.split("|")[0] == src)
            cands = [r for r in mine if unit_of(r) == unit and is_eligible(r, include_ambiguous)]
            run = unit.split("|", 1)[1]
            tied = [r for r in near if unit_of(r) == unit]
            reason = (f"its fiducial run {run!r} has no record at z <= {Z_MAX}" if not tied else
                      f"its fiducial run {run!r} is not eligible: " + ("per-dex normalisation not stated" if any(r["axes"]["yUnit"] == "log10(Mpc^-3)" for r in tied) else "population is not 'all' or too few points"))
        else:
            by_unit = {}
            for r in mine:
                if is_eligible(r, include_ambiguous) and not variant.search(r.get("run") or ""):
                    by_unit.setdefault(r.get("run") or "", []).append(r)
            cands, reason = pick(src, by_unit), "no eligible non-variant run"
        if cands:
            out[src] = min(cands, key=lambda r: (abs(r["epoch"]["zRepresentative"]), r["id"]))
        else:
            excluded[src] = reason
    return out, excluded


def build_matrix(chosen, lib, **kw):
    """m(phi) raw and harmonized for every chosen suite, plus labels and the share of levels corrected."""
    names = sorted(chosen)
    raw = np.array([mass_at(points(chosen[s]), PHI) for s in names])
    labels = [(chosen[s]["definitions"].get("imf"), CLASS_OF.get(str(chosen[s]["definitions"].get("massDefinition")))) for s in names]
    har, done = zip(*[harmonize(raw[i], labels[i][0], labels[i][1], lib, **kw) for i in range(len(names))])
    return names, raw, np.array(har), np.array(done), labels


def library_curves(recs):
    byid = {r["id"]: r for r in recs}
    return {s: {c: points(byid[i]) for c, i in cs.items()} for s, cs in LIBRARY.items()}
