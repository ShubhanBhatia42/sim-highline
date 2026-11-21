// The "answer" pages of the site (site/answer-*.html and answers.html), generated from the curve records and data/answers.json.
// Nothing on a page is typed that the data could change: the number of simulations at an epoch, which of them can be compared with the observation, why not, and how far each lies from it are computed here
// with the Explorer's own rules (highline/logic.js: fiducial run per simulation, anchor observation, median offset over the overlap; compare.js: the verdicts), so a page agrees with the Explorer's Tension view cell for cell
// (scripts/test-answers.mjs checks that in the browser). Returns { pages: { file: template }, index: template, cards: [...] }; the templates carry the {{head}}, {{header}} and {{footer}} placeholders of the site build.
import vm from "node:vm";

const TIER = { "official-table": "official table", "catalog-derived": "public catalogue", "published-table": "paper table", "published-fit": "published fit", "digitized-figure": "read from a figure" };
const sgn = v => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)}`;
const median = a => { const s = [...a].sort((x, y) => x - y), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
const ZFMT = z => String(z);

export function answerPages({ recs, spec, compareSrc, logicSrc, colorFor, ticks, esc, release, repo }) {
  const load = src => { const c = { globalThis: {} }; vm.runInNewContext(src, c); return c.globalThis; };
  const C = load(compareSrc).SimHighlineCompare, L = load(logicSrc).SimHighlineLogic;
  // the Explorer files each record under a relation of its own (the mass-metallicity records split by what the metallicity is), and every rule runs on that key; the same mapping here (highline/index.html: relKey)
  const relKey = r => { if (r.relation !== "mzr") return r.relation; const q = r.definitions?.metallicityQuantity; if (q === "gas-O/H") return "mzr"; return /Zsun/.test(r.axes?.yDefinition || "") ? "mzrz" : "mzrraw"; };
  recs = recs.filter(r => r.representation).map(r => ({ ...r, rel0: r.relation, relation: relKey(r) }));
  const sims = recs.filter(r => r.kind !== "observation"), obs = recs.filter(r => r.kind === "observation");
  const isScatter = r => r.representation.type === "points" && r.representation.connect === false;
  const evalCache = new Map();
  // the points of a record at an epoch, as the Explorer reads them (a parametric curve is evaluated at the epoch)
  const pts = (r, z) => {
    const rep = r.representation;
    if (rep.type === "points") return rep.points.filter(p => Number.isFinite(p.x) && Number.isFinite(p.y)).map(p => ({ x: p.x, y: p.y })).sort((a, b) => a.x - b.x);
    if (!evalCache.has(r.id)) { try { evalCache.set(r.id, C.evaluator(r)); } catch (e) { evalCache.set(r.id, null); } }
    const f = evalCache.get(r.id); if (!f) return [];
    const out = []; for (let i = 0; i <= 40; i++) { const x = r.domain.xMin + (r.domain.xMax - r.domain.xMin) * i / 40, y = f(x, z); if (Number.isFinite(y)) out.push({ x, y }); } return out;
  };
  const pickSims = (rel, z) => {
    const best = new Map();
    for (const r of sims) {
      if (r.relation !== rel) continue;
      const an = r.epoch.mode === "analytic-evolution", d = an ? (z >= r.epoch.zMin && z <= r.epoch.zMax ? 0 : Infinity) : Math.abs(r.epoch.zRepresentative - z);
      if (d > L.tol(z)) continue;
      const k = L.unitOf(r); if (!best.has(k) || d < best.get(k).d) best.set(k, { r, d });
    }
    return [...best.values()].map(v => v.r);
  };
  const pickObs = (rel, z) => obs.filter(r => r.relation === rel && (r.epoch.mode === "analytic-evolution" ? z <= r.epoch.zMax : (z >= r.epoch.zMin - .1 && z <= r.epoch.zMax + .1) || Math.abs(r.epoch.zRepresentative - z) <= L.tol(z)));
  const primary = new Map();
  const units = rel => { if (!primary.has(rel)) primary.set(rel, L.primaryUnits(sims.filter(r => r.relation === rel))); return primary.get(rel); };
  const at = (P, x) => { if (!P.length || x < P[0].x || x > P[P.length - 1].x) return null; const v = C.interpolate(P, x); return Number.isFinite(v) ? v : null; };

  const lc = t => (/^[A-Z][a-z]/.test(t) ? t[0].toLowerCase() + t.slice(1) : t), label = k => C.KEY_LABEL[k] || k;
  // a blocker or caveat from compare.js in plain words
  const reason = (s, r) => {
    let m;
    if ((m = /^(\w+) not documented/.exec(s))) return `${lc(label(m[1]))} not stated`;
    if ((m = /^(\w+): .+ vs .+/.exec(s)) && m[1] in C.KEY_LABEL) return `${lc(label(m[1]))} differs`;
    if (/^structured definitions missing/.test(s)) return "definitions missing";
    if (/not rankable|context only|digitized|warning/i.test(s) || !r.rankable) return `not rankable, ${TIER[r.provenance.tier] || r.provenance.tier}`;
    return s.length > 60 ? s.slice(0, 57) + "…" : s;
  };

  function epoch(a, z) {
    const rx = new RegExp(a.anchors ? a.anchors[ZFMT(z)] : a.anchor), O = pickObs(a.relation, z), anchor = L.pickAnchor(O, rx, z), prim = units(a.relation);
    if (!anchor) throw new Error(`answers: no anchor observation for ${a.relation} at z = ${z}`);
    const A = pts(anchor, z), rows = [];
    for (const r of pickSims(a.relation, z)) {
      if (!prim.has(L.unitOf(r))) continue;
      const P = pts(r, z), offset = isScatter(r) ? null : L.medianOffset(A, P, C.interpolate), v = C.compatible(anchor, r);
      const overlap = P.length ? A.filter(p => p.x >= P[0].x && p.x <= P[P.length - 1].x).length : 0;
      rows.push({ r, P, offset, verdict: v.verdict, blockers: v.blockers, caveats: v.caveats, reasons: [...new Set(v.blockers.map(s => reason(s, r)))], notes: [...new Set(v.caveats.map(s => reason(s, r)))], overlap, yRef: at(P, a.refX), scatterOnly: isScatter(r) });
    }
    rows.sort((p, q) => (p.verdict === "not-comparable") - (q.verdict === "not-comparable") || p.r.source.localeCompare(q.r.source) || (p.r.run || "").localeCompare(q.r.run || ""));
    const others = O.filter(r => r !== anchor && !isScatter(r) && r.source !== anchor.source);
    return { z, anchor, A, rows, others, obsSources: [...new Set(O.map(r => r.source))], yAnchorRef: at(A, a.refX) };
  }

  // the simulations that share the relation's decisive definitions, compared with each other (the Explorer's Disagreement view, cell for cell)
  function agree(a, E) {
    const hard = (C.RULES[a.relation] || { hard: [] }).hard, UNSET = [undefined, null, "unspecified", "heterogeneous"], by = new Map();
    for (const x of E.rows) { if (x.scatterOnly) continue; const c = by.get(x.r.source); if (!c || Math.abs(x.r.epoch.zRepresentative - E.z) < Math.abs(c.r.epoch.zRepresentative - E.z)) by.set(x.r.source, x); }
    let rs = [...by.values()].filter(x => hard.every(h => !UNSET.includes(x.r.definitions?.[h])));
    const key = x => [x.r.axes.xUnit, x.r.axes.yUnit, ...hard.map(h => JSON.stringify(x.r.definitions[h]))].join("|"), cnt = new Map();
    for (const x of rs) cnt.set(key(x), (cnt.get(key(x)) || 0) + 1);
    const top = [...cnt].sort((p, q) => q[1] - p[1])[0]; if (!top) return null;
    rs = rs.filter(x => key(x) === top[0]);
    const sp = L.spread(rs.map(x => x.P.filter(p => Number.isFinite(p.y)))); if (!sp) return null;
    return { ...sp, names: rs.map(x => x.r.source), fromFigure: rs.filter(x => x.r.provenance.tier === "digitized-figure").length, basis: hard.map(h => `${label(h)}: ${rs[0].r.definitions[h]}`) };
  }
  const agreeText = (a, g) => g ? `Among the ${g.suites} simulations that share the decisive definitions (${g.basis.map(esc).join("; ")}), the curves differ from one another by ${g.sigma.toFixed(2)} ${a.unit} (the standard deviation between them, median over the range they share): ${g.names.map(esc).join(", ")}.${g.fromFigure ? ` ${g.fromFigure === g.suites ? (g.suites === 1 ? "This curve is" : "All of these curves are") : g.fromFigure === 1 ? "1 of these curves is" : `${g.fromFigure} of these curves are`} read from ${g.fromFigure === 1 ? "a published figure" : "published figures"}, so the spread includes the error of reading ${g.fromFigure === 1 ? "it" : "them"}.` : ""}` : "";

  // one paragraph per epoch, built from the counts: compared (comparable, with an offset), not comparable (a rule says so), no usable overlap (comparable in principle, but no curve over at least three points of the anchor)
  function sentence(a, E) {
    const n = E.rows.length, ok = E.rows.filter(r => r.offset != null && r.verdict !== "not-comparable"), no = E.rows.filter(r => r.verdict === "not-comparable"), none = E.rows.filter(r => r.verdict !== "not-comparable" && r.offset == null);
    const cnt = new Map(); for (const r of no) for (const x of r.reasons) cnt.set(x, (cnt.get(x) || 0) + 1);
    const top = [...cnt].sort((p, q) => q[1] - p[1] || p[0].localeCompare(q[0])).slice(0, 3).map(([x, c]) => `${x}: ${c}`);
    const why = top.length ? `, for these reasons (a curve can have more than one), with the number of curves: ${top.join("; ")}` : "";
    const parts = [`At z ≈ ${E.z}, ${n} simulations have a ${esc(a.noun)} in the dataset. The anchor observation is ${esc(E.anchor.source)}.`];
    if (ok.length >= 3) { const d = ok.map(r => r.offset); parts.push(`${ok.length} of them can be compared with it, with the caveats in the table; they lie between ${sgn(Math.min(...d))} and ${sgn(Math.max(...d))} ${a.unit} from it (median ${sgn(median(d))}).`); }
    else if (ok.length) parts.push(`Only ${ok.length} can be compared with it (${ok.map(r => `${esc(r.r.source)}, ${sgn(r.offset)} ${a.unit}`).join("; ")}).`);
    if (no.length === n) parts.push(`None of the ${n} can be compared with it${why}. The offsets in the table are shown in grey for orientation only; they are not verdicts on the simulations.`);
    else if (no.length) parts.push(`${no.length} cannot be compared${why}; ${no.length === 1 ? "its offset is" : "their offsets are"} shown in grey for orientation and ${no.length === 1 ? "is not a verdict" : "are not verdicts"}.`);
    if (none.length) parts.push(`${none.length} ${none.length === 1 ? "has" : "have"} no curve that overlaps the anchor over at least three of its points (${none.map(r => esc(r.r.source)).join(", ")}; ${none.some(r => r.scatterOnly) ? "individual galaxies, not a curve, or " : ""}too little overlap).`);
    return { text: parts.join(" "), n, k: ok.length, clean: ok.filter(r => r.verdict === "comparable").length, noOffset: n - E.rows.filter(r => r.offset != null).length };
  }

  function figure(a, E, ids, size) {
    const { W = 760, H = 380, L0 = 62, R = 18, T = 14, B = 50 } = size || {};
    const lines = E.rows.filter(r => r.P.length > 1 && !r.scatterOnly), all = [...lines.flatMap(r => r.P), ...E.A];
    const xs = all.map(p => p.x), x0 = Math.floor(Math.min(...xs) * 2) / 2, x1 = Math.ceil(Math.max(...xs) * 2) / 2;
    const ys = all.filter(p => p.x >= x0 && p.x <= x1).map(p => p.y).sort((p, q) => p - q), y0 = Math.floor(ys[Math.floor(.01 * ys.length)]), y1 = Math.ceil(ys[Math.min(ys.length - 1, Math.floor(.995 * ys.length))]);
    const sx = x => L0 + (x - x0) / (x1 - x0) * (W - L0 - R), sy = y => H - B - (y - y0) / (y1 - y0) * (H - T - B), P = p => "M" + p.map(q => `${sx(q.x).toFixed(1)},${sy(q.y).toFixed(1)}`).join("L");
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`${a.yName} against ${a.xName} at z ≈ ${E.z}: ${E.rows.length} simulations and the anchor observation ${E.anchor.source}`)}"><g class="axis">`;
    for (const t of ticks(x0, x1)) s += `<line x1="${sx(t)}" x2="${sx(t)}" y1="${T}" y2="${H - B}" opacity=".5"/><text x="${sx(t)}" y="${H - B + 18}" text-anchor="middle">${t}</text>`;
    for (const t of ticks(y0, y1)) s += `<line x1="${L0}" x2="${W - R}" y1="${sy(t)}" y2="${sy(t)}" opacity=".5"/><text x="${L0 - 8}" y="${sy(t) + 4}" text-anchor="end">${t}</text>`;
    s += `</g><text class="al" x="${(L0 + W - R) / 2}" y="${H - 10}" text-anchor="middle">${esc(a.xlab)}</text><text class="al" transform="translate(16 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle">${esc(a.ylab)}</text><defs><clipPath id="${ids}"><rect x="${L0}" y="${T}" width="${W - L0 - R}" height="${H - T - B}"/></clipPath></defs><g clip-path="url(#${ids})" fill="none">`;
    for (const r of E.others) { const q = pts(r, E.z); if (q.length > 1) s += `<path d="${P(q)}" stroke="var(--cream3)" stroke-width="1.2" stroke-dasharray="3 4"/>`; }
    for (const r of lines.filter(r => r.verdict === "not-comparable")) s += `<path d="${P(r.P)}" stroke="${colorFor(r.r.source)}" stroke-width="1.4" stroke-dasharray="2 3" opacity=".6"/>`;
    for (const r of lines.filter(r => r.verdict !== "not-comparable")) s += `<path d="${P(r.P)}" stroke="${colorFor(r.r.source)}" stroke-width="2.4"/>`;
    s += `<path d="${P(E.A)}" stroke="var(--ink)" stroke-width="3"/></g></svg>`;
    const key = [...new Set(lines.map(r => r.r.source))].map(src => `<span><i style="background:${colorFor(src)}"></i>${esc(src)}</span>`).join("") + `<span><i style="background:var(--ink)"></i>${esc(E.anchor.source)} (anchor)</span>`;
    return { svg: s, key };
  }

  function table(a, E, id) {
    const head = `<thead><tr><th scope="col">Simulation</th><th scope="col">How the curve was obtained</th><th scope="col">Compared with the anchor</th><th scope="col">Offset (${a.unit})</th><th scope="col">At ${esc(a.refXLabel)}</th></tr></thead>`;
    const body = E.rows.map(r => {
      const no = r.verdict === "not-comparable", word = r.verdict === "comparable" ? "comparable" : no ? "not comparable" : "comparable with caveats", mark = r.verdict === "comparable" ? "✓" : no ? "✕" : "~";
      const why = no ? r.reasons : r.notes;
      const off = r.offset == null ? `<span class="dim">${r.scatterOnly ? "individual galaxies, no curve" : r.overlap < 3 ? "too little overlap" : "no offset"}</span>` : `<span${no ? ' class="dim"' : ""}>${sgn(r.offset)}</span>${no ? '<span class="sr"> (for orientation only)</span>' : ""}`;
      const ref = r.yRef == null ? `<span class="dim">outside range</span>` : `<span${no ? ' class="dim"' : ""}>${r.yRef.toFixed(2)}</span>`;
      return `<tr><th scope="row"><span class="sw" style="display:inline-block;vertical-align:middle;margin-right:6px;width:.7rem;height:.7rem;background:${colorFor(r.r.source)}"></span>${esc(r.r.source)}<br><span class="dim">${esc(String(r.r.run || "").length > 56 ? String(r.r.run).slice(0, 55) + "…" : r.r.run || "")}</span></th><td data-l="How obtained">${esc(TIER[r.r.provenance.tier] || r.r.provenance.tier)}</td><td data-l="Compared with the anchor"><span aria-hidden="true">${mark}</span> ${word}${why.length ? `<br><span class="dim">${esc(why.join("; "))}</span>` : ""}</td><td data-l="Offset (${a.unit})">${off}</td><td data-l="At ${esc(a.refXLabel)}">${ref}</td></tr>`;
    }).join("");
    return `<div class="tw" role="region" aria-label="Simulations at z ≈ ${E.z}, compared with ${esc(E.anchor.source)}" tabindex="0"><table class="stack" id="${id}"><caption class="sr">Each simulation's fiducial run at z ≈ ${E.z}</caption>${head}<tbody>${body}</tbody></table></div>`;
  }

  const link = r => { const p = r.provenance, h = p.doi ? `https://doi.org/${p.doi}` : p.url; return h ? `<a href="${esc(h)}" target="_blank" rel="noopener">${esc(r.source)}</a>` : esc(r.source); };
  const cards = [], pages = {};
  for (const a of spec.answers) {
    const Es = a.epochs.map(z => epoch(a, z)), S = Es.map(E => sentence(a, E)), G = Es.map(E => agree(a, E));
    const CV = Es.map(E => L.plotCaveats([E.anchor, ...E.rows.filter(r => !r.scatterOnly && r.P.length > 1).map(r => r.r)], C, { name: r => r.source }));
    const line = `Comparable with caveats at ${Es.map((E, i) => `z ≈ ${E.z}: ${S[i].k} of ${S[i].n}`).join("; ")}`;
    const K = S.reduce((t, s) => t + s.k, 0), N = S.reduce((t, s) => t + s.n, 0), Cn = S.reduce((t, s) => t + s.clean, 0);
    const summary = K === 0 ? `None of the ${N} simulation curves across the ${Es.length} epochs can be compared with the anchor observation under the site's comparison rules. The reasons are given for each epoch, and the offsets are shown for orientation only.` : `${K} of ${N} simulation curves across the ${Es.length} epochs can be compared with the anchor observation${Cn === 0 ? ", all of them with caveats" : `, ${Cn} of them without caveats`}; the rest differ in a definition the comparison rules treat as decisive or are not rankable.`;
    cards.push({ id: a.id, page: a.page, question: a.question, short: a.short, line, k: S.map(s => s.k), n: S.map(s => s.n) });
    const sections = Es.map((E, i) => {
      const f = figure(a, E, `c${i}w`), g = figure(a, E, `c${i}n`, { W: 360, H: 400, L0: 50, R: 10, T: 12, B: 48 }), h = `e${i}`;
      return `<section class="sec" id="${h}" aria-labelledby="${h}-h">
<h2 id="${h}-h"><span class="sn" aria-hidden="true">§${i + 1}</span>z ≈ ${E.z}</h2>
<p>${S[i].text}</p>
${G[i] ? `<p>${agreeText(a, G[i])}</p>\n` : ""}<figure class="fig dual"><div class="chart chart-wide">${f.svg}</div><div class="chart chart-narrow">${g.svg}</div><div class="key">${f.key}</div>
<figcaption><span class="fl">Fig. ${i + 1}</span><span>${esc(a.short.split(",")[0])} at z ≈ ${E.z}: solid lines are simulations that can be compared with the anchor, dotted grey lines are the ones that cannot, the thick line is the anchor, and the faint dashed lines are other observations. <a href="../highline.html#r=${a.relation}&amp;z=${E.z}">Open z ≈ ${E.z} in the Explorer</a>.</span></figcaption></figure>
${CV[i].short.length ? `<p class="dim" style="font-size:15px"><b>Which of these curves may be read against each other.</b> ${CV[i].short.map(esc).join(" ")}</p>\n` : ""}${table(a, E, `t${i}`)}
<p class="dim" style="font-size:15px">The observations at this epoch are ${[...new Map(pickObs(a.relation, E.z).filter(r => !isScatter(r)).map(r => [r.source, r])).values()].map(link).join(", ")}.</p>
</section>`;
    }).join("\n");
    const toc = Es.map((E, i) => `<li><a href="#e${i}"><span aria-hidden="true">§${i + 1}</span>z ≈ ${E.z}</a></li>`).join("") + `<li><a href="#how"><span aria-hidden="true">§${Es.length + 1}</span>How to read it</a></li>`;
    const desc = `${a.question} ${a.short}: counts and offsets computed from the dataset with its comparison rules.`;
    pages[a.page] = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(a.short)}: an answer from the data · sim-highline</title>
<meta name="description" content="${esc(desc)}">
{{head}}
</head>
<body>
{{header}}
<main id="main" class="wrap page" tabindex="-1">
<div class="doc">
<nav class="idx nophone" aria-label="On this page"><p class="lab">Contents</p><ol>${toc}</ol></nav>
<div class="c">
<div class="title">
<p class="lab kicker">Answer · ${esc(a.short)}</p>
<h1>${esc(a.question)}</h1>
<p class="standfirst">This page looks at ${a.describes}. ${summary}</p>
<p class="btns"><a class="btn main" href="../highline.html#r=${a.relation}&amp;z=${Es[Es.length > 1 ? 1 : 0].z}">Open it in the Explorer</a><a class="btn" href="answers.html">All answers</a></p>
</div>
${sections}
<section class="sec" id="how" aria-labelledby="how-h">
<h2 id="how-h"><span class="sn" aria-hidden="true">§${Es.length + 1}</span>How to read it</h2>
<ul class="flat">
<li><b>Fiducial run.</b> Each simulation is shown by one run: the default configuration of its main paper, not the variations. The dataset holds more runs; the Explorer lists them.</li>
<li><b>Anchor.</b> The observation the simulations are measured against. It is the Explorer's anchor for this relation${a.anchors ? ", chosen here by redshift" : ""}; the others at the same epoch are listed under each figure.</li>
<li><b>Offset.</b> The median difference between a simulation's curve and the anchor over the range where both are defined (at least three points of the anchor), simulation minus anchor, in ${a.unit} (factors of ten). Positive means above the anchor.</li>
<li><b>Compared with the anchor.</b> ✓ the definitions the comparison rules look at agree; ~ they agree on the decisive ones and differ on others, which the table names; ✕ a rule says the definitions differ on a decisive point, or the curve is not rankable (read from a figure, or marked context only). An offset next to ✕ is not a verdict on the simulation.</li>
</ul>
<h3>What this page does not tell you</h3>
<ul class="flat">
<li>It does not rank simulations. A small offset is not accuracy: simulations calibrated to the same observations agree by construction.</li>
${a.limits.map(t => `<li>${esc(t)}</li>`).join("\n")}
<li>No outside expert has reviewed this page or the records behind it; the counts and offsets are computed from the records, and the records are checked by scripts and by the maintainer. <a href="quality.html">How much to trust the data</a>.</li>
</ul>
<p class="dim" style="font-size:15px">Numbers are computed by <code>scripts/site-answers.mjs</code> from <code>data/curves/</code> and <code>data/answers.json</code>, with the rules the Explorer uses. Dataset v${release.version}.</p>
</section>
</div>
</div>
</main>
{{footer}}
</body>
</html>
`;
  }
  const indexHtml = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Answers: three questions answered from the data · sim-highline</title>
<meta name="description" content="Three questions people ask of galaxy simulations, answered from the dataset: how many simulations can be compared with the observations, why not, and how far each lies from them.">
{{head}}
</head>
<body>
{{header}}
<main id="main" class="wrap page" tabindex="-1">
<div class="doc">
<nav class="idx nophone" aria-label="On this page"><p class="lab">Contents</p><ol><li><a href="#list"><span aria-hidden="true">§1</span>The answers</a></li></ol></nav>
<div class="c">
<div class="title">
<p class="lab kicker">Answers</p>
<h1>Three questions, answered from the data</h1>
<p class="standfirst">Each page takes a question people ask of galaxy simulations, shows the simulations and the observations on one plot, says how many of them can be fairly compared, why the others cannot, and how far each lies from the observation. The numbers are computed from the dataset with the Explorer's rules.</p>
</div>
<section class="sec" id="list" aria-labelledby="list-h">
<h2 id="list-h"><span class="sn" aria-hidden="true">§1</span>The answers</h2>
<dl class="inst">
${cards.map(c => `<div><dt><a href="${c.page}">${esc(c.short)}</a></dt><dd>${esc(c.question)} ${esc(c.line)}.</dd></div>`).join("\n")}
</dl>
<p>Behind each page is the same dataset as the <a href="../highline.html">Explorer</a>. For a question that is not here, start there.</p>
</section>
</div>
</div>
</main>
{{footer}}
</body>
</html>
`;
  return { pages, index: indexHtml, cards };
}
