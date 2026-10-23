// How the Explorer's data is split so that the first page load does not carry every curve.
//
// data/curve-index.js (all records, one browser-readable file) is not changed. For the Explorer, scripts/build-highline.mjs cuts it in two:
//   1. an embedded index with one small entry per record: what the page needs to list, count, search and group records without drawing them
//      (see lightRecord below), and
//   2. one file per relation, dist/highline-data/<relation>.json, holding the complete records of that relation exactly as they are in the index.
// The page fetches a relation's file the first time it needs that relation's numbers and completes the index entries in place.
// This module is shared by the build and by scripts/test-explorer-data.mjs, so the test checks the same rules the build applies.
import { createHash } from "node:crypto";

export const DATA_DIR = "highline-data";

/** data/curve-index.js is `window.NAME=<JSON>;` statements; returns {NAME: parsed JSON, ...}. */
export function parseIndex(text) {
  const parts = {};
  for (const st of text.replace(/^window\./, "").split(/;\s*\nwindow\./)) {
    const i = st.indexOf("=");
    parts[st.slice(0, i)] = JSON.parse(st.slice(i + 1).replace(/;\s*$/, ""));
  }
  return parts;
}

/** A record the Explorer can draw. Records without a representation or a domain were never listed by the page. */
export const drawable = r => !!(r.representation && r.domain);

/**
 * The embedded entry for one record. It keeps each field in the place the page reads it, only thinner, so the page's code does not change:
 * identity (id, source, run, kind, relation), the epoch limits, the representation type (and whether it is a connected curve or carries a
 * per-galaxy distribution), the evidence tier and citation (tooltips, badges, search), and the rankable flag.
 * The metallicity relation is split into three on the page by the quantity and the y axis, so those two fields stay for it.
 * Everything else (points, parameters, distributions, definitions, selection, notes, the rest of the provenance) arrives with the relation's file.
 */
export function lightRecord(r) {
  const rep = r.representation;
  const o = {
    id: r.id, source: r.source, run: r.run, kind: r.kind, relation: r.relation,
    epoch: { mode: r.epoch.mode, zMin: r.epoch.zMin, zMax: r.epoch.zMax, zRepresentative: r.epoch.zRepresentative },
    representation: { type: rep.type },
    provenance: { tier: r.provenance.tier, citation: r.provenance.citation },
    rankable: r.rankable,
  };
  if (rep.connect !== undefined) o.representation.connect = rep.connect;
  if (rep.distribution) o.representation.distribution = true;
  if (r.relation === "mzr") { o.definitions = { metallicityQuantity: r.definitions?.metallicityQuantity }; o.axes = { yDefinition: r.axes?.yDefinition }; }
  return o;
}

/** The complete records of each relation as the text of one file, with a short content hash the page puts in the URL (so a cached file always belongs to the page that asks for it). */
export function splitByRelation(records) {
  const by = new Map();
  for (const r of records) {
    if (!/^[a-z0-9-]+$/.test(r.relation)) throw new Error(`${r.id}: relation "${r.relation}" cannot be a file name`);
    (by.get(r.relation) || by.set(r.relation, []).get(r.relation)).push(r);
  }
  const files = new Map();
  for (const rel of [...by.keys()].sort()) {
    const text = JSON.stringify(by.get(rel));
    files.set(rel, { text, v: createHash("sha256").update(text).digest("hex").slice(0, 12), n: by.get(rel).length });
  }
  return files;
}

/** Everything the build embeds and writes. */
export function splitForExplorer(records) {
  const light = records.filter(drawable).map(lightRecord);
  const files = splitByRelation(records);
  const manifest = { dir: DATA_DIR, files: Object.fromEntries([...files].map(([rel, f]) => [rel, { v: f.v, n: f.n }])) };
  return { light, files, manifest };
}
