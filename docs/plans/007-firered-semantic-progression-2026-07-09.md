# FireRed Semantic Progression

Status: First-overworld acceptance achieved on 2026-08-16; broader semantic skills deferred. The July 9 handoff was blocked before live telemetry. [Plan 008](008-runtime-recovery-and-autonomous-play-2026-08-16.md) records the recovery and actual verification evidence.

## Outcome and boundaries

Prove FireRed Rev 1 game state from source-backed symbols, then build bounded
autonomous actions that verify state transitions. The first gameplay acceptance
state is the first controllable overworld with a named map, player coordinates,
and `field` mode.

- Use the WSL-native toolchain and a ROM whose hash matches the FireRed Rev 1
  profile. Reject missing, incomplete, or implausible symbol data.
- Run a fresh game only with a runtime-owned disposable battery-save workspace;
  never use the normal play save.
- Treat screenshots as supporting evidence. Input counts, frames, and images do
  not prove semantic progress.
- Keep scope to FireRed Rev 1 and bounded play. Keep ROMs, saves, generated
  symbols, emulator binaries, local configuration, and credentials out of Git.
- Keep the first UI pass utilitarian. The mGBA Scripting window remains a bridge
  console; UI polish follows telemetry proof.

## Context and approach

The runtime already has a dedicated mGBA bridge, FireRed telemetry readers,
symbol discovery, action policy, checkpoints, and an objective runner. The
source build must produce the Rev 1 symbols before those readers can establish
live game state. The expected target SHA-1 is
`dd5945db9b930750cb39d00c84da8571feebf417`.

Relevant source and verification paths:

- Build and symbol validation: `Makefile`,
  `tools/runtime/games/firered/symbols.py`, and
  `tools/runtime/runtime_factory.py`.
- Live state decoding: `tools/runtime/games/firered/telemetry.py` and
  `tools/runtime/games/firered/mode.py`.
- Disposable saves and bridge startup: `tools/runtime/config.py`,
  `tools/runtime/storage.py`, and `tools/runtime/emulators/mgba_bridge.py`.
- Bounded agent actions and recovery: `tools/runtime/interaction_policy.py`
  and `tools/runtime/objective_runner.py`.
- Behavior coverage: `tools/runtime/tests/`, especially the symbol,
  save-isolation, FireRed telemetry, and objective tests.

After live telemetry is proven, add semantic skills in small steps: advance
dialogue, dismiss menus, walk to a tile, then reach a map. Each action needs a
bounded retry budget, a before/after state check, and runtime-owned checkpoint
recovery. Screenshot handling and web-deck polish follow those state contracts.

## July 9 handoff evidence

- [x] **Toolchain and symbols.** The July 9 handoff records a WSL user-local
  binutils toolchain, the repository's `agbcc` compiler, and a successful
  `make -j4 syms GAME_VERSION=FIRERED GAME_REVISION=1` build. It reports 50,123
  symbols, required globals, and an owned ROM hash matching the Rev 1 profile.
- [x] **Save isolation.** The handoff records a disposable ROM and battery save
  under the target-scoped Windows mGBA cache, plus a staged `fresh_boot.ss`.
  Nine focused safety tests were reported passing at that point.
- [ ] **First-overworld telemetry.** Not proven in the July 9 handoff. The
  subsequent launch attempts timed out before the Windows mGBA Lua reverse
  client connected. A primitive-only bridge probe had succeeded earlier, but
  it did not prove gameplay telemetry.
- [ ] **Semantic skills.** No first-overworld transition or state-verified
  gameplay skill is recorded as complete.
- [ ] **Screenshot assistance and UI polish.** Deferred until telemetry and
  skill outcomes are state-backed.

## Current verification and continuation

Recovery in plan 008 completed the initial acceptance: model-driven intro,
high-confidence field telemetry on a named bedroom map at `(6,6)`, followed by
a one-step Luna movement to `(5,6)` verified by the conjunctive semantic scorer.
The browser Run path also passed. Full runtime suite: 123 passing cases.

Screenshot-assisted planning is implemented. Reusable dialogue/menu/route
macros, battles and broad story progression remain deferred. Use the committed
verification recipe and current runtime guide for fresh checks; the unchecked
July handoff entries above describe the earlier evidence boundary.
