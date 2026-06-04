---
date: 2026-06-04
plan: .vault/plans/002-firered-telemetry-adapter-2026-06-04.md
scope: runtime dependency verification
---

# FastAPI Starlette Compatibility

## Encounter

The local runtime venv resolved `fastapi 0.136.3` with `starlette 1.2.1`.
Under that combination, even a minimal one-route FastAPI app hung during manual
ASGI invocation and when using the endpoint client path.

## Root Cause

`tools/runtime/requirements.txt` only specified `fastapi>=0.115`, which allowed
a future Starlette major version. The resolver accepted `starlette 1.2.1`, but
the local ASGI request path was not usable.

## Fix

- Pin `starlette<1.0` in `tools/runtime/requirements.txt`.
- Replace `fastapi.testclient.TestClient` usage in runtime tests with a small
  `httpx.ASGITransport` helper.
- Guard endpoint tests with a skip when the currently installed Starlette major
  version is incompatible with the repo pin, so stale local environments skip
  instead of hanging.

## Prevention

Re-sync the runtime venv after dependency changes before claiming HTTP endpoint
verification. If DNS/package fetch is unavailable, record endpoint checks as
skipped rather than passing.
