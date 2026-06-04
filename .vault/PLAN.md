---
project: "Pokemon Disassembly And Play"
date: "2026-06-04"
status: "Active"
progress: 32
---

# Project Roadmap

`PLAN.md` is the project-level roadmap and status index. Keep implementation
detail in `.vault/plans/`.

## Current State

- The workspace at `/home/gilgames/Code/pokemon-disassembly-and-play` has been bootstrapped from `pret/pokefirered` and initialized as a git repository on `main`.
- The project will build a Windows-friendly programmable runtime inspired by `Dimillian/Pocodex`, but based on `pret/pokefirered` and the user's owned FireRed/LeafGreen Rev 1 ROMs.
- The committed first implementation path is FireRed Rev 1, a separate dedicated runtime emulator instance, mGBA as the first bridge target, and BizHawk as the fallback.
- Real Windows mGBA bridge proof is complete using the official dev build, Lua-client reverse socket mode, WSLENV exports, Windows-local script/screenshot staging, and real-time frame waits.
- Active goal overlay: `.vault/goals/goal-firered-runtime-2026-06-04/`.

## Active Plans

| Feature Plan | Feature | Status | Next Action |
|---|---|---|---|
| `.vault/plans/001-firered-runtime-spike-2026-06-04.md` | Bootstrap the `pret/pokefirered` workspace and prove mGBA launch, screenshot, input, and minimal telemetry. | In Progress | Execute M1.T5: minimal FireRed telemetry. |
| `.vault/plans/002-firered-telemetry-adapter-2026-06-04.md` | Expand FireRed symbol, save block, map, text, mode, party, bag, and event telemetry. | Planned | Start after plan 001 proves mGBA memory reads. |
| `.vault/plans/003-runtime-web-control-deck-2026-06-04.md` | Build the Pocodex-style browser control deck, trace UX, manual controls, and save-state surfaces. | Planned | Start after stable `/snapshot`, `/telemetry`, and `/action` APIs exist. |
| `.vault/plans/004-codex-agent-loop-2026-06-04.md` | Add planner-safe Codex agent integration, `agent_context`, action policy, and objective loop. | Planned | Start after manual runtime controls and traces are reliable. |
| `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md` | Add LeafGreen Rev 1 support, fallback bridge checks, packaging/docs, and regression hardening. | Planned | Start after FireRed runtime and agent loop are stable. |

## Active Goal Runs

Use this section only when native `/goal` or `$lfg` is coordinating work across
time or across multiple feature plans.

| Goal Run | Coordinates | Status | Next Action |
|---|---|---|---|
| `.vault/goals/goal-firered-runtime-2026-06-04/` | Plans 001 through 005 | Ready | Start native `/goal` from `goal.md`, then follow `task-graph.md` and `handoff.md`. |

## Primary Goals

1. Build a local programmable runtime that can launch, observe, control, and instrument Pokemon FireRed Rev 1 from the user's owned ROM.
2. Preserve a Pocodex-like architecture: HTTP runtime API, browser control deck, action traces, telemetry, and Codex agent loop.
3. Keep emulator, game telemetry, UI, and agent layers modular so LeafGreen and alternate emulator bridges can be added without rewriting the runtime.

## Success Criteria

- [ ] The workspace is bootstrapped from `pret/pokefirered` without committing ROMs or user emulator saves.
- [ ] A dedicated mGBA runtime instance can launch FireRed Rev 1 from ignored local configuration.
- [ ] `/health`, `/snapshot`, `/telemetry`, `/action`, and `/agent_context` exist with tests around public behavior.
- [ ] The web UI shows a live frame, manual controls, current telemetry, savestates, traces, and agent state.
- [ ] The runtime decodes FireRed map/player/mode and core inventory/party/event state from symbols or documented offsets.
- [ ] The Codex agent loop can observe, choose validated actions, execute them, and verify results without uncontrolled inputs.
- [ ] LeafGreen Rev 1 can be configured and smoke-tested after FireRed stabilizes.

## Architecture Snapshot

```mermaid
graph TD
    A["Owned ROM path under C:\\Emulation"] --> B["Ignored runtime config"]
    B --> C["WSL FastAPI runtime"]
    C --> D["mGBA emulator adapter"]
    D --> E["Dedicated mGBA process"]
    E --> F["FireRed Rev 1 game state"]
    F --> G["FireRed telemetry adapter"]
    G --> C
    C --> H["Pocodex-style web control deck"]
    C --> I["Trace recorder and savestates"]
    C --> J["Codex agent service"]
    J --> K["Validated action policy"]
    K --> C
```

ASCII fallback:

```text
Owned ROM path -> ignored config -> WSL FastAPI runtime -> mGBA adapter -> dedicated mGBA
                                  -> FireRed telemetry -> web UI / traces / Codex agent
```

## Decision Index

| Decision | Rationale | Date | Link |
|:---------|:----------|:-----|:-----|
| Dedicated runtime emulator instance | Protect real play sessions and make automation reproducible. | 2026-06-03 | `.vault/decisions/dedicated-runtime-emulator-instance-2026-06-03.md` |
| mGBA first runtime bridge | Direct GBA fit with Lua memory/input/savestate primitives; BizHawk remains fallback. | 2026-06-04 | `.vault/decisions/mgba-first-runtime-bridge-2026-06-04.md` |
| First-spike scope boundaries | Resolve open planning choices before goal execution begins. | 2026-06-04 | `.vault/decisions/first-spike-scope-boundaries-2026-06-04.md` |

## Risk Register

| Risk | Impact | Likelihood | Mitigation | Owner |
|:-----|:-------|:-----------|:-----------|:------|
| mGBA launch or Lua/socket IPC from WSL/Windows is awkward. | Medium | Low | Proven path uses dev mGBA, Lua-client reverse socket mode, WSLENV exports, staged Windows paths, and real-time frame waits; keep BizHawk fallback only for new evidence. | implementer |
| `pret/pokefirered` build toolchain is missing or slow to configure. | Medium | Medium | Use existing reference clone for source evidence, verify owned ROM hash first, and document build blockers in `.vault/encounters/`. | implementer |
| FireRed state decoding is more pointer/encryption dependent than expected. | High | Medium | Keep plan 001 telemetry narrow, then use plan 002 for symbol and save-block validation. | implementer |
| Agent loop sends unsafe or noisy inputs. | High | Medium | Gate plan 004 behind validated action policy, cooldowns, trace review, and deterministic savestates. | reviewer/security |
| ROMs or saves accidentally enter git. | High | Low | Use ignored local config and explicit plan checks before committing or packaging. | security |

## Knowledge Index

- Research: `.vault/research/pocodex-pokefirered-runtime-2026-06-03.md`
- Decisions: `.vault/decisions/`
- Solutions: `.vault/solutions/`
- Encounters: `.vault/encounters/`
- Goal run: `.vault/goals/goal-firered-runtime-2026-06-04/`
- Visual companions: `.vault/visuals/`

## Maintenance Notes

- Update this file when a feature plan is created, completed, paused, or replaced.
- Promote durable choices into `.vault/decisions/`.
- Capture reusable fixes in `.vault/solutions/` and recurring blockers in `.vault/encounters/`.
- During native `/goal` execution, update `.vault/goals/goal-firered-runtime-2026-06-04/progress.md` after each meaningful implementation or validation step.
