(function (g) {
  const VARIANT = /variation|low[- ]?res|double|single|per galaxy|hybrid|noAGN|full SUBFIND|2 R_half|rTNG|secondary|individual|Recal-/i;
  const FIDUCIAL = { "FLAMINGO": /^L1_m9(?! variation)/, "Magneticum Pathfinder": /^Box2\/hr/, "Illustris": /^Illustris-1$/, "SPHINX20": /100-myr|uv-1500A/, "SIMBA": /^m100n1024 \+ hires \(combined\), V_flat/, "COLIBRE": /Ludlow\+26\), centrals, star-forming/ };
  const TIER_RANK = { "catalog-derived": 0, "official-table": 0, "published-table": 1, "published-fit": 2, "digitized-figure": 3 };
  const unitOf = r => `${r.source}|${r.run || ""}`;
  const tol = z => Math.max(.15, .1 * (1 + z));

  function primaryUnits(records) {
    const by = new Map();
    for (const r of records) {
      const u = unitOf(r), b = by.get(r.source) || by.set(r.source, new Map()).get(r.source), e = b.get(u) || b.set(u, { u, run: r.run || "", z: new Set(), tier: 9 }).get(u);
      e.z.add(r.epoch.zRepresentative);
      e.tier = Math.min(e.tier, TIER_RANK[r.provenance?.tier] ?? 9);
    }
    const out = new Set();
    for (const [src, b] of by) {
      const f = FIDUCIAL[src];
      const best = [...b.values()].sort((a, c) => (f && f.test(a.run) ? 0 : 1) - (f && f.test(c.run) ? 0 : 1) || VARIANT.test(a.run) - VARIANT.test(c.run) || c.z.size - a.z.size || a.tier - c.tier || a.run.localeCompare(c.run))[0];
      out.add(best.u);
    }
    return out;
  }

  const nearest = (stops, z) => stops.length ? stops.reduce((b, v) => Math.abs(v - z) < Math.abs(b - z) ? v : b, stops[0]) : 0;

  function medianOffset(A, S, interpolate) {
    if (A.length < 3 || S.length < 3) return null;
    const lo = S[0].x, hi = S[S.length - 1].x, d = [];
    for (const p of A) {
      if (p.x < lo || p.x > hi) continue;
      const y = interpolate(S, p.x);
      if (Number.isFinite(y)) d.push(y - p.y);
    }
    if (d.length < 3) return null;
    d.sort((u, v) => u - v);
    return d[Math.floor((d.length - 1) / 2)];
  }

  function parseUserCurve(text, { linear = false } = {}) {
    const rows = String(text || "").split(/\r?\n/).map(l => l.trim()).filter(l => l && !l.startsWith("#"));
    const cells = l => l.split(/[,;\t ]+/).filter(Boolean);
    let head = null;
    if (rows.length && !Number.isFinite(Number(cells(rows[0])[0]))) head = cells(rows.shift()).map(h => h.toLowerCase().replace(/[^a-z]/g, ""));
    const col = (names, def) => { const i = head ? head.findIndex(h => names.includes(h)) : -1; return i >= 0 ? i : def; };
    const ix = col(["x", "logm", "mass"], 0), iy = col(["y", "logphi", "phi", "value"], 1);
    const ilo = col(["ylow", "lo", "low", "ymin"], -1), ihi = col(["yhigh", "hi", "high", "ymax"], -1), ierr = col(["err", "sigma", "yerr", "error"], -1);
    const pts = []; let skipped = 0;
    for (const l of rows) {
      const c = cells(l).map(Number);
      let x = c[ix], y = c[iy], lo = ilo >= 0 ? c[ilo] : NaN, hi = ihi >= 0 ? c[ihi] : NaN;
      const err = ierr >= 0 ? c[ierr] : head ? NaN : c.length === 3 ? c[2] : NaN;
      if (!head && c.length >= 4) { lo = c[2]; hi = c[3]; }
      if (!Number.isFinite(x) || !Number.isFinite(y)) { skipped++; continue; }
      if (!Number.isFinite(lo) && !Number.isFinite(hi) && Number.isFinite(err)) { lo = y - err; hi = y + err; }
      if (linear) {
        if (x <= 0 || y <= 0) { skipped++; continue; }
        x = Math.log10(x); const L = v => v > 0 ? Math.log10(v) : NaN; y = Math.log10(y); lo = L(lo); hi = L(hi);
      }
      pts.push({ x, y, lo: Number.isFinite(lo) ? lo : undefined, hi: Number.isFinite(hi) ? hi : undefined });
    }
    pts.sort((a, b) => a.x - b.x);
    return { pts, skipped, header: head };
  }

  function spread(curves, { step = .1, minSuites = 3, maxGap = .6 } = {}) {
    const cs = curves.filter(c => c.length >= 2);
    if (cs.length < minSuites) return null;
    const at = (c, x) => { for (let i = 1; i < c.length; i++) { const a = c[i - 1], b = c[i]; if (x >= a.x && x <= b.x) return b.x - a.x > maxGap ? NaN : b.x === a.x ? a.y : a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x); } return NaN; };
    const lo = Math.min(...cs.map(c => c[0].x)), hi = Math.max(...cs.map(c => c[c.length - 1].x)), sd = [];
    for (let x = lo; x <= hi + 1e-9; x += step) {
      const ys = cs.map(c => at(c, x)).filter(Number.isFinite);
      if (ys.length < minSuites) continue;
      const m = ys.reduce((a, b) => a + b, 0) / ys.length;
      sd.push(Math.sqrt(ys.reduce((a, y) => a + (y - m) * (y - m), 0) / (ys.length - 1)));
    }
    if (sd.length < 3) return null;
    sd.sort((a, b) => a - b);
    return { sigma: sd.length % 2 ? sd[(sd.length - 1) / 2] : (sd[sd.length / 2 - 1] + sd[sd.length / 2]) / 2, grid: sd.length, suites: cs.length };
  }

  const pickAnchor = (cands, re, z) => cands.filter(r => re.test(r.source)).sort((p, q) => Math.abs(p.epoch.zRepresentative - z) - Math.abs(q.epoch.zRepresentative - z))[0] || null;

  g.SimHighlineLogic = { VARIANT, FIDUCIAL, TIER_RANK, unitOf, tol, primaryUnits, nearest, medianOffset, pickAnchor, parseUserCurve, spread };
})(typeof window !== "undefined" ? window : globalThis);
