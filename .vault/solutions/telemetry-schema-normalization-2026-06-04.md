---
date: 2026-06-04
plan: ".vault/plans/002-firered-telemetry-adapter-2026-06-04.md"
scope: "runtime telemetry schema"
---

# Telemetry Schema Normalization

## Pattern

Normalize every telemetry payload through `tools/runtime/state_models.py` before it leaves a runtime adapter.

The schema envelope keeps:

- `schema_version`
- legacy-friendly `game`, `revision`, and `frame`
- structured `target` and `runtime`
- explicit unavailable sections for `rom`, `symbols`, `save_blocks`, `location`, `mode`, `camera`, and `save`
- derived `capabilities` for UI and agent consumers

## Why

Game-specific telemetry grows quickly and not every runtime has generated symbols, map assets, or a configured game adapter. The UI and future agent loop need stable keys without treating omitted data as success.

## Validation

- `timeout 30s /tmp/pokemon-runtime-venv/bin/python -m pytest -q tools/runtime/tests/test_telemetry_schema_should_publish_stable_contract.py tools/runtime/tests/test_firered_saveblock_fixture_should_decode_position.py tools/runtime/tests/test_runtime_factory_should_create_configured_runtime.py -vv` -> `12 passed, 1 skipped`
- `timeout 60s /tmp/pokemon-runtime-venv/bin/python -m pytest -q tools/runtime/tests` -> `37 passed, 8 skipped`
- `timeout 30s /tmp/pokemon-runtime-venv/bin/python -m compileall -q tools/runtime`
- `git diff --check`
