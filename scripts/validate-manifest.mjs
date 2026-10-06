import { readFile } from "node:fs/promises";

const manifest = JSON.parse(await readFile(new URL("../data/manifest.json", import.meta.url), "utf8"));
const registry = JSON.parse(await readFile(new URL("../data/simulations.json", import.meta.url), "utf8"));
const ingestion = JSON.parse(await readFile(new URL("../data/ingestion-manifest.json", import.meta.url), "utf8"));
const allowedStatus = new Set(["planned", "audit", "run-locally", "verified", "corrected-catalog-required"]);
const allowedAssetStatus = new Set(["verified-listed", "verified-auth-required", "index-verified", "ingested"]);
const errors = [];

if (!/^\d+\.\d+\.\d+$/.test(manifest.schemaVersion || "")) errors.push("schemaVersion must be semantic");
if (!Array.isArray(manifest.adapters) || !manifest.adapters.length) errors.push("at least one adapter is required");

const adapterIds = new Set();
for (const adapter of manifest.adapters || []) {
  if (adapterIds.has(adapter.id)) errors.push(`duplicate adapter id: ${adapter.id}`);
  adapterIds.add(adapter.id);
  for (const field of ["id", "kind", "transport", "status", "relations"]) {
    if (adapter[field] === undefined) errors.push(`${adapter.id || "adapter"}: missing ${field}`);
  }
  if (!allowedStatus.has(adapter.status)) errors.push(`${adapter.id}: invalid status ${adapter.status}`);
  if (!Array.isArray(adapter.relations) || !adapter.relations.length) errors.push(`${adapter.id}: relations must be non-empty`);
}

const ids = new Set();
const tiers = new Set(registry.evidenceTiers || []);
const families = new Set((registry.families || []).map(family => family.id));
for (const simulation of registry.simulations || []) {
  if (ids.has(simulation.id)) errors.push(`duplicate simulation id: ${simulation.id}`);
  ids.add(simulation.id);
  if (!tiers.has(simulation.access)) errors.push(`${simulation.id}: invalid evidence tier ${simulation.access}`);
  if (simulation.family !== "independent" && !families.has(simulation.family)) errors.push(`${simulation.id}: unknown family ${simulation.family}`);
  if (!Array.isArray(simulation.redshiftRange) || simulation.redshiftRange.length !== 2) errors.push(`${simulation.id}: redshiftRange must have two values`);
  if (!/^https:\/\//.test(simulation.source || "")) errors.push(`${simulation.id}: primary source URL required`);
}
const assetIds = new Set();
for (const asset of ingestion.assets || []) {
  if (assetIds.has(asset.id)) errors.push(`duplicate ingestion asset id: ${asset.id}`);
  assetIds.add(asset.id);
  if (!allowedAssetStatus.has(asset.status)) errors.push(`${asset.id}: invalid ingestion status ${asset.status}`);
  if (!/^https:\/\//.test(asset.url || "")) errors.push(`${asset.id}: HTTPS source URL required`);
}
for (const family of registry.families || []) for (const id of family.members || []) {
  if (ids.has(id) && !registry.simulations.find(simulation => simulation.id === id && simulation.family === family.id)) errors.push(`${id}: family mismatch`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`sim-highline manifest ${manifest.schemaVersion}: ${manifest.adapters.length} adapters, ${registry.simulations.length} simulations and ${ingestion.assets.length} ingestion assets valid`);
}
