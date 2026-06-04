---
date: 2026-06-04
status: accepted
related_plan: .vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md
---

# BizHawk Fallback Not Needed Yet

## Decision

Do not implement a BizHawk fallback adapter during plan 005.

Keep BizHawk as a documented future fallback behind the existing
`EmulatorBridge` contract, but continue with mGBA as the only implemented
runtime bridge until new evidence shows mGBA is insufficient.

## Evidence

- Plan 001 proved real Windows mGBA launch from WSL using the official dev build,
  `--script`, Lua-client reverse socket mode, and `realtime_wait` frame advance.
- The real smoke covered health, ROM memory reads, button input, frame
  progression, and screenshot capture.
- The initial WSL/socket issues were understood and captured in
  `.vault/encounters/mgba-wsl-bridge-2026-06-04.md`.
- The browser concurrency issue was fixed by serializing line-protocol bridge
  requests and captured in `.vault/encounters/mgba-socket-concurrency-2026-06-04.md`.
- Later plans built API, web UI, telemetry, savestate, and agent-loop behavior on
  the same bridge boundary without requiring bridge redesign.

## Consequences

- No `bizhawk_bridge.py` is added in this milestone.
- Adapter contract tests remain focused on the mGBA implementation and fake
  bridge until a second implementation exists.
- If mGBA later fails on launch, Lua IPC, screenshots, savestates, memory reads,
  or deterministic input in a way that cannot be contained locally, capture a new
  encounter first and then add BizHawk behind `tools/runtime/emulators/base.py`.
