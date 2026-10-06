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

  const pickAnchor = (cands, re, z) => cands.filter(r => re.test(r.source)).sort((p, q) => Math.abs(p.epoch.zRepresentative - z) - Math.abs(q.epoch.zRepresentative - z))[0] || null;

  g.SimHighlineLogic = { VARIANT, FIDUCIAL, TIER_RANK, unitOf, tol, primaryUnits, nearest, medianOffset, pickAnchor };
})(typeof window !== "undefined" ? window : globalThis);
