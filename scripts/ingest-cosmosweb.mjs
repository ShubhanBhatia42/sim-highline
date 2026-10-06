import { definitionsFor } from "./definitions.mjs";
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";

const input = process.argv[2] ? pathToFileURL(process.argv[2]) : new URL("file:///private/tmp/cosmosweb-smf.ecsv");
const output = new URL("../data/curves/cosmosweb.json", import.meta.url);
const bytes = await readFile(input);
const checksumSha256 = createHash("sha256").update(bytes).digest("hex");
const sourceUrl = "https://raw.githubusercontent.com/mShuntov/SMF_in_COSMOS-Web_Shuntov2024/main/SMF_data_points.ecsv";
const groups = new Map();

for (const line of bytes.toString("utf8").split(/\r?\n/)) {
  const match = line.match(/^"([\d.]+) < z < ([\d.]+)"\s+([\deE+.-]+)\s+([\deE+.-]+)\s+([\deE+.-]+)$/);
  if (!match) continue;
  const [, low, high, mass, phi, error] = match;
  const key = `${low}:${high}`;
  if (!groups.has(key)) groups.set(key, { zMin: +low, zMax: +high, rows: [] });
  groups.get(key).rows.push({ x: +mass, phi: +phi, error: +error });
}

const records = [...groups.values()].map(({ zMin, zMax, rows }) => {
  const points = rows.filter(({ phi, error }) => phi > 0 && phi + error > 0).map(({ x, phi, error }) => ({
    x: +x.toFixed(6),
    y: +Math.log10(phi).toFixed(6),
    yLow: +(phi > error ? Math.log10(phi - error) : Math.log10(phi)).toFixed(6),
    yHigh: +Math.log10(phi + error).toFixed(6)
  }));
  const zRepresentative = +(0.5 * (zMin + zMax)).toFixed(3);
  return {
    id: `cosmosweb25.gsmf.z${zMin}-${zMax}.official`, source: "COSMOS-Web 2025", run: null,
    kind: "observation", relation: "gsmf",
    epoch: { zRepresentative, zMin, zMax, mode: "observational-bin", snapshot: null },
    axes: {
      xDefinition: "log10 stellar mass, Chabrier (2003) IMF", xUnit: "log10(Msun)",
      yDefinition: "log10 total galaxy number density per dex", yUnit: "log10(Mpc^-3 dex^-1)"
    },
    domain: { xMin: points[0].x, xMax: points.at(-1).x },
    representation: { type: "points", intervalKind: "uncertainty", points },
    scatter: { lower: "tabulated total uncertainty", upper: "tabulated total uncertainty" },
    selection: {
      population: "COSMOS-Web total galaxy sample",
      warning: "Mass completeness, SED-model systematics and cosmic variance evolve across the published redshift bins."
    },
    definitions: definitionsFor("COSMOS-Web 2025", "gsmf"),
    provenance: {
      tier: "official-table", citation: "Shuntov et al. 2025, A&A 695, A20",
      doi: "10.1051/0004-6361/202452570", url: sourceUrl, retrieved: "2026-10-02", checksumSha256
    },
    calibration: "validation", rankable: true,
    notes: "Official ECSV points. Linear Phi and dPhi transformed to log space; non-positive lower limits are shown at the central value rather than invented."
  };
});

records.sort((a, b) => a.epoch.zRepresentative - b.epoch.zRepresentative);
await writeFile(output, `${JSON.stringify({ schemaVersion: "1.0.0", records }, null, 2)}\n`);
console.log(`Ingested ${records.length} COSMOS-Web GSMF redshift bins`);
