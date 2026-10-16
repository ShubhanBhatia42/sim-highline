// How the browser tests start Chromium. PW_CHANNEL picks an installed browser channel (used in CI); PW_EXECUTABLE points at a Chromium binary when the installed Playwright expects a different download than the one on the machine.
export const launchOptions = () =>
  process.env.PW_EXECUTABLE ? { executablePath: process.env.PW_EXECUTABLE }
  : process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL }
  : {};
