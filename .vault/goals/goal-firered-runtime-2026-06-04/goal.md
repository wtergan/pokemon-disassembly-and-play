# Goal: FireRed Runtime

## Objective

Build a Windows-friendly programmable runtime for Pokemon FireRed Rev 1, then
extend it toward LeafGreen Rev 1 after FireRed is stable. The runtime should be
inspired by Pocodex while using `pret/pokefirered`, a dedicated mGBA emulator
instance, the user's owned ROMs, a browser control deck, telemetry, traces, and a
planner-safe Codex agent loop.

## Starting Point

- Project index: `.vault/PLAN.md`
- Active goal run: `.vault/goals/goal-firered-runtime-2026-06-04/`
- Existing plans:
  - `.vault/plans/001-firered-runtime-spike-2026-06-04.md`
  - `.vault/plans/002-firered-telemetry-adapter-2026-06-04.md`
  - `.vault/plans/003-runtime-web-control-deck-2026-06-04.md`
  - `.vault/plans/004-codex-agent-loop-2026-06-04.md`
  - `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md`

## Acceptance Criteria

- [ ] Plan 001 proves the dedicated mGBA runtime spike for FireRed Rev 1.
- [ ] Plan 002 provides source-backed FireRed telemetry beyond minimal pointer/location state.
- [ ] Plan 003 provides a usable browser control deck with traces, savestates, and verification.
- [ ] Plan 004 provides a bounded, validated Codex agent loop.
- [ ] Plan 005 adds LeafGreen Rev 1 target support and runtime hardening.
- [ ] ROMs, saves, local config, screenshots, credentials, and emulator state remain outside git.
- [ ] `.vault/goals/goal-firered-runtime-2026-06-04/progress.md` records execution evidence as plans advance.

## Non-Goals and Approval Boundaries

- Do not support unrelated Pokemon games or revisions without user approval.
- Do not distribute ROMs, BIOS files, saves, or emulator binaries.
- Do not run unbounded autonomous gameplay sessions.
- Ask before destructive git/filesystem operations, system-wide dependency installs, commits/pushes, credential setup, or scope expansion.

## Constraints

- Use FireRed Rev 1 first and LeafGreen Rev 1 later.
- Use a separate dedicated runtime emulator instance.
- Use mGBA first, with BizHawk fallback only if evidence shows mGBA blocks progress.
- Keep runtime core, emulator bridge, FireRed/LeafGreen telemetry, web UI, and agent loop modular.
- Prefer behavior-first tests and focused verification after each milestone.
- Capture durable decisions, reusable solutions, and recurring encounters in `.vault`.

## Native Goal Contract

```text
/goal Outcome: Execute the FireRed/LeafGreen runtime roadmap in `.vault/plans/001` through `.vault/plans/005`: bootstrap from `pret/pokefirered`, prove a dedicated mGBA FireRed Rev 1 runtime, expand telemetry, build the web control deck, add a bounded Codex agent loop, then add LeafGreen Rev 1 support and hardening.

Context: Start from `.vault/goals/goal-firered-runtime-2026-06-04/handoff.md`, `task-graph.md`, `.vault/PLAN.md`, and the linked plans. The workspace currently has `.vault` only; plan 001 bootstraps source before runtime code.

Boundaries: ROMs owned local under `C:\Emulation` stay outside git. Do not commit ROMs, saves, screenshots, local config, credentials, or emulator state. Do not attach to active Mesen2 sessions. Ask before destructive actions, system-wide installs, commits/pushes, credential setup, or scope expansion beyond FireRed/LeafGreen Rev 1.

Constraints: Use FireRed Rev 1 first, LeafGreen Rev 1 later, a dedicated emulator instance, and mGBA first with BizHawk fallback only after captured evidence. Keep runtime core, emulator bridge, game telemetry, UI, and agent layers modular. Prefer TDD for config, adapters, telemetry, actions, policies, and storage.

Verify: After each task run focused tests and relevant smoke checks. Final evidence must include changed files, tests, runtime smoke, UI/agent evidence where applicable, open risks, and updated `.vault/goals/goal-firered-runtime-2026-06-04/progress.md`.

Iterate/done/stop: Execute the task graph in order, update progress after meaningful actions, capture decisions/solutions/encounters when durable, and stop for approval boundaries or repeated blockers. Done only when linked plan success criteria pass or the user explicitly defers remaining plans.
```
