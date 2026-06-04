---
date: 2026-06-04
status: accepted
related_plan: .vault/plans/004-codex-agent-loop-2026-06-04.md
---

# Agent Client Disabled By Default

## Decision

The runtime defaults to `[agent].mode = "disabled"` even though it now has fake
and `codex app-server` planner client implementations.

## Rationale

- Manual runtime observation/control must not require Codex credentials,
  background app-server processes, or network/model availability.
- Fake mode gives deterministic tests and local objective-runner development.
- App-server mode must be opted into explicitly from ignored local config.
- `RuntimeCore.close()` closes any configured planner client so app-server
  process ownership remains bounded by the runtime lifecycle.

## Consequences

- Plan 004 can build objective-runner and UI behavior against the same
  `AgentService` contract regardless of backend.
- A real autonomous run should still wait for M4.T4/M4.T5 step caps, stop
  controls, and UI visibility.
