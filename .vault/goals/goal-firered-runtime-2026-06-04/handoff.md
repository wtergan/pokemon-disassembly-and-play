# Goal Handoff

## Resume Here

- Active goal run: `.vault/goals/goal-firered-runtime-2026-06-04/`
- Current milestone/task: M1.T1
- Current branch/worktree: `/home/gilgames/Code/pokemon-disassembly-and-play` is not yet a git repository.
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

- The project is planning-complete enough to start execution.
- The workspace contains `.vault` operational memory and no production runtime source yet.
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

- mGBA launch and Lua/socket IPC from WSL/Windows may need environment-specific handling.
- The workspace bootstrap must preserve `.vault` while bringing in `pret/pokefirered` source.
- `pret/pokefirered` build toolchain may need setup before symbol generation works.
- FireRed telemetry must avoid overclaiming uncertain pointer, encrypted, or mode state.

## Next Action

Execute M1.T1 from `.vault/goals/goal-firered-runtime-2026-06-04/task-graph.md`: bootstrap `pret/pokefirered` source into the current workspace while preserving `.vault`, then validate that `Makefile` and `include/global.h` exist and no ROM files were imported.
