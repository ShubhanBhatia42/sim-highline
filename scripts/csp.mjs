// A Content-Security-Policy for the built pages, as a <meta> tag: scripts only from the page itself or by the hash of each inline script (so injected script cannot run), styles inline or from Google Fonts, fonts from Google Fonts, images from the page, data: and blob:, no plug-ins, no form posts, and connections only back to the same site.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
// optional page-count beacon (data/usage-counts.json, off by default): the page path only, no identifier, nothing when the browser sends Do Not Track
const USAGE = JSON.parse(readFileSync(new URL("../data/usage-counts.json", import.meta.url), "utf8"));
const beacon = USAGE.enabled && /^https:\/\/[^"'\s<>]+$/.test(USAGE.endpoint || "") ? `<script>(function(){try{if(navigator.doNotTrack==="1"||window.doNotTrack==="1")return;navigator.sendBeacon(${JSON.stringify(USAGE.endpoint)},JSON.stringify({path:location.pathname}))}catch(e){}})();</script>` : "";
export function withCsp(html) {
  if (beacon) html = html.replace("</body>", beacon + "</body>");
  const hashes = [...new Set([...html.matchAll(/<script(?![^>]*\bsrc=)(?![^>]*type="application\/(?:ld\+)?json")[^>]*>([\s\S]*?)<\/script>/g)].map(m => `'sha256-${createHash("sha256").update(m[1]).digest("base64")}'`))];
  const policy = ["default-src 'self'", `script-src 'self' ${hashes.join(" ")}`.trim(), "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com", "font-src https://fonts.gstatic.com", "img-src 'self' data: blob:", `connect-src 'self'${beacon ? " " + new URL(USAGE.endpoint).origin : ""}`, "object-src 'none'", "base-uri 'self'", "form-action 'none'"].join("; ");
  if (!/<meta charset="utf-8">/.test(html)) throw new Error("withCsp: no <meta charset> to place the policy after");
  return html.replace(/<meta charset="utf-8">/, m => `${m}<meta http-equiv="Content-Security-Policy" content="${policy}">`);
}
