// How the browser tests start a browser.
//   PW_BROWSER     chromium (default), firefox or webkit
//   PW_CHANNEL     an installed browser channel (used in CI, Chromium only)
//   PW_EXECUTABLE  a Chromium binary, for when the installed Playwright expects a different download than the one on the machine
// With none of the last two set, a Chromium at /opt/pw-browsers/chromium is used if there is one (managed cloud sessions), else Playwright's own download.
import { existsSync } from "node:fs";
import * as pw from "playwright";
export const browserName = () => process.env.PW_BROWSER || "chromium";
export const launchOptions = () => browserName() !== "chromium" ? {}
  : process.env.PW_EXECUTABLE ? { executablePath: process.env.PW_EXECUTABLE }
  : process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL }
  : existsSync("/opt/pw-browsers/chromium") ? { executablePath: "/opt/pw-browsers/chromium" }
  : {};
export const launchBrowser = () => pw[browserName()].launch(launchOptions());
