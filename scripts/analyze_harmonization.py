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


# ---------------------------------------------------------------- the aperture library: galaxy-level mass remaps (amendment A2)
HUB = REF
DEGREE = 3
EDGE_MARGIN = 0.3
LN10 = float(np.log(10.0))


def _cumulative(pts, step=0.01):
    """Number density above each mass of a curve (per volume), by trapezoids; the part above the last point continues the last slope as an exponential."""
    x = np.array([p[0] for p in pts], float)
    y = np.array([p[1] for p in pts], float)
    xs = np.arange(x[0], x[-1] + 1e-9, step)
    ph = 10.0 ** np.interp(xs, x, y)
    slope = (y[-1] - y[-2]) / (x[-1] - x[-2])
    tail = 10.0 ** y[-1] / (abs(slope) * LN10) if slope < -0.05 else 0.0
    seg = 0.5 * (ph[1:] + ph[:-1]) * step
    return xs, np.concatenate([np.cumsum(seg[::-1])[::-1], [0.0]]) + tail


class Remap:
    """f(M): the shift in log stellar mass that one definition gives each galaxy relative to another (a cubic polynomial fitted to a rank-preserving match), valid on [lo, hi]."""

    def __init__(self, lo, hi, coef, grid=None, values=None):
        self.lo, self.hi, self.coef, self.grid, self.values = float(lo), float(hi), np.asarray(coef, float), grid, values

    def f(self, x):
        return np.polyval(self.coef, x)

    def df(self, x):
        return np.polyval(np.polyder(self.coef), x)

    def contains(self, x):
        return (np.asarray(x) >= self.lo - 1e-9) & (np.asarray(x) <= self.hi + 1e-9)

    def transformed(self, reflect=False, sign=1):
        if not reflect and sign == 1:
            return self
        g = np.linspace(self.lo, self.hi, 60)
        v = self.f(g[::-1]) if reflect else self.f(g)
        return Remap(self.lo, self.hi, np.polyfit(g, v * sign, DEGREE), g, v * sign)


def estimate_remap(pts_a, pts_b):
    """Rank-preserving match of two curves of the same population: f(M_A) = M_B - M_A at equal number density above the mass. None where the curves share under 0.4 dex."""
    xa, na = _cumulative(pts_a)
    xb, nb = _cumulative(pts_b)
    lo, hi = max(xa[0], xb[0]), min(xa[-1], xb[-1]) - EDGE_MARGIN
    if hi - lo < 0.4:
        return None
    g = np.arange(lo, hi, 0.02)
    ln = np.log10(np.interp(g, xa, na))
    ok = (ln > np.log10(nb[-2])) & (ln < np.log10(nb[0]))
    if ok.sum() < 20:
        return None
    mb = np.interp(ln, np.log10(np.maximum(nb, 1e-300))[::-1], xb[::-1])
    f = (mb - g)[ok]
    g = g[ok]
    return Remap(g[0], g[-1], np.polyfit(g, f, DEGREE), g, f)


class Library:
    """Remaps measured inside single runs. reflect and signs build the counterfactual worlds of the E2 null (maps mirrored in mass, or sign-flipped per source class); `shared` lets those worlds
    reuse the remap estimates, which do not depend on the world."""

    def __init__(self, curves, reflect=False, signs=None, shared=None):
        self.curves, self.reflect, self.signs, self._raw, self._cache, self._diff = curves, reflect, signs or {}, shared if shared is not None else {}, {}, {}

    def remaps(self, a, b):
        """[(suite, Remap)] for every library suite that holds both definitions."""
        if (a, b) not in self._cache:
            out = []
            for s, cs in sorted(self.curves.items()):
                if a in cs and b in cs:
                    if (s, a, b) not in self._raw:
                        self._raw[(s, a, b)] = estimate_remap(cs[a], cs[b])
                    r = self._raw[(s, a, b)]
                    if r is not None:
                        out.append((s, r.transformed(self.reflect, self.signs.get(a, 1))))
            self._cache[(a, b)] = out
        return self._cache[(a, b)]

    def apply(self, pts, a, b):
        """The curve as it would be published with definition b instead of a: every mass shifted by the mean remap of the library suites that define it at that mass, the density per dex divided by the
        Jacobian. Points outside the mass range of every library map are dropped. None when no map exists for the pair (even composed through the hub class)."""
        if a == b:
            return pts
        ents = self.remaps(a, b)
        if not ents:
            if HUB in (a, b) or not self.remaps(a, HUB) or not self.remaps(HUB, b):
                return None
            mid = self.apply(pts, a, HUB)
            return self.apply(mid, HUB, b) if mid else []
        if not pts:
            return []
        x = np.array([p[0] for p in pts], float)
        y = np.array([p[1] for p in pts], float)
        f, df = np.full((len(ents), x.size), np.nan), np.full((len(ents), x.size), np.nan)
        for k, (_, r) in enumerate(ents):
            ok = r.contains(x)
            f[k, ok], df[k, ok] = r.f(x[ok]), r.df(x[ok])
        n = np.isfinite(f).sum(axis=0)
        fm, dm = np.nansum(f, axis=0) / np.maximum(n, 1), np.nansum(df, axis=0) / np.maximum(n, 1)
        keep = (n > 0) & (1 + dm > 0.05)
        return list(zip((x + fm)[keep].tolist(), (y[keep] - np.log10(1 + dm[keep])).tolist()))

    def diff(self, a, b):
        """Level-matched maps, delta(phi) = m_B(phi) - m_A(phi) (the earlier design; kept for sensitivity S2)."""
        if (a, b) not in self._diff:
            out = []
            for s, cs in sorted(self.curves.items()):
                if a in cs and b in cs:
                    ma, mb = mass_at(cs[a], PHI_FINE), mass_at(cs[b], PHI_FINE)
                    ok = np.isfinite(ma) & np.isfinite(mb)
                    if ok.sum() >= 5:
                        o = np.argsort(PHI_FINE[ok])
                        out.append((s, PHI_FINE[ok][o], (mb - ma)[ok][o] * self.signs.get(a, 1)))
            self._diff[(a, b)] = out
        return self._diff[(a, b)]

    def delta_phi(self, a, b, phi):
        """Mean over library suites of m_B(phi) - m_A(phi), NaN where no suite defines it; composed through the hub class when the pair was never measured; None when there is no path."""
        if a == b:
            return np.zeros(np.shape(phi))
        ents = self.diff(a, b)
        if ents:
            v = np.array([np.interp(phi, p, d, left=np.nan, right=np.nan) for _, p, d in ents])
            n = np.isfinite(v).sum(axis=0)
            return np.where(n > 0, np.nansum(v, axis=0) / np.maximum(n, 1), np.nan)
        if HUB in (a, b):
            return None
        d1, d2 = self.delta_phi(a, HUB, phi), self.delta_phi(HUB, b, phi)
        return None if d1 is None or d2 is None else d1 + d2


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


def library_curves(recs):
    byid = {r["id"]: r for r in recs}
    return {s: {c: points(byid[i]) for c, i in cs.items()} for s, cs in LIBRARY.items()}


# ---------------------------------------------------------------- mass scatter (amendment A1)
SCATTER_ITERATIONS = 10
SCATTER_STEP = 0.02
SCATTER_PAD = 1.5
GATE_DEX = 0.05
SCATTER_RE = re.compile(r"include the ([0-9.]+) dex random lognormal", re.I)


def scatter_sigma(rec):
    """Lognormal mass scatter (dex) the record states it contains; 0 when none is stated."""
    m = SCATTER_RE.search(rec.get("selection", {}).get("warning", "") or "")
    return float(m.group(1)) if m else 0.0


def _fine(pts):
    x = np.array([p[0] for p in pts], float)
    y = np.array([p[1] for p in pts], float)
    g = np.arange(x[0] - SCATTER_PAD, x[-1] + SCATTER_PAD + 1e-9, SCATTER_STEP)
    ly = np.interp(g, x, y)
    sl, sr = (y[1] - y[0]) / (x[1] - x[0]), (y[-1] - y[-2]) / (x[-1] - x[-2])
    ly = np.where(g < x[0], y[0] + sl * (g - x[0]), ly)
    ly = np.where(g > x[-1], y[-1] + sr * (g - x[-1]), ly)
    return x[0], x[-1], g, 10.0 ** ly


def _kernel(sigma):
    k = np.arange(-4 * sigma, 4 * sigma + 1e-9, SCATTER_STEP)
    w = np.exp(-0.5 * (k / sigma) ** 2)
    return w / w.sum()


def convolve_scatter(pts, sigma):
    """The curve after lognormal scatter of sigma dex is added to every stellar mass (exact forward model of the Eddington effect), on the span of the input curve."""
    x0, x1, g, ph = _fine(pts)
    out = np.convolve(ph, _kernel(sigma), mode="same")
    keep = (g >= x0 - 1e-9) & (g <= x1 + 1e-9)
    return list(zip(g[keep].tolist(), np.log10(np.maximum(out[keep], 1e-300)).tolist()))


def deconvolve_scatter(pts, sigma, iterations=SCATTER_ITERATIONS):
    """Richardson-Lucy removal of sigma dex of lognormal mass scatter. Returns the curve on the span of the input and the lowest mass above which it is trusted (3 sigma above the lower end)."""
    x0, x1, g, obs = _fine(pts)
    w = _kernel(sigma)
    est = obs.copy()
    for _ in range(iterations):
        est = est * np.convolve(obs / np.maximum(np.convolve(est, w, mode="same"), 1e-300), w[::-1], mode="same")
    keep = (g >= x0 - 1e-9) & (g <= x1 + 1e-9)
    return list(zip(g[keep].tolist(), np.log10(np.maximum(est[keep], 1e-300)).tolist())), x0 + 3 * sigma


def validate_scatter():
    """Gate V1: the operators against the released COLIBRE tables, which hold the same runs with (sigma(z) = min(0.1 + 0.1 z, 0.3)) and without Eddington scatter."""
    import yaml
    tab = yaml.safe_load((ROOT / "data" / "raw" / "2509.07960.yml").read_text())["COLIBRE_L200m6"]

    def curve(key, z):
        t = tab[key][f"z{z:.1f}"]
        return [(a, b) for a, b in zip(t["log10_bin_centers"], t["log10_gsmf_values"]) if b is not None and np.isfinite(b)]
    rows = []
    for z in (0, 1, 2, 3, 4):
        sigma = min(0.1 + 0.1 * z, 0.3)
        raw, edd = curve("gsmf_raw", z), curve("gsmf_with_edd_bias", z)
        m_raw, m_edd = mass_at(raw, PHI), mass_at(edd, PHI)
        m_conv = mass_at(convolve_scatter(raw, sigma), PHI)
        dec, lo = deconvolve_scatter(edd, sigma)
        m_dec = np.where(mass_at(edd, PHI) >= lo, mass_at(dec, PHI), np.nan)
        ok_c, ok_d = np.isfinite(m_conv) & np.isfinite(m_edd), np.isfinite(m_dec) & np.isfinite(m_raw)
        rows.append({"z": z, "sigma": sigma, "levels": int(ok_d.sum()), "needed_median": round(float(np.median((m_edd - m_raw)[ok_d])), 4), "needed_max": round(float(np.max(np.abs((m_edd - m_raw)[ok_d]))), 4),
                     "deconvolution_max_error": round(float(np.max(np.abs((m_dec - m_raw)[ok_d]))), 4), "convolution_max_error": round(float(np.max(np.abs((m_conv - m_edd)[ok_c]))), 4)})
    gate = all(r["deconvolution_max_error"] <= GATE_DEX and r["levels"] >= 8 for r in rows if r["z"] >= 2)
    return {"passed": bool(gate), "threshold_dex": GATE_DEX, "rows": rows}


# ---------------------------------------------------------------- suites and the harmonizer
OPS = ("imf", "scatter", "aperture")
BODY = PHI >= -3.0 - 1e-9
TAIL = PHI <= -3.25 + 1e-9


def m_of(curve):
    return mass_at(curve, PHI) if len(curve) >= 2 else np.full(len(PHI), np.nan)


class Suite:
    def __init__(self, name, rec):
        d = rec["definitions"]
        self.name, self.rec, self.pts = name, rec, points(rec)
        self.imf, self.cls, self.sigma = d.get("imf"), CLASS_OF.get(str(d.get("massDefinition"))), scatter_sigma(rec)
        self.native = m_of(self.pts)

    def label(self):
        return (self.imf, self.cls, self.sigma)


class Harmonizer:
    """Applies the operators named in ops to a suite's curve (scatter removed, masses expressed in the reference IMF, every mass remapped to the reference aperture) and reads m(phi) from the result.
    Caches per (suite, label), so permutation and assignment searches stay cheap."""

    def __init__(self, lib, ops=OPS, ref=REF, imf_extra=0.0, by="mass", ref_sigma=0.0, noise=None):
        self.lib, self.ops, self.ref, self.imf_extra, self.by, self.ref_sigma, self.noise = lib, set(ops), ref, imf_extra, by, ref_sigma, noise
        self._curves, self._m, self._dec = {}, {}, {}

    def transform(self, pts, imf, cls):
        """The IMF and aperture operators on a curve. A class with no measured map (None from the library) is left as it is."""
        if "imf" in self.ops and imf is not None:
            shift = imf_shift(imf, self.imf_extra)
            pts = [(x + shift, y) for x, y in pts]
        if "aperture" in self.ops and self.by == "mass" and cls is not None and cls != self.ref:
            out = self.lib.apply(pts, cls, self.ref)
            pts = pts if out is None else out
        return pts

    def curve(self, s, label):
        key = (s.name, label)
        if key not in self._curves:
            imf, cls, sigma = label
            pts = s.pts
            if "scatter" in self.ops and sigma > 0 and not self.ref_sigma:
                if (s.name, sigma) not in self._dec:
                    dec, lo = deconvolve_scatter(s.pts, sigma)
                    self._dec[(s.name, sigma)] = [(x, y) for x, y in dec if x >= lo]
                pts = self._dec[(s.name, sigma)]
            pts = self.transform(pts, imf, cls)
            if "scatter" in self.ops and self.ref_sigma and len(pts) >= 2:
                extra = float(np.sqrt(max(self.ref_sigma ** 2 - sigma ** 2, 0.0)))  # sensitivity S8: bring every curve to the same total scatter instead
                if extra > 1e-9:
                    pts = convolve_scatter(pts, extra)
            self._curves[key] = pts
        return self._curves[key]

    def __call__(self, s, label):
        key = (s.name, label)
        if key not in self._m:
            m = m_of(self.curve(s, label))
            if self.by == "phi" and "aperture" in self.ops and label[1] not in (None, self.ref):  # sensitivity S2: the earlier design, a shift that depends on the abundance
                d = self.lib.delta_phi(label[1], self.ref, PHI)
                if d is not None:
                    m = m + d
            if self.noise is not None:
                m = m + self.noise.get(s.name, 0.0)
            self._m[key] = m
        return self._m[key]

    def matrices(self, suites, labels):
        """Raw and harmonized m(phi), complete cases only: a level counts for a suite only if both exist, so the two variances describe the same suites."""
        raw = np.array([s.native for s in suites])
        har = np.array([self(s, lab) for s, lab in zip(suites, labels)])
        valid = np.isfinite(raw) & np.isfinite(har)
        return np.where(valid, raw, np.nan), np.where(valid, har, np.nan)


def r_point(hz, suites, labels=None, levels=None):
    labels = labels or [s.label() for s in suites]
    raw, har = hz.matrices(suites, labels)
    return reduction(raw, har, levels)


# ---------------------------------------------------------------- E1: documented definitions
def estimand_e1(suites, hz, rng, nboot=NBOOT, nperm=NPERM):
    labels = [s.label() for s in suites]
    raw, har = hz.matrices(suites, labels)
    out = {"R": {"all": reduction(raw, har), "body": reduction(raw, har, BODY), "tail": reduction(raw, har, TAIL)}}
    boot = {k: bootstrap_reduction(raw, har, rng, nboot, lv) for k, lv in (("all", None), ("body", BODY), ("tail", TAIL))}
    out["ci95"] = {k: ci95(v) for k, v in boot.items()}
    out["boot_fraction_positive"] = {k: round(float((v > 0).mean()), 4) for k, v in boot.items()}
    obs = out["R"]["all"]
    perm = []
    for _ in range(nperm):
        order = rng.permutation(len(suites))
        perm.append(r_point(hz, suites, [labels[j] for j in order]))
    perm = np.array([p for p in perm if np.isfinite(p)])
    out["permutation"] = {"n": int(perm.size), "mean": round(float(perm.mean()), 4), "p95": round(float(np.percentile(perm, 95)), 4), "p_value": round(float((1 + (perm >= obs).sum()) / (1 + perm.size)), 4)}
    return out


def by_operator(suites, lib, rng, nboot=NBOOT, **kw):
    """R for each operator alone and with each operator left out (point estimate and cluster-bootstrap interval)."""
    rows = {}
    for name, ops in [(f"{op} only", {op}) for op in OPS] + [(f"without {op}", set(OPS) - {op}) for op in OPS] + [("all three", set(OPS))]:
        hz = Harmonizer(lib, ops, **kw)
        raw, har = hz.matrices(suites, [s.label() for s in suites])
        rows[name] = {"R": round(reduction(raw, har), 4), "ci95": ci95(bootstrap_reduction(raw, har, rng, nboot))}
    return rows


# ---------------------------------------------------------------- E2: upper bound from undocumented apertures
def e2_worlds():
    """The observed world and the counterfactual worlds of the null: every library map mirrored in mass or not, and the map of each source class sign-flipped or not."""
    worlds = []
    for reflect in (False, True):
        for signs in itertools.product((1, -1), repeat=len(LIB_CLASSES)):
            worlds.append((reflect, dict(zip(LIB_CLASSES, signs))))
    return worlds


def upper_bound(suites, curves, world, imf_extra=0.0, shared=None):
    reflect, signs = world
    hz = Harmonizer(Library(curves, reflect, signs, shared), imf_extra=imf_extra)
    free = [i for i, s in enumerate(suites) if s.cls is None]
    base = [hz(s, s.label()) for s in suites]
    raw = np.array([s.native for s in suites])
    best, best_assign = -np.inf, None
    for assign in itertools.product(LIB_CLASSES, repeat=len(free)):
        har = list(base)
        for i, c in zip(free, assign):
            har[i] = hz(suites[i], (suites[i].imf, c, suites[i].sigma))
        har = np.array(har)
        valid = np.isfinite(raw) & np.isfinite(har)
        r = reduction(np.where(valid, raw, np.nan), np.where(valid, har, np.nan))
        if np.isfinite(r) and r > best:
            best, best_assign = r, assign
    return best, dict(zip([suites[i].name for i in free], best_assign or ()))


def estimand_e2(suites, curves):
    shared = {}
    obs, assign = upper_bound(suites, curves, (False, {}), shared=shared)
    null = [upper_bound(suites, curves, w, shared=shared)[0] for w in e2_worlds()[1:]]
    null = np.array([v for v in null if np.isfinite(v)])
    return {"R_ub": round(obs, 4), "assignment": assign, "free_suites": sorted(assign), "null_n": int(null.size), "null_p95": round(float(np.percentile(null, 95)), 4), "null_max": round(float(null.max()), 4),
            "null_median": round(float(np.median(null)), 4), "exceeds_null": bool(obs > np.percentile(null, 95))}


# ---------------------------------------------------------------- E3: universality of the aperture map
def estimand_e3(lib):
    """Leave one library suite out and predict its remap f(M) for a -> reference by the mean of the others, on the mass range all of them share (the direction in which the map is applied)."""
    out = []
    for a in LIB_CLASSES:
        ents = lib.remaps(a, REF) if a != REF else []
        if len(ents) < 2:
            continue
        lo, hi = max(r.lo for _, r in ents), min(r.hi for _, r in ents)
        row = {"pair": f"{a} -> {REF}", "suites": [s for s, _ in ents], "n_suites": len(ents), "common_mass_range": [round(float(lo), 3), round(float(hi), 3)]}
        if hi - lo < 0.5:
            out.append({**row, "testable": False, "reason": "common mass range under 0.5 dex"})
            continue
        grid = np.arange(lo, hi + 1e-9, 0.05)
        D = np.array([r.f(grid) for _, r in ents])
        folds = []
        for i, (s, _) in enumerate(ents):
            pred = D[[j for j in range(len(ents)) if j != i]].mean(axis=0)
            mse0 = float(np.mean(D[i] ** 2))
            folds.append({"left_out": s, "skill": round(1 - float(np.mean((D[i] - pred) ** 2)) / mse0, 4) if mse0 > 0 else None, "mae_dex": round(float(np.mean(np.abs(D[i] - pred))), 4), "rms_map_dex": round(float(np.sqrt(mse0)), 4)})
        full = len(ents) >= 3
        universal = bool(full and all(f["skill"] is not None and f["skill"] > 0 for f in folds) and float(np.mean([f["mae_dex"] for f in folds])) < 0.05)
        out.append({**row, "testable": True, "folds": folds, "leave_one_out_with_three_or_more": full, "universal": universal,
                    "between_suite_sd_dex": round(float(np.mean(np.std(D, axis=0, ddof=1))), 4)})
    return out


def library_summary(lib):
    rows = []
    for a in LIB_CLASSES:
        ents = lib.remaps(a, REF) if a != REF else []
        if not ents:
            continue
        rows.append({"pair": f"{a} -> {REF}", "suites": [s for s, _ in ents], "range": {s: [round(r.lo, 2), round(r.hi, 2)] for s, r in ents},
                     "shift_dex_at": {str(m): {s: (round(float(r.f(m)), 4) if r.lo <= m <= r.hi else None) for s, r in ents} for m in (10.0, 10.5, 11.0, 11.5)}})
    return rows


# ---------------------------------------------------------------- E4: injection and recovery
INJECT_CLASSES = ["30", "50", "100", "total"]
INJECT_NOISE = 0.02


def forward(pts, remap, lam):
    """The curve as it would look in the aperture whose map is lam times `remap`; points outside the map's mass range are dropped."""
    out = []
    for x, y in pts:
        if remap.lo - 1e-9 <= x <= remap.hi + 1e-9:
            jac = 1.0 + lam * float(remap.df(x))
            if jac > 0.05:
                out.append((x + lam * float(remap.f(x)), y - float(np.log10(jac))))
    return out


def estimand_e4(suites, curves, rng, lambdas=LAMBDAS, ndraw=NINJ, nboot=NINJ_BOOT):
    """Start from the harmonized curves (a world with no definition differences), give each suite an aperture class, show it the sky through the forward map of one randomly chosen library suite scaled by lambda,
    add 0.02 dex of digitization noise in log Phi, and run the E1 pipeline with the universal (mean) maps. Reports the recovered against the true R and how often the E1 rule (interval above 0, p < 0.05) is met."""
    lib = Library(curves)
    base = [c for c in (Harmonizer(lib).curve(s, s.label()) for s in suites) if len(c) >= 2]
    n = len(base)
    har0 = np.array([m_of(c) for c in base])
    donors = {c: lib.remaps(REF, c) for c in INJECT_CLASSES if c != REF}
    assert all(donors.values()), donors
    recover = Harmonizer(lib, ("aperture",))
    out = []
    for lam in lambdas:
        r_true, r_est, hit = [], [], 0
        for _ in range(ndraw):
            kind = rng.integers(0, len(INJECT_CLASSES), size=n)
            obs, rec = np.empty((n, len(PHI))), np.empty((len(INJECT_CLASSES), n, len(PHI)))
            for i in range(n):
                c = INJECT_CLASSES[kind[i]]
                cur = base[i] if c == REF else forward(base[i], donors[c][int(rng.integers(0, len(donors[c])))][1], lam)
                cur = [(x, y + e) for (x, y), e in zip(cur, rng.normal(0, INJECT_NOISE, len(cur)))]
                obs[i] = m_of(cur)
                for k, c2 in enumerate(INJECT_CLASSES):
                    rec[k, i] = m_of(recover.transform(cur, None, c2))
            idx = np.arange(n)
            got = rec[kind, idx]

            def masked(a, b, *more):
                v = np.isfinite(a) & np.isfinite(b)
                for x in more:
                    v &= np.isfinite(x)
                return np.where(v, a, np.nan), np.where(v, b, np.nan)
            est_t, tru = reduction(*masked(obs, got, har0)), reduction(*masked(obs, har0, got))
            test = reduction(*masked(obs, got))
            if not (np.isfinite(est_t) and np.isfinite(tru) and np.isfinite(test)):
                continue
            boot = bootstrap_reduction(*masked(obs, got), rng, nboot)
            perm = []
            for _ in range(nboot):
                perm.append(reduction(*masked(obs, rec[kind[rng.permutation(n)], idx])))
            perm = np.array([p for p in perm if np.isfinite(p)])
            p = (1 + (perm >= test).sum()) / (1 + perm.size)
            r_true.append(tru)
            r_est.append(est_t)
            hit += int(boot.size > 0 and np.percentile(boot, 2.5) > 0 and p < 0.05)
        out.append({"lambda": lam, "draws": len(r_est), "R_true_mean": round(float(np.mean(r_true)), 4), "R_recovered_mean": round(float(np.mean(r_est)), 4),
                    "recovery_rmse": round(float(np.sqrt(np.mean((np.array(r_est) - np.array(r_true)) ** 2))), 4), "detection_rate": round(hit / max(len(r_est), 1), 4)})
    return out


# ---------------------------------------------------------------- sensitivity analyses
def sensitivities(recs, suites, curves, rng):
    lib = Library(curves)
    out = {}
    out["S1_reference_50pkpc"] = round(r_point(Harmonizer(lib, ref="50"), suites), 4)
    out["S2_map_applied_by_abundance"] = round(r_point(Harmonizer(lib, by="phi"), suites), 4)
    out["S3_levels_phi_ge_-3.75"] = round(r_point(Harmonizer(lib), suites, levels=PHI >= -3.75 - 1e-9), 4)
    out["S4_imf_offsets_plus_0.05"] = round(r_point(Harmonizer(lib, imf_extra=0.05), suites), 4)
    out["S4_imf_offsets_minus_0.05"] = round(r_point(Harmonizer(lib, imf_extra=-0.05), suites), 4)

    def draw(src, by_unit):
        runs = sorted(by_unit)
        return by_unit[runs[int(rng.integers(0, len(runs)))]] if runs else []
    vals = []
    for _ in range(NRAND):
        chosen, _ = choose_suites(recs, pick=draw)
        ss = [Suite(n, r) for n, r in sorted(chosen.items())]
        vals.append(r_point(Harmonizer(lib), ss))
    vals = np.array([v for v in vals if np.isfinite(v)])
    out["S5_random_fiducial_run"] = {"draws": int(vals.size), "median": round(float(np.median(vals)), 4), "ci95": ci95(vals), "fraction_positive": round(float((vals > 0).mean()), 4)}
    out["S6_leave_one_suite_out"] = {s.name: round(r_point(Harmonizer(lib), [t for t in suites if t is not s]), 4) for s in suites}
    chosen7, _ = choose_suites(recs, include_ambiguous=True)
    s7 = [Suite(n, r) for n, r in sorted(chosen7.items())]
    raw7, har7 = Harmonizer(lib).matrices(s7, [s.label() for s in s7])
    out["S7_include_unstated_normalisation"] = {"suites": [s.name for s in s7], "R": round(reduction(raw7, har7), 4), "ci95": ci95(bootstrap_reduction(raw7, har7, rng, NBOOT))}
    raw8, har8 = Harmonizer(lib, ref_sigma=0.3).matrices(suites, [s.label() for s in suites])
    out["S8_convolve_all_to_sigma_0.3"] = {"R": round(reduction(raw8, har8), 4), "ci95": ci95(bootstrap_reduction(raw8, har8, rng, NBOOT)), "placebo_smoothing_only_R": round(float(reduction(*_smooth_only(suites))), 4)}
    vals = []
    for _ in range(NRAND):
        noise = {s.name: rng.normal(0, 0.03, len(PHI)) for s in suites if s.sigma > 0}
        vals.append(r_point(Harmonizer(lib, noise=noise), suites))
    vals = np.array([v for v in vals if np.isfinite(v)])
    out["S9_deconvolution_error_0.03"] = {"median": round(float(np.median(vals)), 4), "ci95": ci95(vals)}
    return out


def _smooth_only(suites):
    """Placebo for S8: add 0.3 dex of scatter to every curve and nothing else, so the change in dispersion is the smoothing alone."""
    raw = np.array([s.native for s in suites])
    har = np.array([m_of(convolve_scatter(s.pts, 0.3)) for s in suites])
    valid = np.isfinite(raw) & np.isfinite(har)
    return np.where(valid, raw, np.nan), np.where(valid, har, np.nan)


# ---------------------------------------------------------------- assembly
def suite_table(suites, lib):
    rows = []
    for s in suites:
        row = {"suite": s.name, "record": s.rec["id"], "run": s.rec.get("run"), "z": s.rec["epoch"]["zRepresentative"], "imf": s.imf, "mass_definition": s.rec["definitions"].get("massDefinition"),
               "aperture_class": s.cls, "stated_scatter_dex": s.sigma, "levels_defined": int(np.isfinite(s.native).sum()), "phi_lowest_defined": float(PHI[np.isfinite(s.native)].min()) if np.isfinite(s.native).any() else None}
        for op in OPS:
            m = Harmonizer(lib, {op})(s, s.label())
            ok = np.isfinite(m) & np.isfinite(s.native)
            row[f"mean_shift_{op}_dex"] = round(float(np.mean((m - s.native)[ok])), 4) if ok.any() else None
        rows.append(row)
    return rows


def level_table(raw, har):
    vr, vh = level_variance(raw), level_variance(har)
    n = np.isfinite(raw).sum(axis=0)
    return [{"phi": float(PHI[k]), "suites": int(n[k]), "sd_raw_dex": None if not np.isfinite(vr[k]) else round(float(np.sqrt(vr[k])), 4),
             "sd_harmonized_dex": None if not np.isfinite(vh[k]) else round(float(np.sqrt(vh[k])), 4)} for k in range(len(PHI))]


def run():
    recs = adb.load()
    rng = np.random.default_rng(SEED)
    gate = validate_scatter()
    curves = library_curves(recs)
    lib = Library(curves)
    chosen, excluded = choose_suites(recs)
    suites = [Suite(n, r) for n, r in sorted(chosen.items())]
    ops = OPS if gate["passed"] else ("imf", "aperture")
    hz = Harmonizer(lib, ops)
    raw, har = hz.matrices(suites, [s.label() for s in suites])
    res = {"version": json.loads((ROOT / "data" / "release.json").read_text())["version"], "protocol": "docs/PROTOCOL-harmonization.md",
           "parameters": {"seed": SEED, "phi_levels": [float(v) for v in PHI], "reference_aperture_pkpc": int(REF), "min_suites_per_level": MIN_SUITES, "z_max": Z_MAX, "bootstrap": NBOOT, "permutations": NPERM,
                          "random_fiducial_draws": NRAND, "injection_draws": NINJ, "injection_bootstrap": NINJ_BOOT, "lambdas": list(LAMBDAS), "scatter_iterations": SCATTER_ITERATIONS, "imf_dex": IMF_DEX},
           "gate_V1": gate, "operators_used": list(ops), "suites": suite_table(suites, lib), "excluded_suites": excluded, "levels": level_table(raw, har),
           "library": {"summary": library_summary(lib), "records": {s: dict(c) for s, c in LIBRARY.items()}}, "E3": estimand_e3(lib)}
    res["E1"] = estimand_e1(suites, hz, rng)
    res["operators"] = by_operator(suites, lib, rng)
    res["E2"] = estimand_e2(suites, curves)
    res["E4"] = estimand_e4(suites, curves, rng)
    res["sensitivity"] = sensitivities(recs, suites, curves, rng)
    res["verdicts"] = verdicts(res)
    res["deviations"] = deviations(res)
    return res


def verdicts(res):
    e1, sens = res["E1"], res["sensitivity"]
    r = e1["R"]["all"]
    lo = e1["ci95"]["all"][0]
    signs = [np.sign(r), np.sign(sens["S1_reference_50pkpc"]), np.sign(sens["S2_map_applied_by_abundance"])]
    e1_ok = bool(lo > 0 and e1["permutation"]["p_value"] < 0.05 and len(set(signs)) == 1 and r > 0)
    e3 = [t for t in res["E3"] if t.get("testable") and t.get("leave_one_out_with_three_or_more")]
    detect = [row["lambda"] for row in res["E4"] if row["lambda"] > 0 and row["detection_rate"] >= 0.8]
    return {"E1": {"supported": e1_ok, "R": r, "ci95_lower": lo, "permutation_p": e1["permutation"]["p_value"], "sign_consistent_S1_S2": len(set(signs)) == 1},
            "E2": {"R_ub": res["E2"]["R_ub"], "exceeds_null": res["E2"]["exceeds_null"]},
            "E3": {"universal": {t["pair"]: t["universal"] for t in e3}, "tested_with_three_or_more_suites": [t["pair"] for t in e3]},
            "E4": {"smallest_lambda_detected_in_80_percent": min(detect) if detect else None, "false_positive_rate_at_lambda_0": next(r["detection_rate"] for r in res["E4"] if r["lambda"] == 0)}}


def deviations(res):
    d = ["An E3 was computed under the earlier level-matched design and its outcome was seen before amendment A2 replaced the aperture operator (details in section 8 of the protocol); the rule and the new result are the ones reported here.",
         "The E1 permutation test shuffles the complete label (IMF, aperture class, stated scatter) among all suites, including those with no measured map, rather than only among correctable suites; the null it generates is therefore somewhat wider than the protocol described.",
         "The Illustris 30 pkpc curve and its total curve come from different papers (Pillepich+18 and Genel+14), whereas the EAGLE and COLIBRE maps come from one figure each; the protocol listed three codes without that difference.",
         "E3 is evaluated in the direction in which the map is applied (to 30 pkpc); the protocol named the pair 30 pkpc to total, which is the same map in the other direction."]
    if not res["gate_V1"]["passed"]:
        d.append("Gate V1 failed: the scatter operator was not used and FLAMINGO was left uncorrected; E2 did not vary its scatter as the protocol says it should.")
    return d


def write_outputs(res):
    out = ROOT / "data" / "analysis" / "harmonization.json"
    out.write_text(json.dumps(res, indent=1) + "\n")
    (ROOT / "docs" / "ANALYSIS-harmonization.md").write_text(render(res))


def main():
    res = run()
    write_outputs(res)
    v = res["verdicts"]
    print(f"harmonization: E1 R={v['E1']['R']:.3f} (CI lower {v['E1']['ci95_lower']:.3f}, p={v['E1']['permutation_p']}) supported={v['E1']['supported']}; E2 R_ub={v['E2']['R_ub']:.3f} exceeds null={v['E2']['exceeds_null']}")


def render(res):
    raise NotImplementedError


if __name__ == "__main__":
    main()
