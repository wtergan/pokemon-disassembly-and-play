# Goal Handoff

## Resume Here

- Active goal run: `.vault/goals/goal-firered-runtime-2026-06-04/`
- Current milestone/task: M2.T1
- Current branch/worktree: `/home/gilgames/Code/pokemon-disassembly-and-play` on git branch `main`.
- Read first:
  - `.vault/goals/goal-firered-runtime-2026-06-04/progress.md`
  - `.vault/goals/goal-firered-runtime-2026-06-04/task-graph.md`
  - `.vault/PLAN.md`
  - `.vault/plans/001-firered-runtime-spike-2026-06-04.md`
  - `.vault/research/pocodex-pokefirered-runtime-2026-06-03.md`
  - `.vault/decisions/dedicated-runtime-emulator-instance-2026-06-03.md`
  - `.vault/decisions/mgba-first-runtime-bridge-2026-06-04.md`
  - `.vault/decisions/first-spike-scope-boundaries-2026-06-04.md`

## Latest Known State

- The project has started execution.
- The workspace now contains `pret/pokefirered` source plus `.vault` operational memory.
- Reference clones exist under `/home/gilgames/Code/github-clones/`:
  - `Dimillian-Pocodex`
  - `pret-pokefirered`
- The user's FireRed Rev 1 and LeafGreen Rev 1 ROM hashes matched `pret/pokefirered` targets during prior research.
- Accepted direction:
  - FireRed Rev 1 first
  - LeafGreen Rev 1 later
  - dedicated emulator instance
  - mGBA first
  - BizHawk fallback only with evidence
  - no ROMs/saves/local config in git

## Open Risks

- FireRed telemetry must avoid overclaiming uncertain pointer, encrypted, or mode state.
- `pret/pokefirered` build toolchain may need setup before symbol generation works.
- mGBA's live GUI bridge cannot call `emu:runFrame()` from the socket callback; Windows/WSL runtime config must use `frame_advance_mode = "realtime_wait"`.
- No generated `pokefirered_rev1.sym` exists yet, so real runtime telemetry reports ROM identity plus missing-symbol state until the toolchain can generate symbols.
- Plan 001 browser verification found and fixed mGBA socket concurrency by serializing bridge requests.

## Next Action

Execute M2.T1 from `.vault/goals/goal-firered-runtime-2026-06-04/task-graph.md`: stabilize generated symbol resolution and decide how the runtime should obtain `pokefirered_rev1.sym` in this environment.

<!-- codex-vault-memory-advisor:start -->
## Automated Handoff Snapshot

- Updated: 2026-06-04T03:31:02-04:00
- Event: `precompact`
- Repo: `/home/gilgames/Code/pokemon-disassembly-and-play`
- Branch: `main`
- Active goal: `.vault/goals/goal-firered-runtime-2026-06-04/`
- Active plan: `.vault/plans/001-firered-runtime-spike-2026-06-04.md`
- Changed files: 4
  - `tools/runtime/emulators/mgba_bridge.lua`
  - `tools/runtime/emulators/mgba_bridge.py`
  - `tools/runtime/tests/test_mgba_launch_command_should_include_script_and_rom.py`
  - `tools/runtime/tests/test_mgba_socket_bridge_should_parse_socket_responses.py`
- Last progress: - Encounters: none yet.

### Capture Queue
- Solution candidate: progress suggests a fix/resolution with production changes, but no `.vault/solutions/` file changed.
<!-- codex-vault-memory-advisor:end -->
