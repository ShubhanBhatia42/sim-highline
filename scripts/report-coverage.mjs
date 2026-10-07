import { readFile, readdir, writeFile } from "node:fs/promises";

const curveDir = new URL("../data/curves/", import.meta.url);
const files = (await readdir(curveDir)).filter(file => file.endsWith(".json"));
const records = (await Promise.all(files.map(async file => JSON.parse(await readFile(new URL(file, curveDir), "utf8")).records))).flat();

const byRelation = Object.groupBy(records, record => record.relation);
const bySource = Object.groupBy(records, record => record.source);
const summarize = entries => Object.fromEntries(Object.entries(entries).sort(([a],[b]) => a.localeCompare(b)).map(([key, values]) => [key, {
  records: values.length,
  epochs: [...new Set(values.map(record => record.epoch.zRepresentative))].sort((a,b) => a-b),
  epochRanges: [...new Set(values.map(record => `${record.epoch.zMin}:${record.epoch.zMax}`))].sort(),
  relations: [...new Set(values.map(record => record.relation))].sort(),
  rankable: values.filter(record => record.rankable).length,
  contextOnly: values.filter(record => !record.rankable).length,
  tiers: [...new Set(values.map(record => record.provenance.tier))].sort()
}]));

const report = {
  schemaVersion: "1.0.0",
  generatedAt: JSON.parse(await readFile(new URL("../data/release.json", import.meta.url), "utf8")).released,
  totals: {
    records: records.length,
    sources: Object.keys(bySource).length,
    relations: Object.keys(byRelation).length,
    rankable: records.filter(record => record.rankable).length,
    contextOnly: records.filter(record => !record.rankable).length
  },
  byRelation: summarize(byRelation),
  bySource: summarize(bySource)
};

await writeFile(new URL("../data/coverage-report.json", import.meta.url), `${JSON.stringify(report,null,2)}\n`);
console.log(`Coverage report: ${report.totals.records} records, ${report.totals.sources} sources, ${report.totals.relations} relations`);
