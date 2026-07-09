---
date: 2026-07-09
tags: [mgba, wsl, autonomy, verification]
related_feature_plan: ".vault/plans/006-runtime-reconnect-and-autonomy-smoke-2026-07-09.md"
---

# mGBA Lua Retry And Objective Action Count

## Problem

A fresh WSL-to-Windows mGBA launch could miss the reverse socket once, and a
visible emulator's continually advancing frame count could make an objective
succeed before the intended number of planner actions ran.

## Root Cause

The Lua client made exactly one blocking connection attempt. Objective scoring
only considered emulator state, even when the acceptance criterion was the
number of inspected autonomous actions.

## Solution

Retry reverse-socket startup at bounded frame intervals for at most 20 attempts,
give Python 20 seconds to accept, and support
`success.agent_steps_at_least` in the objective runner.

## Files Changed

- `tools/runtime/emulators/mgba_bridge.lua`
- `tools/runtime/emulators/mgba_bridge.py`
- `tools/runtime/objective_scoring.py`
- `tools/runtime/objective_runner.py`
- `tools/runtime/tests/test_mgba_lua_client_should_retry_transient_connection.py`
- `tools/runtime/tests/test_objective_agent_steps_should_require_executed_actions.py`

## Verification

- Full runtime suite: `89 passed in 8.82s`.
- Real FireRed mGBA smoke: Lua bridge connected and the GPT-5.6-Luna planner
  executed `tap_a`, `tap_start`, and `tap_up` through policy validation.

## Reuse Guidance

Use explicit action-count criteria for bounded autonomy checks. Use telemetry
criteria only when the required semantic state is actually observable.
