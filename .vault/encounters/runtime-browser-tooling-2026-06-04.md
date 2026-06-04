---
date: 2026-06-04
plan: ".vault/plans/003-runtime-web-control-deck-2026-06-04.md"
scope: "browser verification"
---

# Runtime Browser Tooling

## Encounter

The Playwright MCP server was configured to launch Chrome from `/opt/google/chrome/chrome`, but that binary was not installed. The Playwright CLI could still capture screenshots, and a one-off interaction script worked after installing Playwright under `/tmp/pokemon-runtime-pw`.

## Impact

MCP browser actions could not be used for the web control deck verification pass, but CLI screenshots and a local Playwright script still provided browser evidence.

## Prevention

For future browser verification in this environment, either:

- install the Chrome binary expected by the MCP server, or
- use `npm install --prefix /tmp/pokemon-runtime-pw playwright` and run scripts with `NODE_PATH=/tmp/pokemon-runtime-pw/node_modules`.
