---
date: 2026-07-09
status: resolved
severity: medium
related_feature_plan: ".vault/plans/006-runtime-reconnect-and-autonomy-smoke-2026-07-09.md"
---

# Transient mGBA Reverse Socket And Frame-Only Success

## Trigger

Fresh FireRed launch and a first real app-server objective smoke after a month
without runtime use.

## Symptom

The Lua client logged a failed connection and the Python listener timed out.
After reconnecting, a `runtime_frame_at_least` smoke passed after one wait action
because visible mGBA advanced while the planner response was pending.

## Root Cause

Both controls depended on elapsed time: a single startup connection and a frame
threshold did not prove the desired interaction count.

## Resolution

Added bounded retry logic and an explicit `agent_steps_at_least` criterion.

## Prevention Rule

For WSL/Windows mGBA, keep a finite Lua-client reconnect window. For autonomy
smokes, make the success criterion match the evidence being claimed.

## Evidence

- `tools/runtime/tests/test_mgba_lua_client_should_retry_transient_connection.py`
- `tools/runtime/tests/test_objective_agent_steps_should_require_executed_actions.py`
- Full suite: `89 passed in 8.82s`.
