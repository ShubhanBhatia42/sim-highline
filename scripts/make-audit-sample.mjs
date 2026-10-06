import { readdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const root = new URL("../", import.meta.url);
const files = (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json")).sort();
const all = [];
for (const f of files) for (const r of JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records) all.push({ ...r, _file: f });
const h = s => createHash("sha256").update(s).digest("hex");
const bySource = new Map();
for (const r of all.filter(r => r.kind === "simulation")) (bySource.get(r.source) || bySource.set(r.source, []).get(r.source)).push(r);
const rows = [];
for (const [source, rs] of [...bySource].sort((a, b) => a[0].localeCompare(b[0]))) {
  const byRel = new Map();
  for (const r of rs.sort((a, b) => h(a.id).localeCompare(h(b.id)))) if (!byRel.has(r.relation)) byRel.set(r.relation, r);
  const pick = [...byRel.values()].sort((a, b) => (b.provenance.tier === "digitized-figure") - (a.provenance.tier === "digitized-figure") || h(a.id).localeCompare(h(b.id))).slice(0, 2);
  rows.push(...pick);
}
const md = `# Expert audit sample

Records for an independent check by someone who knows each suite. Selection is deterministic (two records per simulation source, different relations, digitized figures first, ordered by a hash of the id), so the list is stable between releases of the same data. ${rows.length} records from ${bySource.size} sources.

For each record: open the cited figure or table, confirm (1) the curve is the one named (run, population, panel), (2) the axis values at two labelled ticks, (3) the definitions block (mass aperture, IMF, SFR timescale, halo definition), and (4) that the epoch is the published one. Report disagreements with the record id.

| source | record | relation | z | tier | citation |
|---|---|---|---|---|---|
${rows.map(r => `| ${r.source} | \`${r.id}\` | ${r.relation} | ${r.epoch.zRepresentative} | ${r.provenance.tier} | ${r.provenance.citation.replace(/\|/g, "/")} |`).join("\n")}
`;
await writeFile(new URL("docs/expert-audit-sample.md", root), md);
console.log(`Audit sample: ${rows.length} records from ${bySource.size} sources -> docs/expert-audit-sample.md`);
