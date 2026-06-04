---
date: 2026-06-04
status: accepted
related_plan: ".vault/plans/001-firered-runtime-spike-2026-06-04.md"
---

# ADR: First Spike Scope Boundaries

## Context

The project has resolved the broad runtime direction: FireRed Rev 1 first, a
separate dedicated emulator instance, and mGBA as the first emulator bridge.
Several planning choices remained open and would otherwise slow the first goal
execution loop.

## Decision

For the first spike:

- Bootstrap the current empty workspace from `pret/pokefirered` before adding runtime files.
- Use the user's existing owned FireRed Rev 1 ROM path from `C:\Emulation` through ignored local configuration.
- Launch a visible dedicated mGBA window by default, because visible state is easier to debug during the first bridge validation.
- Keep initial telemetry narrow: frame count, ROM identity/hash, `gSaveBlock1Ptr`, `gSaveBlock2Ptr`, map group/number, and player/camera coordinates.
- Defer party, bag, battle, menu, text, objective, and LeafGreen support to later plans.

## Drivers

- The workspace currently contains only `.vault`, so implementation needs a base source tree before runtime work.
- Directly referencing the owned ROM avoids duplicating copyrighted ROM data in the repo.
- A visible emulator window reduces uncertainty while mGBA launch and IPC behavior are still being proven.
- Narrow telemetry gives the first spike a testable finish line without pretending Gen 3 memory decoding is simple.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|---|---|---|---|
| Clone or fork later, start with runtime files only | Faster initial file creation. | Runtime would lack the source, symbol, map, and build context it needs. | The runtime is meant to be `pret/pokefirered`-based, not a detached tool. |
| Copy the ROM into a repo-local cache | Stable path and easier config. | Higher risk of accidental git inclusion and unclear ownership boundary. | Use direct local path first; add an ignored cache only if path stability becomes a real issue. |
| Headless mGBA first | Cleaner automation shape. | Harder to debug launch, screenshot, and input issues during the first spike. | Headless can be a later mode after the bridge is proven. |
| Include party/bag/battle telemetry in plan 001 | More impressive first demo. | Expands scope into save-block decoding and encrypted fields before the emulator bridge is stable. | Plan 002 owns richer telemetry. |

## Consequences

- Plan 001 must include a bootstrap step before runtime implementation.
- Local config and `.gitignore` rules are part of the first spike, because ROMs and runtime saves must stay outside git.
- The first mGBA bridge may be visually interactive during development, even though later automation can become headless.
- Completion of plan 001 is intentionally modest but meaningful: launch, frame, button, memory read, basic HTTP surface.

## Verification

This decision remains valid if plan 001 can prove the narrow runtime loop without
touching the user's active Mesen2 sessions or committing ROM/savestate data.

If visible mGBA cannot be automated reliably, capture an encounter and either
switch to BizHawk or narrow the bridge strategy before continuing.

## Related Artifacts

- Plan: `.vault/plans/001-firered-runtime-spike-2026-06-04.md`
- Research: `.vault/research/pocodex-pokefirered-runtime-2026-06-03.md`
- Decision: `.vault/decisions/dedicated-runtime-emulator-instance-2026-06-03.md`
- Decision: `.vault/decisions/mgba-first-runtime-bridge-2026-06-04.md`
