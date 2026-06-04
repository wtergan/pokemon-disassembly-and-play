---
date: 2026-06-04
status: accepted
related_plan: .vault/plans/004-codex-agent-loop-2026-06-04.md
---

# Agent Action Policy Boundaries

## Decision

Planner-facing agent actions use advertised `action_id` values instead of raw
runtime primitives. Optional `button`, `frames`, and `slot` fields are accepted
only when they match the advertised affordance exactly.

## Rationale

- The agent context can advertise a small stable tool surface without exposing
  raw emulator, Lua, memory, or filesystem operations.
- Fixed frame counts keep tap, hold, and wait behavior bounded.
- `save_quick` and `load_quick` are pinned to the runtime-owned `quick` slot.
- Rejected actions are traced before raising so unsafe or malformed planner
  output remains reviewable.

## Consequences

- Manual `/action` remains available for the web control deck, but agent callers
  should use `RuntimeCore.execute_agent_action()` and later agent endpoints.
- New agent affordances must be added to `tools/runtime/interaction_policy.py`
  and covered with rejection and execution tests.
- Objective-runner success must still be verified against telemetry deltas in a
  later milestone; action execution alone is not proof of progress.
