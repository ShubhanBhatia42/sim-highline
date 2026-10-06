import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
const root = new URL("../", import.meta.url);
const doc = JSON.parse(await readFile(new URL("data/literature-backlog.json", root), "utf8"));
const STATUS = new Set(["ingested", "queued", "skipped", "candidate"]);
const seen = new Set();
const cited = new Set();
for (const f of (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json"))) {
  for (const r of JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records) for (const m of `${r.provenance.url} ${r.provenance.citation}`.matchAll(/\d{4}\.\d{4,5}/g)) cited.add(m[0]);
}
for (const e of doc.entries) {
  assert(/^\d{4}\.\d{4,5}$/.test(e.arxiv), `bad arXiv id ${e.arxiv}`);
  assert(!seen.has(e.arxiv), `duplicate ${e.arxiv}`);
  seen.add(e.arxiv);
  assert(STATUS.has(e.status), `${e.arxiv}: bad status ${e.status}`);
  assert(e.title && e.project && e.year >= 1990, `${e.arxiv}: incomplete entry`);
  assert((e.status === "ingested") === cited.has(e.arxiv), `${e.arxiv}: status ${e.status} disagrees with the curve provenance`);
  if (e.status === "skipped") assert(e.statusNote, `${e.arxiv}: skipped needs a reason`);
}
console.log(`Literature backlog valid: ${doc.entries.length} entries, ${doc.entries.filter(e => e.status === "ingested").length} ingested, ${doc.entries.filter(e => e.status === "queued").length} queued`);
