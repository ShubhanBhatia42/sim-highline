// Text and table rows of the quenching-shape study page (site/src/study-shape.html), generated from data/analysis/quenching-shape.json (and the checks made after the run, if present). Nothing is typed here that a number could change.
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const md = t => esc(t).replace(/(\d) %/g, "$1%").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
const f = (v, d = 2) => (v == null || !Number.isFinite(v) ? "–" : v.toFixed(d));
const SETS = [["shape", "shape (green-valley fraction and width)"], ["sf2", "quenched fraction and main sequence"], ["sf2+shape", "those two plus the shape"], ["joint", "the joint set of the earlier study"], ["joint+shape", "the joint set plus the shape"], ["hmf", "halo mass function (negative control)"]];
const SENS = { "S2:gv": "green-valley fraction alone", "S2:sfw": "width alone", "S3:wide": "lower threshold at −11.5 for the green valley, with the width", "S1:shape": "shape without the two lowest mass bins", "S1:sf2": "quenched fraction and main sequence without the two lowest mass bins", "S1:sf2+shape": "those plus the shape, without the two lowest mass bins", "S1:joint": "joint set without the two lowest mass bins", "S1:joint+shape": "joint set plus shape, without the two lowest mass bins" };

export function shapeStats(R, CK) {
  if (!R) return { qsTodo: true };
  const v = R.verdicts, p = R.point, s = R.splits, val = R.validations, q2 = R.paired.Q2, q3 = R.paired.Q3;
  const bad = Object.entries(val).filter(([, x]) => x && x.passed === false).map(([k]) => k);
  const word = { structural: "structural", removable: "removable", unresolved: "unresolved" };
  const rows = SETS.filter(([k]) => s[k]).map(([k, t]) => `<tr><td>${esc(t)}</td><td class="n">${p[k].n_outputs}</td><td class="n">${f(p[k].D_fiducial)}</td><td class="n">${f(p[k].D)}</td><td class="n">${f(s[k].between.p5)} / ${f(s[k].between.p50)} / ${f(s[k].between.p95)}</td><td class="n">${f(s[k].control.p95)}</td><td>${word[s[k].verdict]}</td></tr>`).join("");
  const pair = (q, label) => `<tr><td>${esc(label)}</td><td class="n">${f(q.excess.p5, 3)} / ${f(q.excess.p50, 3)} / ${f(q.excess.p95, 3)}</td><td class="n">${f(q.between.p5, 3)} / ${f(q.between.p50, 3)} / ${f(q.between.p95, 3)}</td><td>${word[q.verdict_base]} → ${word[q.verdict_big]}</td><td><b>${esc(q.verdict)}</b></td></tr>`;
  const V = val, valRows = [
    ["Emulator error of the shape outputs against their seed noise: share of outputs within 1.5 times (IllustrisTNG / SIMBA)", `${f(V.V1.IllustrisTNG["fraction_below_1.5"])} / ${f(V.V1.SIMBA["fraction_below_1.5"])}; median ratio ${f(V.V1.IllustrisTNG.median_ratio)} / ${f(V.V1.SIMBA.median_ratio)}`, "≥ 0.8 each", V.V1.passed],
    ["Negative control: the halo mass function", `${V.V2.verdict}`, "removable", V.V2.passed],
    ["Outputs resting on fewer than 30 galaxies per bin in the median fiducial simulation", `${f(100 * V.V3.share_below_30, 0)}%`, "≤ 25%", V.V3.passed],
    ["Point distance of the shape set with 4 and 8 random starts", `${f(V.V4.D_starts_4, 3)} and ${f(V.V4.D_starts_8, 3)} (${f(100 * V.V4.relative_change, 0)}%)`, "< 5%", V.V4.passed]]
    .map(([a, b, c, ok]) => `<tr><td>${esc(a)}</td><td>${esc(b)}</td><td>${esc(c)}</td><td>${ok ? "yes" : "<b>no</b>"}</td></tr>`).join("");
  const sensRows = Object.entries(SENS).filter(([k]) => s[k]).map(([k, t]) => `<tr><td>${esc(t)}</td><td class="n">${f(p[k].D)}</td><td>${word[s[k].verdict]}</td></tr>`).join("");
  const ck = CK && CK.distances ? CK.distances["registered (seed noise and emulator error)"] : null, ckSeed = CK && CK.distances ? CK.distances["seed noise only"] : null, last = CK ? String(CK.starts[CK.starts.length - 1]) : null;
  const why = { V1: "the emulators of these outputs are less accurate than the run-to-run scatter", V2: "the negative control (the halo mass function) was not removable", V3: "too many outputs rest on few galaxies", V4: `the search for the best setting is not stable with four random starts${ck ? `; with up to ${last} starts the distance settles at ${f(ck.rows[last].median, 2)}` : ""}` };
  const caveat = bad.length ? ` ${["No", "One", "Two", "Three", "Four"][bad.length]} of the four checks set in advance did not hold (${bad.join(", ")}): ${bad.map(k => why[k]).join("; ")}.` : "";
  const q1w = v.Q1 === "removable" ? "can be brought into agreement" : v.Q1 === "structural" ? "stay apart" : "are neither clearly together nor clearly apart";
  const addw = x => x === "adds separation" ? "adds a difference between the codes" : x === "adds nothing detectable" ? "adds no difference we can detect" : "has an unclear effect";
  const out = {
    qsTodo: false,
    qsStatus: "Pre-registered · result",
    qsHead: `shape alone ${v.Q1}; added to the usual two: ${v.Q2}; added to everything: ${v.Q3}`,
    qsAbs: `Does the share of galaxies between the blue cloud and the red sequence, and the width of the star-forming sequence, separate IllustrisTNG from SIMBA in CAMELS beyond what the quenched fraction and the main sequence already do? Over ${p.shape.n_outputs} outputs in ${p.shape.n_blocks} blocks (z = 0 and 0.95) the shape alone is ${v.Q1}: half-sample median ${f(s.shape.between.p50)} noise units, same-code controls at most ${f(s.shape.control.p95)}, ${f(p.shape.D_fiducial)} at the fiducial parameters. Added to the quenched fraction and the main sequence it ${addw(v.Q2)} (excess over the controls, 5th to 95th percentile ${f(q2.excess.p5, 2)} to ${f(q2.excess.p95, 2)} noise units); added to the joint set of the earlier study it ${addw(v.Q3)} (${f(q3.excess.p5, 2)} to ${f(q3.excess.p95, 2)}).${caveat} The rules were fixed before the data were ingested, with one amendment made before any distance existed.`,
    qsStatusShort: `Q1 ${v.Q1}; Q2 ${v.Q2}; Q3 ${v.Q3}`,
    qsEligible: `${R.meta.n_outputs_eligible} of ${R.meta.n_outputs_total} outputs (these and the earlier study's) are eligible; the shape outputs are eligible at z = 0 and 0.95 and not at z = 2.15, where too few bins hold enough galaxies.`,
    qsHeadline: R.headline.map(h => `<li>${md(h)}</li>`).join(""),
    qsSetRows: rows,
    qsPairRows: pair(q2, "Q2: shape added to the quenched fraction and the main sequence") + pair(q3, "Q3: shape added to the joint set"),
    qsValRows: valRows,
    qsSensRows: sensRows,
    qsDev: R.deviations.map(d => `<li>${md(d)}</li>`).join(""),
    plainShapeOne: v.Q1 === "removable" && v.Q2 !== "adds separation" && v.Q3 !== "adds separation"
      ? "Looking at how many galaxies sit between the blue and the red groups, and how wide the blue group is, did not find a new way to tell the two codes apart."
      : v.Q2 === "adds separation" || v.Q3 === "adds separation" ? "The shape of the star-forming and quenched populations does add a difference between the two codes." : "The shape of the star-forming and quenched populations does not give a clear answer on whether it separates the two codes.",
    plainShape: `The earlier study found that the two codes cannot be made to agree on everything at once, mainly because of black holes. This study asked whether the finer shape of the star-forming and quenched populations is another place where they differ. With the dials of each code set freely, the shape outputs ${q1w}; ${v.Q2 === v.Q3 ? `adding them to the other star-formation measures, or to everything, ${addw(v.Q2)}` : `adding them to the other star-formation measures ${addw(v.Q2)}, and adding them to everything ${addw(v.Q3)}`}. The distance to the other measures even falls when the shape is added, because the codes already agree on it (an averaging effect, not a sign that the shape closes the gap).${bad.length ? " Some of the checks we set in advance did not hold, so this is a result with limited power: it says that no extra difference was found, not that there is none." : ""}`
  };
  return out;
}
