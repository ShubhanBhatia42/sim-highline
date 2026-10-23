"""Tests of the observer layer in sim_highline.py (Gaussian mass scatter, mass offset, completeness, sSFR detection floor).
What is checked: (1) the scattered density against closed forms and against the defining integral evaluated by an independent adaptive quadrature; (2) invariants (zero scatter returns the input,
number is conserved, offsets and cuts behave); (3) the Python results equal tests/fixtures/observer-fixture.json, which scripts/test-observer.mjs also reproduces from observer-lib.js;
(4) the checks fail if the convolution is replaced by a no-op. `python3 scripts/test_observer.py --write-fixture` rewrites the fixture from the Python code (only after a deliberate change)."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import numpy as np
    from scipy import integrate
except ImportError:
    print("observer test skipped: numpy/scipy not installed")
    raise SystemExit(0)
import sim_highline as sh

FIXTURE = ROOT / "tests" / "fixtures" / "observer-fixture.json"
LN10 = math.log(10)
TOL_PAR = 1e-9            # Python against the fixture (JS is held to the same number)


def schechter_y(x, alpha, xs, phi):
    """log10 of the single Schechter function per dex."""
    u = x - xs
    return math.log10(LN10 * phi * 10 ** ((alpha + 1) * u) * math.exp(-(10 ** u)))


def schechter_n(x, alpha, xs, phi):
    """The same function in linear units, zero where it underflows."""
    u = x - xs
    return 0.0 if u > 2.8 else LN10 * phi * 10 ** ((alpha + 1) * u) * math.exp(-(10 ** u))


def pts_from(f, xs, band=None):
    return [{"x": float(x), "y": f(x), **({"yLow": f(x) - band, "yHigh": f(x) + band} if band else {})} for x in xs]


def checks(sp):
    """The whole battery against a scatter function sp(points, sigma, **opts); returns how many checks ran. Raises AssertionError on the first failure."""
    n = 0

    # 1a. a pure power law: the Eddington-biased density is the input times exp((beta sigma ln10)^2 / 2), exactly, edges included (the continuation of a straight line is exact)
    beta, sig = -1.4, 0.3
    pl = pts_from(lambda x: beta * x + 3.0, np.arange(8, 11.01, 0.25))
    out = sp(pl, sig)
    want = math.log10(math.exp(0.5 * (beta * sig * LN10) ** 2))
    assert want > 0.2
    for a, b in zip(out, pl):
        assert abs((a["y"] - b["y"]) - want) < 1e-9, (a, want)
    n += 1

    # 1b. a Gaussian (lognormal) mass function of width s convolved with scatter sigma is a Gaussian of width sqrt(s^2 + sigma^2) and amplitude A s / sqrt(s^2 + sigma^2)
    c, s, A = 10.5, 0.45, 2e-3
    f = lambda x: math.log10(A * math.exp(-0.5 * ((x - c) / s) ** 2))
    ln = pts_from(f, np.round(np.arange(7.5, 13.5001, 0.01), 6))
    for sg in (0.1, 0.2, 0.3):
        out = sp(ln, sg)
        se = math.hypot(s, sg)
        worst = max(abs(q["y"] - math.log10(A * s / se * math.exp(-0.5 * ((q["x"] - c) / se) ** 2))) for q in out if 8.4 <= q["x"] <= 12.6)
        assert worst < 2e-4, (sg, worst)       # the tolerance is the linear-in-log interpolation of the input between points 0.01 dex apart
    n += 1

    # 1c. a Schechter function: (i) the closed-form series  n_obs = ln10 phi sum_k (-1)^k / k! 10^((b+k) u) exp((b+k)^2 s^2 / 2), s = sigma ln10, b = alpha + 1 (an expansion in 10^u, used where u <= -1);
    # (ii) the defining integral by adaptive quadrature at every mass; both on points 0.01 dex apart, so the tolerance is the interpolation of the input, 1e-3 dex
    alpha, xs0, phi = -1.2, 10.7, 1e-3
    sc = pts_from(lambda x: schechter_y(x, alpha, xs0, phi), np.round(np.arange(7.0, 13.0001, 0.01), 6))
    for sg in (0.1, 0.2, 0.3):
        out = sp(sc, sg)
        b, s2 = alpha + 1, (sg * LN10) ** 2
        for q in out:
            if not (8.4 <= q["x"] <= 12.0):
                continue
            u = q["x"] - xs0
            if u <= -1:
                ser, prev = 0.0, float("inf")
                for k in range(0, 60):               # an asymptotic series: stop at the smallest term
                    term = (-1) ** k / math.factorial(k) * 10 ** ((b + k) * u) * math.exp((b + k) ** 2 * s2 / 2)
                    if abs(term) > prev:
                        break
                    ser, prev = ser + term, abs(term)
                ser *= LN10 * phi
                assert abs(q["y"] - math.log10(ser)) < 1e-3, ("series", sg, q["x"], q["y"], math.log10(ser))
            ref, _ = integrate.quad(lambda m: schechter_n(m, alpha, xs0, phi) * math.exp(-0.5 * ((q["x"] - m) / sg) ** 2) / (sg * math.sqrt(2 * math.pi)), q["x"] - 9 * sg, q["x"] + 9 * sg, points=[q["x"]], epsabs=0, epsrel=1e-12, limit=400)
            assert abs(q["y"] - math.log10(ref)) < 1e-3, ("quad", sg, q["x"], q["y"], math.log10(ref))
    # and the change is the Eddington bias: above the knee the scattered density is higher than the input by more than the interpolation tolerance
    out = sp(sc, 0.3)
    assert [q for q in out if q["x"] == 11.5][0]["y"] - [q for q in sc if q["x"] == 11.5][0]["y"] > 0.2
    n += 1

    # 1d. mass-dependent scatter: sigma(m) = 0.4 at m = 8 falling linearly to 0.15 at m = 12 (a table), power law input, against quadrature of  integral 10^(b m) N(x - m; sigma(m)) dm
    tab = {"x": [8.0, 12.0], "sigma": [0.4, 0.15]}
    sfun = lambda m: float(np.interp(m, tab["x"], tab["sigma"]))
    pl2 = pts_from(lambda x: -1.0 * x + 2.0, np.arange(7.0, 13.01, 0.25))
    out = sp(pl2, tab)
    for q in out:
        if not (9.0 <= q["x"] <= 11.0):
            continue
        ref, _ = integrate.quad(lambda m: 10 ** (-1.0 * m + 2.0) * math.exp(-0.5 * ((q["x"] - m) / sfun(m)) ** 2) / (sfun(m) * math.sqrt(2 * math.pi)), q["x"] - 4, q["x"] + 4, points=[q["x"]], epsabs=0, epsrel=1e-12, limit=400)
        assert abs(q["y"] - math.log10(ref)) < 1e-6, (q["x"], q["y"], math.log10(ref))
    # a table that is constant must agree with the number (12 digits)
    a, b2 = sp(pl2, {"x": [0.0, 20.0], "sigma": [0.2, 0.2]}), sp(pl2, 0.2)
    assert max(abs(p["y"] - q["y"]) for p, q in zip(a, b2)) < 1e-12
    n += 1

    # 2a. zero scatter returns the input, exactly
    pt = pts_from(lambda x: schechter_y(x, alpha, xs0, phi), np.arange(8, 12.01, 0.3), band=0.05)
    z = sp(pt, 0)
    assert [(p["x"], p["y"], p["yLow"], p["yHigh"]) for p in z] == [(p["x"], p["y"], p["yLow"], p["yHigh"]) for p in pt]
    # ... and a very small scatter is close to it (continuity): 0.002 dex on a smooth curve changes y by well under 1e-3 dex in the interior
    sm = sp(pl, 0.002)
    assert max(abs(a["y"] - b["y"]) for a, b in zip(sm, pl)) < 1e-3
    n += 1

    # 2b. number is conserved: a tent density 10^(-a|x - c|) (log-linear, so the input is exact) integrates to 2 / (a ln10); the scattered density integrates to the same, for a constant and a mass-dependent sigma
    a_, c0 = 2.5, 10.0
    tent = pts_from(lambda x: -a_ * abs(x - c0), np.round(np.arange(c0 - 6, c0 + 6.0001, 0.01), 6))
    total = 2 / (a_ * LN10)
    for spec in (0.1, 0.3, {"x": [4.0, 16.0], "sigma": [0.35, 0.1]}):
        out = sp(tent, spec)
        got = float(np.trapz([10 ** q["y"] for q in out], [q["x"] for q in out])) if hasattr(np, "trapz") else float(np.trapezoid([10 ** q["y"] for q in out], [q["x"] for q in out]))
        assert abs(got / total - 1) < 2e-4, (spec, got, total)      # 7e-5 of this is the grid sum across the kink of the tent (derivative jump 2 a ln10), the rest is smaller
    n += 1

    # 2c. bands: constant input error 0.05 dex in every point; independent errors average, so the scattered error is smaller than 0.05 and larger than 0, and equals 0.05 at no scatter;
    # an input without bands gets none; an input with one-sided asymmetric bands keeps the asymmetry
    bd = pts_from(lambda x: beta * x + 3.0, np.arange(8, 11.01, 0.25), band=0.05)
    o = sp(bd, 0.3)
    mid = [q for q in o if 8.9 <= q["x"] <= 10.1]
    assert all(0.0 < q["yHigh"] - q["y"] < 0.05 and 0.0 < q["y"] - q["yLow"] < 0.05 for q in mid)
    assert all("yHigh" not in q for q in sp(pl, 0.3))
    asym = [{**p, "yHigh": p["y"] + 0.10, "yLow": p["y"] - 0.02} for p in pl]
    oa = sp(asym, 0.3)
    assert all((q["yHigh"] - q["y"]) > 3 * (q["y"] - q["yLow"]) for q in oa)
    n += 1

    # 2d. edge flags: the end points of a 3-dex curve scattered by 0.3 dex draw most of their density from the continuation; the middle does not
    o = sp(pl, 0.3)
    assert o[0]["edge"] and o[-1]["edge"] and not o[len(o) // 2]["edge"]
    assert all(0 <= q["edgeShare"] <= 1 for q in o)
    n += 1
    return n


def other_checks():
    """Offset, completeness, floors, Poisson bands, composition."""
    n = 0
    pt = pts_from(lambda x: -1.0 - 0.5 * (x - 8), np.arange(8, 11.01, 0.5), band=0.05)
    pt[0]["count"] = 400.0
    # offset: x moves by delta, nothing else; the inverse restores the input
    sh_ = sh.shift_points(pt, -0.2)
    assert all(abs(a["x"] - (b["x"] - 0.2)) < 1e-12 and a["y"] == b["y"] and a["yLow"] == b["yLow"] for a, b in zip(sh_, pt))
    back = sh.shift_points(sh_, 0.2)
    assert all(abs(a["x"] - b["x"]) < 1e-12 for a, b in zip(back, pt))
    n += 1
    # hard cut: only x >= limit stay; cutting twice changes nothing
    cut = sh.completeness_cut(pt, 9.0)
    assert [p["x"] for p in cut] == [9.0, 9.5, 10.0, 10.5, 11.0] and sh.completeness_cut(cut, 9.0) == cut
    n += 1
    # smooth completeness: C(m50) = 1/2, y lowered by log10 2 there, C -> 1 far above, counts times C, bands move with y
    w = sh.completeness_weight(pt, 9.5, 0.2)
    mid = [p for p in w if p["x"] == 9.5][0]
    ref = [p for p in pt if p["x"] == 9.5][0]
    assert abs(mid["y"] - (ref["y"] - math.log10(2))) < 1e-12 and abs(mid["yHigh"] - mid["y"] - 0.05) < 1e-12
    assert abs(w[-1]["completeness"] - 1) < 1e-3 and abs(w[0]["count"] - 400 * w[0]["completeness"]) < 1e-9
    n += 1
    # Poisson bands: 100 counts is 10 per cent; one count has no lower bound; a point with a band is left alone
    pb = sh.poisson_bands([{"x": 9, "y": 0.0, "count": 100.0}, {"x": 10, "y": 0.0, "count": 1.0}, {"x": 11, "y": 0.0, "count": 50.0, "yLow": -0.3, "yHigh": 0.3}])
    assert abs(pb[0]["yHigh"] - math.log10(1.1)) < 1e-12 and abs(pb[0]["yLow"] - math.log10(0.9)) < 1e-12
    assert math.isnan(pb[1]["yLow"]) and pb[2]["yLow"] == -0.3
    n += 1
    # the pipeline applies scatter, then offset, then completeness, and says so
    sc = pts_from(lambda x: schechter_y(x, -1.2, 10.7, 1e-3), np.arange(8, 12.01, 0.25))
    p, steps = sh.observe(sc, sigma=0.2, offset=-0.1, completeness=(9.0, 0.2), m_lim=8.5)
    assert [s.split(" ")[0] for s in steps] == ["Gaussian", "mass", "smooth", "limiting"] and min(q["x"] for q in p) >= 8.5
    manual = sh.completeness_cut(sh.completeness_weight(sh.shift_points(sh.scatter_points(sc, 0.2), -0.1), 9.0, 0.2), 8.5)
    assert all(abs(a["y"] - b["y"]) < 1e-12 and a["x"] == b["x"] for a, b in zip(p, manual)) and len(p) == len(manual)
    n += 1
    # sSFR floor on a curve of medians: points whose median is below the floor go, the lower band is raised to the floor
    ss = [{"x": 9.0, "y": -9.5, "yLow": -10.5, "yHigh": -9.0}, {"x": 10.0, "y": -10.5, "yLow": -12.0, "yHigh": -9.8}, {"x": 11.0, "y": -12.0, "yLow": -13.0, "yHigh": -10.9}]
    f = sh.ssfr_floor_points(ss, -11.0)
    assert [p["x"] for p in f] == [9.0, 10.0] and f[0].get("clipped") is None and f[1]["yLow"] == -11.0 and f[1]["clipped"]
    ft = sh.ssfr_floor_points(ss, {"x": [9.0, 11.0], "floor": [-10.0, -12.5]})      # floor -10.0 at 9, -11.25 at 10, -12.5 at 11: the median at 9.0 (-9.5) stays, at 10.0 (-10.5) stays, at 11.0 (-12.0) stays
    assert [p["x"] for p in ft] == [9.0, 10.0, 11.0] and ft[1]["yLow"] == -11.25
    ft2 = sh.ssfr_floor_points(ss, {"x": [9.0, 11.0], "floor": [-10.0, -11.0]})     # floor -10.5 at 10: a median of exactly -10.5 stays; -12.0 at 11 is below -11.0 and goes
    assert [p["x"] for p in ft2] == [9.0, 10.0]
    assert sh.sfr_floor_to_ssfr(-1.0, 10.0) == -11.0
    n += 1
    # sSFR floor on counts: nothing removed when the floor is below every bin (quantiles then equal those of the project's own statistics), half a bin removed at the edge
    import distribution_stats as D
    fx = json.loads((ROOT / "tests" / "fixtures" / "distribution-fixture.json").read_text())
    st = D.stats(fx["input"])
    d = fx["input"]
    i = next(k for k, t in enumerate(st["n"]) if t >= 10)
    r0 = sh.ssfr_floor_row(d["counts"][i], d["yEdges"], d["yEdges"][0] - 1.0, levels=(0.16, 0.5, 0.84))
    assert r0["fractionDetected"] == 1.0 and all(abs(a - b) < 1e-6 for a, b in zip(r0["quantiles"], [st["quantiles"][k][i] for k in (1, 2, 3)]))
    rr = sh.ssfr_floor_row([10, 10, 10, 10], [-13, -12, -11, -10, -9], -11.5)
    assert rr["detected"] == 25 and abs(rr["fractionDetected"] - 0.625) < 1e-12 and rr["quantiles"][1] > -11.0
    n += 1
    # inputs that cannot be handled say so
    for bad in (lambda: sh.scatter_points([{"x": 9, "y": 0}], 0.2), lambda: sh.scatter_points([{"x": 9, "y": 0}, {"x": 9, "y": 1}], 0.2), lambda: sh.scatter_points([{"x": 8, "y": 0}, {"x": 10, "y": 1}], 0.2),
                lambda: sh.scatter_points([{"x": 8, "y": 0}, {"x": 8.5, "y": 1}], -0.1), lambda: sh.scatter_points([{"x": 8, "y": 0}, {"x": 8.5, "y": 1}], "wide"), lambda: sh.completeness_fraction(9, 9, 0)):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("an invalid input was accepted")
    n += 1
    return n


def fixture_cases():
    xs = [7.9, 8.3, 8.7, 9.1, 9.6, 10.0, 10.3, 10.6, 10.9, 11.2, 11.5, 11.8]
    smf = []
    for i, x in enumerate(xs):
        y = round(schechter_y(x, -1.3, 10.8, 1.2e-3), 6)
        smf.append({"x": x, "y": y, "yLow": round(y - 0.03 - 0.01 * i, 6), "yHigh": round(y + 0.05 + 0.012 * i, 6), "count": float(max(3, int(40000 * 10 ** y)))})
    ssfr = [{"x": 9.0, "y": -9.6, "yLow": -10.4, "yHigh": -9.2}, {"x": 9.5, "y": -9.9, "yLow": -11.0, "yHigh": -9.4}, {"x": 10.0, "y": -10.4, "yLow": -12.0, "yHigh": -9.7}, {"x": 10.5, "y": -11.2, "yLow": -12.8, "yHigh": -10.2}, {"x": 11.0, "y": -11.9, "yLow": -13.0, "yHigh": -10.9}]
    return [
        {"name": "scatter constant 0.2", "op": "scatter", "points": smf, "params": {"sigma": 0.2}},
        {"name": "scatter constant 0.3, no Poisson bands", "op": "scatter", "points": smf, "params": {"sigma": 0.3, "opts": {"poisson": False}}},
        {"name": "scatter mass-dependent table", "op": "scatter", "points": smf, "params": {"sigma": {"x": [8.0, 12.0], "sigma": [0.4, 0.15]}}},
        {"name": "scatter small sigma, coarse grid options", "op": "scatter", "points": smf, "params": {"sigma": 0.02, "opts": {"step": 0.01, "edgeFit": 2}}},
        {"name": "scatter zero", "op": "scatter", "points": smf, "params": {"sigma": 0}},
        {"name": "shift", "op": "shift", "points": smf, "params": {"offset": -0.15}},
        {"name": "cut", "op": "cut", "points": smf, "params": {"mLim": 9.1}},
        {"name": "weight", "op": "weight", "points": smf, "params": {"m50": 9.3, "width": 0.25}},
        {"name": "poisson", "op": "poisson", "points": [{k: v for k, v in p.items() if k not in ("yLow", "yHigh")} for p in smf], "params": {}},
        {"name": "observe all", "op": "observe", "points": smf, "params": {"sigma": 0.25, "offset": 0.1, "mLim": 8.5, "completeness": {"m50": 8.9, "width": 0.2}}},
        {"name": "ssfr floor table", "op": "floorPoints", "points": ssfr, "params": {"floor": {"x": [9.0, 11.0], "floor": [-10.5, -12.0]}}},
        {"name": "ssfr floor number", "op": "floorPoints", "points": ssfr, "params": {"floor": -11.0}},
        {"name": "ssfr floor row", "op": "floorRow", "points": [], "params": {"row": [3, 8, 20, 41, 60, 35, 12, 4], "yEdges": [-13.0, -12.5, -12.0, -11.5, -11.0, -10.5, -10.0, -9.5, -9.0], "floorLog": -11.2}},
    ]


def py_case(c):
    p, a = c["points"], c["params"]
    if c["op"] == "scatter":
        return sh.scatter_points(p, a["sigma"], **a.get("opts", {}))
    if c["op"] == "shift":
        return sh.shift_points(p, a["offset"])
    if c["op"] == "cut":
        return sh.completeness_cut(p, a["mLim"])
    if c["op"] == "weight":
        return sh.completeness_weight(p, a["m50"], a["width"])
    if c["op"] == "poisson":
        return sh.poisson_bands(p)
    if c["op"] == "observe":
        comp = a.get("completeness")
        pts, steps = sh.observe(p, sigma=a.get("sigma"), offset=a.get("offset", 0.0), m_lim=a.get("mLim"), completeness=(comp["m50"], comp["width"]) if comp else None)
        return {"points": pts, "steps": steps}
    if c["op"] == "floorPoints":
        return sh.ssfr_floor_points(p, a["floor"])
    if c["op"] == "floorRow":
        return sh.ssfr_floor_row(a["row"], a["yEdges"], a["floorLog"])
    raise KeyError(c["op"])


def plain(v):
    """JSON-ready: NaN becomes null, numpy numbers become floats."""
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, float, np.floating, np.integer)):
        return None if not math.isfinite(float(v)) else float(v)
    return v


def same(a, b, path="", tol=TOL_PAR):
    if isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b), (path, sorted(a), sorted(b) if isinstance(b, dict) else b)
        for k in a:
            same(a[k], b[k], f"{path}.{k}", tol)
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), (path, len(a), len(b) if isinstance(b, list) else b)
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, f"{path}[{i}]", tol)
    elif isinstance(a, bool) or isinstance(a, str) or a is None:
        assert a == b, (path, a, b)
    else:
        assert b is not None and abs(a - b) <= tol * max(1.0, abs(a)), (path, a, b)


if "--write-fixture" in sys.argv:
    cases = fixture_cases()
    for c in cases:
        c["expected"] = plain(py_case(c))
    FIXTURE.write_text(json.dumps({"note": "Inputs and the results of sim_highline.py (scripts/test_observer.py --write-fixture); scripts/test-observer.mjs requires observer-lib.js to reproduce them to 1e-9. NaN is written as null.", "tolerance": TOL_PAR, "cases": cases}, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {FIXTURE} ({len(cases)} cases)")
    raise SystemExit(0)

n1 = checks(sh.scatter_points)
n2 = other_checks()

# the checks must fail when the convolution is a no-op (and when it is a different, wrong convolution)
def noop(points, sigma, **opts):
    return [{**p, "edgeShare": 0.0, "edge": False} for p in sorted(points, key=lambda q: q["x"])]


def half_width(points, sigma, **opts):
    return sh.scatter_points(points, (sigma / 2) if isinstance(sigma, (int, float)) else sigma, **opts)


for name, broken in (("no-op", noop), ("half the scatter", half_width)):
    try:
        checks(broken)
    except AssertionError:
        continue
    raise AssertionError(f"the checks did not fail for a {name} convolution")

# every public function says what it assumes
for fn in (sh.scatter_points, sh.shift_points, sh.completeness_cut, sh.completeness_weight, sh.completeness_fraction, sh.observe, sh.ssfr_floor_points, sh.ssfr_floor_row, sh.poisson_bands):
    assert fn.__doc__ and len(fn.__doc__) > 80, fn.__name__
assert "Assumption" in sh.scatter_points.__doc__ and "Assumes" in sh.shift_points.__doc__ and "A convenient shape" in sh.completeness_fraction.__doc__ and "does not recompute" in sh.ssfr_floor_points.__doc__

# parity with the fixture that observer-lib.js also reproduces
fx = json.loads(FIXTURE.read_text())
assert [c["name"] for c in fx["cases"]] == [c["name"] for c in fixture_cases()], "fixture cases differ from the test's; rewrite with --write-fixture only if the change is deliberate"
for c in fx["cases"]:
    got = plain(py_case(c))
    same(got, c["expected"], c["name"])
print(f"observer tests passed: {n1 + n2} check groups, analytic and quadrature agreement, invariants, {len(fx['cases'])} fixture cases equal to the stored results, and a no-op convolution is caught")
