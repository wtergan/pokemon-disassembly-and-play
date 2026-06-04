---
date: 2026-06-04
status: accepted
related_plan: ".vault/plans/001-firered-runtime-spike-2026-06-04.md"
---

# ADR: mGBA First Runtime Bridge

## Context

The project needs a dedicated emulator bridge for a Windows-friendly programmable
runtime inspired by `Dimillian/Pocodex`, but targeting `pret/pokefirered` and the
user's owned FireRed/LeafGreen Rev 1 ROMs.

The previous decision established that the first implementation will use a
separate runtime-owned emulator instance rather than attaching to the user's
active Mesen2 sessions. That removes Mesen2's strongest advantage, which was
reuse of the current play setup, and shifts the bridge choice toward automation
quality, GBA support, scripting, memory access, input control, screenshots, and
save-state handling.

## Decision

Use mGBA as the first emulator bridge target for the dedicated FireRed Rev 1
runtime spike.

Keep BizHawk as the explicit fallback if mGBA's Windows launch, Lua/socket IPC,
screenshot capture, or frame/input control proves awkward enough to slow the
first spike.

## Drivers

- mGBA is directly focused on Game Boy Advance emulation.
- mGBA exposes Lua primitives for memory reads, memory writes, frame control,
  screenshots, key input, and save states.
- mGBA can keep the runtime concept cross-platform even though the first
  environment is Windows/WSL.
- The runtime architecture can isolate the bridge behind an emulator adapter, so
  choosing mGBA first does not hard-code the project to mGBA forever.
- The first spike needs a narrow prove-out loop: launch FireRed Rev 1, capture a
  frame, press a button, read pointer-backed telemetry, and serve that through
  Pocodex-style HTTP endpoints.

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|---|---|---|---|
| Mesen2-first bridge | Matches the user's current emulator setup; could be useful for later live-session integrations. | Higher Windows GUI coupling; less clear scripting documentation for this use; risks interfering with real play sessions if reused. | The project has committed to a separate dedicated runtime instance, so Mesen2's main advantage is no longer decisive. |
| BizHawk-first bridge | Mature scripting and TAS ecosystem; Windows-native; GBA via mGBA core; strong Lua launch story. | Adds another emulator stack; more Windows-centric; may obscure direct GBA/mGBA behavior behind BizHawk layers. | Strong fallback, but mGBA is the cleaner first fit for a GBA-specific runtime adapter. |
| Abstract bridge only, no first target | Avoids early commitment and keeps all options open. | Delays the first real validation loop; risks designing abstractions without emulator evidence. | The first feature plan needs one concrete emulator to validate launch, input, screenshot, memory, and save-state behavior. |

## Consequences

- The first feature plan should target an `mgba_bridge` adapter before any
  BizHawk or Mesen2 adapters.
- The runtime should still define a small emulator interface so fallback remains
  practical.
- The first spike must explicitly validate mGBA launch behavior from WSL/Windows,
  Lua or socket IPC shape, screenshot capture, frame stepping, button input, and
  EWRAM/IWRAM reads.
- BizHawk remains the fallback if mGBA cannot provide reliable automation quickly.
- Mesen2 can remain a future optional integration for attaching to manual play,
  but it is outside the first implementation scope.

## Verification

The decision remains valid if the first spike can prove:

- FireRed Rev 1 launches in a dedicated mGBA instance from a configured local ROM
  path.
- The runtime can capture a frame or screenshot for `/snapshot`.
- The runtime can send button input and observe state changes.
- The runtime can read enough GBA memory to resolve `gSaveBlock1Ptr`,
  `gSaveBlock2Ptr`, map/location, and player position telemetry.
- The runtime can isolate save states and traces from the user's normal emulator
  saves.

If these fail due to mGBA launch or IPC limitations, the plan should switch to
the BizHawk fallback while keeping the same runtime/game adapter boundaries.

## Related Artifacts

- Planned feature plan: `.vault/plans/001-firered-runtime-spike-2026-06-04.md`
- Research: `.vault/research/pocodex-pokefirered-runtime-2026-06-03.md`
- Decision: `.vault/decisions/dedicated-runtime-emulator-instance-2026-06-03.md`
