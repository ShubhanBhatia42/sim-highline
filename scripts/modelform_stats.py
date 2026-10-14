"""Small statistical helpers for the model-form analysis (numpy only): the Student t and F distributions through the regularized incomplete beta function, the Pitman-Morgan test for two correlated
variances, Gaussian-process draws and a deterministic quadratic ridge emulator. Each is tested against known values in scripts/test_model_form.py."""
import math

import numpy as np


def _betacf(a, b, x, itmax=400, eps=3e-14):
    """Continued fraction of the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def t_sf(t, df):
    """P(T > t) for Student's t with df degrees of freedom."""
    x = df / (df + t * t)
    p = 0.5 * betainc(0.5 * df, 0.5, x)
    return p if t >= 0 else 1.0 - p


def t_ppf(p, df):
    """Quantile of Student's t by bisection (p in (0, 1))."""
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if 1.0 - t_sf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def f_sf(f, d1, d2):
    """P(F > f) for the F distribution with d1 and d2 degrees of freedom."""
    if f <= 0:
        return 1.0
    return betainc(0.5 * d2, 0.5 * d1, d2 / (d2 + d1 * f))


def pitman_morgan(x, y):
    """Pitman-Morgan test of equal variances of two paired samples (exact under bivariate normality). Returns the ratio var(y)/var(x), the statistic and the one-sided p-value for var(y) > var(x)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    sx, sy = x.var(ddof=1), y.var(ddof=1)
    r = np.corrcoef(x, y)[0, 1]
    if sx <= 0 or sy <= 0 or abs(r) >= 1 - 1e-12 or n < 4:
        return float("nan"), float("nan"), float("nan")
    t = (sy - sx) * math.sqrt(n - 2) / (2.0 * math.sqrt(sx * sy * (1.0 - r * r)))
    return float(sy / sx), float(t), float(t_sf(t, n - 2))


def gp_draws(grid, amp, length, rng, n=1):
    """n draws of a zero-mean Gaussian process with squared-exponential kernel, standard deviation amp(grid) (array) and correlation length `length`, on `grid`."""
    g = np.asarray(grid, float)
    k = np.exp(-0.5 * ((g[:, None] - g[None, :]) / length) ** 2)
    w, v = np.linalg.eigh(k + 1e-9 * np.eye(len(g)))
    root = v * np.sqrt(np.clip(w, 0, None))
    return (rng.standard_normal((n, len(g))) @ root.T) * np.asarray(amp, float)[None, :]


def quad_features(X, degree=2):
    """Polynomial features of the rows of X up to `degree` (1, x_j, x_j x_k, and cubes when degree 3)."""
    X = np.atleast_2d(np.asarray(X, float))
    n, d = X.shape
    cols = [np.ones(n)]
    cols += [X[:, j] for j in range(d)]
    for j in range(d):
        for k in range(j, d):
            cols.append(X[:, j] * X[:, k])
    if degree >= 3:
        for j in range(d):
            for k in range(j, d):
                for m in range(k, d):
                    cols.append(X[:, j] * X[:, k] * X[:, m])
    return np.column_stack(cols)


class Emulator:
    """Weighted ridge regression of Y (n x nz, NaN allowed per column) on polynomial features of X, one solve per column, weights from `weights` (n,) or uniform."""

    def __init__(self, degree=2, ridge=1e-3):
        self.degree, self.ridge = degree, ridge
        self.coef = None

    def fit(self, X, Y, weights=None):
        F = quad_features(X, self.degree)
        n, p = F.shape
        w = np.ones(n) if weights is None else np.asarray(weights, float)
        Y = np.asarray(Y, float)
        self.coef = np.full((p, Y.shape[1]), np.nan)
        for j in range(Y.shape[1]):
            ok = np.isfinite(Y[:, j]) & (w > 0)
            if ok.sum() < 2 * p:
                continue
            Fw = F[ok] * w[ok, None]
            A = F[ok].T @ Fw
            pen = np.diag(np.full(p, self.ridge * float(np.mean(np.diag(A)[1:]))))  # ridge as a fraction of the mean diagonal of F'WF (intercept excluded), as the protocol states
            pen[0, 0] = 0.0
            self.coef[:, j] = np.linalg.solve(A + pen, Fw.T @ Y[ok, j])
        return self

    def predict(self, X):
        return quad_features(X, self.degree) @ self.coef

    def gradient_matrices(self, d):
        """Indices that map the coefficient vector to the gradient: used by the reachability search."""
        return None
