---
date: 2026-06-04
plan: ".vault/plans/003-runtime-web-control-deck-2026-06-04.md"
scope: "runtime web control deck"
---

# Runtime Web Control Deck Pattern

## Pattern

Keep the browser deck static and split behavior into small ES modules:

- `api-client.js` owns endpoint calls, timeouts, and error extraction.
- `telemetry-format.js` owns display summaries for decoded and unavailable state.
- `app.js` coordinates DOM updates, polling, input, and state-slot actions.

Runtime state slots are addressed by validated slot names and mapped to contained files under `state_dir` by `tools/runtime/state_slots.py`.

## Browser Verification

- Desktop screenshot: `/tmp/pokemon-runtime-m3-desktop-fixed.png`
- Mobile screenshot: `/tmp/pokemon-runtime-m3-mobile-fixed.png`
- Interaction smoke: Playwright script verified held input state, save/load state feedback, and action/state trace rendering against `http://127.0.0.1:18765/`.

## Validation

- `timeout 60s /tmp/pokemon-runtime-venv/bin/python -m pytest -q tools/runtime/tests` -> `50 passed, 5 skipped`
- `timeout 30s /tmp/pokemon-runtime-venv/bin/python -m compileall -q tools/runtime`
- `git diff --check`
