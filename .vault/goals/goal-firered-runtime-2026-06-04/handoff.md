# Goal Handoff

## Resume Here

- Active goal run: `.vault/goals/goal-firered-runtime-2026-06-04/`
- Current milestone/task: complete
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
- No generated `pokefirered_rev1.sym` exists yet, so real runtime telemetry reports ROM identity plus missing-symbol state until the toolchain can generate symbols. The runtime now auto-discovers the file when it appears at the repo root or `build/firered_rev1/`.
- Plan 001 browser verification found and fixed mGBA socket concurrency by serializing bridge requests.
- Plan 001 post-review fixes also added runtime close support, unique snapshot filenames, memory-read frame updates, malformed action validation, and basename-only symbol source telemetry.
- M2.T2 is complete: `telemetry.save` now includes player identity bytes, play time, encrypted money, coins, bag pocket counts, compact flag/var summaries, and checksum-validated party member summaries.
- M2.T3 is complete: `telemetry.location.map` now includes map metadata, layout dimensions/paths, connections, warps, and coordinate context when map assets are available.
- M2.T4 is complete: `telemetry.save.player.name` and party member `nickname` values decode through `charmap.txt`, and `telemetry.mode` classifies field, battle, menu, dialogue_textbox, transition_loading, and unknown with confidence plus `gMain`/`gPaletteFade`/`gTasks` evidence.
- M2.T5 and plan 002 are complete at fixture/API level: `/telemetry` now normalizes through schema v1 with `target`, `runtime`, explicit unavailable sections, and `capabilities` flags. Live decoded-state smoke still needs `pokefirered_rev1.sym` to be generated.
- M3.T1 is complete: static UI now imports `api-client.js`, runtime API requests have timeouts and JSON error detail handling, and periodic refreshes are single-flight.
- M3.T2 is complete: controls now send press/release for pointer and keyboard holds, show held-button state, maintain `aria-pressed`, and serialize action requests.
- M3.T3 is complete: telemetry panel formatting lives in `telemetry-format.js`; the deck renders mode, map, player, camera, party, bag, flags/vars, symbols, raw JSON, and formatted trace labels.
- M3.T4 is complete: runtime state slots are contained under `state_dir`, exposed through `/states` endpoints, and rendered by the state panel.
- M3.T5 and plan 003 are complete: desktop/mobile screenshots and Playwright interaction smoke passed against the fake runtime. `.git` is writable again as of the full-access permission change, so commits can proceed.
- M4.T1 is complete: `/agent_context` now returns a compact privacy-safe planner context with target/runtime/state summaries, objective placeholder, quick slot metadata, allowed action affordances, capped traces, rules, and output contract. Tests cover POSIX/Windows path omission, hash omission, trace caps, and safe action affordances.
- M4.T2 is complete: `RuntimeCore.execute_agent_action()` validates advertised agent action IDs, rejects unknown fields and mismatched button/frame/slot overrides, traces proposed/validated/rejected/failed/executed states, and executes bounded tap/wait/save/load/inspect/stop behavior. Durable boundary decision: `.vault/decisions/agent-action-policy-boundaries-2026-06-04.md`.
- M4.T3 is complete: `AgentService` can run one planner step through disabled/fake/app-server clients; optional `[agent]` config defaults to disabled, fake mode is wired for tests, and `codex app-server --stdio` initialize was probed successfully. Durable default decision: `.vault/decisions/agent-client-disabled-default-2026-06-04.md`.
- M4.T4 is complete: `ObjectiveRunner` runs short capped objectives with quick checkpoint/recovery hooks, explicit stop handling, context deltas, and success criteria that must match observed context. Durable pattern: `.vault/solutions/codex-agent-loop-solution-2026-06-04.md`.
- M4.T5 and plan 004 are complete at fake-runtime/API/browser level: agent endpoints and the Agent panel are implemented, live endpoint smoke passed, and desktop/mobile browser screenshots were captured. Real mGBA objective smoke remains a later environment check.
- M5.T1 is complete: target profiles now cover FireRed Rev 1 and LeafGreen Rev 1, config verifies ROM SHA-1 by default, fixture configs can opt out with `verify_hash = false`, and wrong-hash/LeafGreen profile tests pass. Durable decision: `.vault/decisions/target-profile-hash-verification-2026-06-04.md`.
- M5.T2 is complete: runtime factory selects FireRed or LeafGreen telemetry readers from target profiles, LeafGreen publishes `target.game = leafgreen`, and profile-based symbol discovery finds `pokeleafgreen_rev1.sym`.
- M5.T3 is complete: runtime-owned storage roots are scoped by target profile key for states, traces, logs, screenshots, and cache paths; factory uses scoped state and screenshot paths. Durable pattern: `.vault/solutions/leafgreen-support-and-hardening-solution-2026-06-04.md`.
- M5.T4 is complete: current mGBA evidence remains sufficient, so no BizHawk adapter was added. Durable decision: `.vault/decisions/bizhawk-fallback-not-needed-2026-06-04.md`.
- M5.T5 and plan 005 are complete: top-level and runtime docs cover Windows/WSL, mGBA config, ROM config, symbols, runtime artifacts, safety, verification, and troubleshooting. FireRed and LeafGreen real-runtime smokes passed for health, snapshot, action, and basic telemetry.
- Current local venv has stale `starlette 1.2.1`; repo requirements now pin `starlette<1.0`, but DNS prevented re-sync. Endpoint tests skip in this stale env rather than hanging.

## Next Action

Start a new feature plan for any follow-up work. Good candidates are symbol-generation automation, real mGBA objective smoke with the agent loop, or support for additional target revisions.

<!-- codex-vault-memory-advisor:start -->
## Automated Handoff Snapshot

- Updated: 2026-06-04T12:10:55-04:00
- Event: `goal complete`
- Repo: `/home/gilgames/Code/pokemon-disassembly-and-play`
- Branch: `main`
- Active goal: `.vault/goals/goal-firered-runtime-2026-06-04/`
- Active plan: `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md`
- Changed files: 8
  - `.vault/PLAN.md`
  - `.vault/decisions/bizhawk-fallback-not-needed-2026-06-04.md`
  - `.vault/goals/goal-firered-runtime-2026-06-04/handoff.md`
  - `.vault/goals/goal-firered-runtime-2026-06-04/progress.md`
  - `.vault/goals/goal-firered-runtime-2026-06-04/task-graph.md`
  - `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md`
  - `README.md`
  - `tools/runtime/README.md`
- Last progress: Plans 001 through 005 complete.

### Capture Queue
- None.
<!-- codex-vault-memory-advisor:end -->
