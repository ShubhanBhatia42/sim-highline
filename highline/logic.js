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

  /* Reads a pasted or loaded curve. Understands comma, semicolon, tab and space separated rows; decimal commas when the separator is a semicolon; a byte-order mark and Windows line endings; comment lines (#); a header row; a units row;
     missing values. Values are log10 by default. linear = the y values are linear (and x too if it is plainly a linear mass, i.e. larger than 1000); linearX / linearY set either side explicitly. */
  function parseUserCurve(text, { linear = false, linearX, linearY } = {}) {
    const lines = String(text || "").replace(/^﻿/, "").split(/\r?\n|\r/).map((l, i) => ({ l: l.trim(), n: i + 1 })).filter(o => o.l && !o.l.startsWith("#"));
    const cells = l => (l.includes(";") ? l.split(";").map(c => c.trim().replace(",", ".")) : l.split(/[,\t ]+/)).filter(c => c !== "");
    let head = null;
    if (lines.length && !Number.isFinite(Number(cells(lines[0].l)[0]))) head = cells(lines.shift().l).map(h => h.toLowerCase().replace(/[^a-z]/g, ""));
    const col = (names, def) => { const i = head ? head.findIndex(h => names.includes(h)) : -1; return i >= 0 ? i : def; };
    const ix = col(["x", "logm", "mass", "mstar", "logmstar", "z", "redshift"], 0), iy = col(["y", "logphi", "phi", "value", "sfr", "ssfr", "logsfr"], 1);
    const ilo = col(["ylow", "lo", "low", "ymin"], -1), ihi = col(["yhigh", "hi", "high", "ymax"], -1), ierr = col(["err", "sigma", "yerr", "error", "dy"], -1);
    const rows = []; const bad = [];
    for (const o of lines) {
      const c = cells(o.l).map(v => (v === "" ? NaN : Number(v)));
      const x = c[ix], y = c[iy];
      if (!Number.isFinite(x) || !Number.isFinite(y)) { bad.push({ line: o.n, text: o.l.slice(0, 40), reason: /^[(\[]/.test(o.l) ? "units row" : "not numbers" }); continue; }
      let lo = ilo >= 0 ? c[ilo] : NaN, hi = ihi >= 0 ? c[ihi] : NaN;
      const err = ierr >= 0 ? c[ierr] : head ? NaN : c.length === 3 ? c[2] : NaN;
      if (!head && c.length >= 4) { lo = c[2]; hi = c[3]; }
      if (!Number.isFinite(lo) && !Number.isFinite(hi) && Number.isFinite(err)) { lo = y - err; hi = y + err; }
      rows.push({ x, y, lo, hi, line: o.n });
    }
    const ly = linearY ?? linear, lx = linearX ?? (linear && rows.length > 0 && Math.max(...rows.map(r => r.x)) > 1000);
    const pts = []; let skipped = bad.length;
    for (const r of rows) {
      let { x, y, lo, hi } = r;
      if (ly) { if (y <= 0) { skipped++; bad.push({ line: r.line, text: `${r.x}, ${r.y}`, reason: "not positive, so not a linear value" }); continue; } const L = v => (v > 0 ? Math.log10(v) : NaN); y = Math.log10(y); lo = L(lo); hi = L(hi); }
      if (lx) { if (x <= 0) { skipped++; bad.push({ line: r.line, text: `${r.x}, ${r.y}`, reason: "x not positive" }); continue; } x = Math.log10(x); }
      pts.push({ x, y, lo: Number.isFinite(lo) ? lo : undefined, hi: Number.isFinite(hi) ? hi : undefined });
    }
    pts.sort((a, b) => a.x - b.x);
    return { pts, skipped, header: head, bad, xLinear: lx, yLinear: ly };
  }

  /* What was understood, and what looks wrong. expect = the range of the published curves at this epoch ({xlo, xhi, ylo, yhi}) when known. */
  function inspectUserCurve(text, opts = {}, expect = null) {
    const r = parseUserCurve(text, opts), pts = r.pts, w = [], f = v => (Math.abs(v) >= 1000 || (Math.abs(v) < 0.01 && v !== 0) ? v.toExponential(1) : (+v.toFixed(2)).toString());
    if (!pts.length) { const lin = r.bad.filter(b => /not positive/.test(b.reason)).length >= 2; return { points: 0, skipped: r.bad, header: r.header, warnings: [lin ? "No y value is positive, so they look like logarithms already: untick \"values are linear, not log10\"." : "No numeric x,y rows were found."], summary: lin ? "No rows could be read as linear values (none is positive)." : "No numeric rows found. Paste x,y per line (optional third column: 1σ error).", ...r }; }
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y), xlo = xs[0], xhi = xs[xs.length - 1], ylo = Math.min(...ys), yhi = Math.max(...ys);
    const raw = String(text || "").replace(/^﻿/, "");
    const rawY = [];
    { const lines = raw.split(/\r?\n|\r/).map(l => l.trim()).filter(l => l && !l.startsWith("#")); if (lines.length && !Number.isFinite(Number(lines[0].split(/[,;\t ]+/)[0]))) lines.shift(); for (const l of lines) { const c = (l.includes(";") ? l.split(";").map(v => v.trim().replace(",", ".")) : l.split(/[,\t ]+/)).filter(v => v !== "").map(Number); if (Number.isFinite(c[1])) rawY.push(c[1]); } }
    if (!opts.linear && !opts.linearY && rawY.length >= 3 && rawY.every(v => v > 0) && Math.max(...rawY) / Math.min(...rawY) >= 10) w.push("The y values are all positive and span several orders of magnitude, so they look linear: tick \"values are linear, not log10\".");
    if ((opts.linear || opts.linearY) && r.bad.filter(b => /not positive/.test(b.reason)).length >= Math.max(2, rawY.length / 2)) w.push("Most y values are not positive, so they look like logarithms already: untick \"values are linear, not log10\".");
    if (pts.length < 3) w.push("At least three points are needed before an offset can be computed.");
    if (new Set(xs).size < xs.length) w.push("Some x values are repeated; the curve is read in the order of x.");
    if (expect && Number.isFinite(expect.xlo)) {
      if (xhi < expect.xlo || xlo > expect.xhi) w.push(`Your x range (${f(xlo)} to ${f(xhi)}) does not overlap the published curves at this epoch (${f(expect.xlo)} to ${f(expect.xhi)}): check the units or the relation.`);
      else if (Number.isFinite(expect.ylo)) { const m = ys.slice().sort((a, b) => a - b)[Math.floor(ys.length / 2)]; if (m < expect.ylo - 3 || m > expect.yhi + 3) w.push(`Your median y (${f(m)}) is far outside the published curves (${f(expect.ylo)} to ${f(expect.yhi)}): check the units or whether the values are logarithms.`); }
    }
    const parts = [`${pts.length} points read, x from ${f(xlo)} to ${f(xhi)}, y from ${f(ylo)} to ${f(yhi)}`];
    if (r.header) parts.push(`header "${r.header.join(", ")}"`);
    if (pts.some(p => Number.isFinite(p.lo))) parts.push("error column used");
    if (r.yLinear) parts.push("linear values converted to log10");
    if (r.bad.length) parts.push(`${r.bad.length} row${r.bad.length > 1 ? "s" : ""} skipped (${r.bad.slice(0, 3).map(b => `line ${b.line}: ${b.reason}`).join("; ")}${r.bad.length > 3 ? "; …" : ""})`);
    return { points: pts.length, skipped: r.bad, header: r.header, warnings: w, summary: parts.join("; ") + ".", ...r };
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

  g.SimHighlineLogic = { VARIANT, FIDUCIAL, TIER_RANK, unitOf, tol, primaryUnits, nearest, medianOffset, pickAnchor, parseUserCurve, inspectUserCurve, spread };
})(typeof window !== "undefined" ? window : globalThis);
