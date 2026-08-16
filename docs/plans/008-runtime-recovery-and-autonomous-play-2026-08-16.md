# Runtime recovery and autonomous play

Status: Verified bounded acceptance. Observation date: 2026-08-16 (America/New_York).

## Outcome and scope

Resumed the unfinished July 9 implementation and proved that a model planner can play the owned FireRed Rev 1 through the intro into the first controllable overworld, followed by a state-verified movement. Simplified documentation and tests and restored emulator launch access.

ROMs, normal saves, generated symbols/binaries, private configuration and credentials stay outside Git. Retain the mGBA-first design and runtime-owned saves. Full campaign completion, battles and LeafGreen autonomous progression are outside the verified result.

## Recovered context and important files

- Main baseline: `d4b4912`, July 9, 2026. Reused the existing `firered-semantic-progression` worktree and its generated Rev 1 symbols.
- Original primary `.vault` notes, untracked July handoff/images and pending source patch are preserved under the primary Git directory's `recovery-2026-08-16/`. The original primary archive was compared byte-for-byte before cleanup; Git also retains all previously tracked legacy notes.
- Current workflow uses `docs/PLAN.md`, concise feature plans and useful visuals. Earlier plans/decisions are condensed in `docs/runtime-history.md` and plan 007.
- Runtime boundaries: `storage.py`, `runtime_factory.py`, `emulators/mgba_bridge.*`, `emulators/windows_process.py`.
- State proof: `games/firered/{memory,map_data,mode,save_blocks,telemetry}.py`, `objective_scoring.py`.
- Model path: `codex_client.py`, `agent_service.py`, `objective_runner.py`; browser requests under `static/`.
- Reusable verification: `verify_runtime.py`, `.agents/skills/verify-pokemon-runtime/`, and `docs/visuals/runtime-feature-map.html`. This applies the installed Poteto-inspired verification generator to this project's actual behavior and evidence.

## Acceptance and completed work

- [x] Read legacy handoff, pending code, relevant Vault emulation notes and current dotfiles workflow.
- [x] Review/recover symbol validation and isolated battery/save-state changes.
- [x] Verify owned ROM, source build, live bridge, input, memory, telemetry and screenshots.
- [x] Model-driven intro and checkpointed semantic transition with local evidence.
- [x] Reusable bounded verification recipe; fix demonstrated defects.
- [x] Migrate useful legacy context into concise docs and retain original material locally.
- [x] Consolidate test files while retaining meaningful existing behavior coverage.
- [x] Create/verify emulator launch shortcuts and all seven taskbar pins.
- [x] Native-session review of each delegated result.
- [x] Full suite, compile and diff checks; each source milestone tested as its own tree.

## Verified behavior and corrections

Mounted the attached Windows T: volume in WSL without relocating the library. Rebuilding FireRed Rev 1 produced SHA-1 `dd5945db9b930750cb39d00c84da8571feebf417`, exactly matching the owned ROM. LeafGreen Rev 1 matched `7862c67bdecbe21d1d69ce082ce34327e1c6ed5e`.

The live KEYINPUT probe failed before correction: A produced `0x2`. mGBA's key API expects indices, so correcting the mapping produced `0x1`; all ten physical inputs passed afterward. Memory now uses bounded per-observation pages instead of thousands of scalar bridge requests. Source-backed guards normalize Thumb callbacks, require `CB2_Overworld` for field mode, use palette fade byte 7, validate complete EWRAM SaveBlocks and reject out-of-layout coordinates. Explicit source map names now resolve all 425 maps; the former guessed IDs resolved only 249 and lost numeric floor names. The missing bedroom map was reproduced with a failing regression before correction.

A Windows ownership helper records the actual launched PID and creation time; closing the Linux interop launcher alone left GUI children. Repeated real verifier runs now close their own Windows instance. FireRed and LeafGreen each passed all ten input bits, checkpoint save/reload and normal-save preservation. Both normal `.sav` SHA-256 values remained `b5a41c3758763bbec72769fab4a2533bf2db0b6312d93d25a695f9e4b9e02260`.

The app-server planner works with the desktop sign-in through the existing CLI wrapper's `CODEX_CLI_HOME` option. The separate WSL CLI sign-in returned workspace-discovery 401. No credentials were copied or printed. The local executable wrapper and configuration are ignored. Planner turns receive a screenshot plus structured state, advertised bounded actions and the current objective; private local paths are omitted.

The planner completed 35 bounded decisions through intro/naming into the starting bedroom after native startup navigation reached Oak's introduction. An initial naming attempt stopped honestly under an overly restrictive instruction. With map lookup corrected, the retained model-created `first_overworld` checkpoint reported exact `CB2_Overworld`, high-confidence field mode, `MAP_PALLET_TOWN_PLAYERS_HOUSE_2F`, `(6,6)` within a 12x9 layout. A fresh model-driven movement objective then changed `(6,6)` to `(5,6)` in one step; all six conjunctive semantic checks passed. No game-memory writes or injected saves were used. Frame counts are diagnostic only.

A fresh browser context independently exercised **Run** end to end and displayed `semantic: success: 1 step`, field/high and held:none. Browser model requests now have a separate bounded inference timeout, and every new objective includes its starting state. At 390px the deck and feature map had no horizontal overflow; the 240px live image loaded. Manual A press/release and UI Save/Load passed. Full accessibility and every deck interaction were not audited.

## Evidence and reproducible checks

Local ignored evidence under `.runtime-logs/recovery-2026-08-16/` includes `movement-objective.json`, `movement-result.json`, `browser-run-proof.txt`, `browser-run.txt`, `native-pin-audit.json`, `build.log`, Windows launch/pin checks and screenshots. `.runtime-logs/verification/report.json` and the LeafGreen report retain real doctor results. These links are local evidence and are unavailable in a clean clone; the committed recipe regenerates them.

```sh
.venv/bin/python -m pytest -q tools/runtime/tests
.venv/bin/python -m compileall -q tools/runtime
.venv/bin/python -m tools.runtime.verify_runtime --config tools/runtime/runtime.local.toml --output .runtime-logs/verification
git diff --check
```

Full suite: **123 passed**. The original 93 cases remain represented in seven responsibility modules; four focused modules cover the observed memory/telemetry/planner/semantic defects. A browser timeout regression is included in the HTTP module. Each selected source milestone was exported and tested independently: 93, 107, 122, 123 and 123 cases respectively. No broad new test infrastructure was added.

All seven canonical emulator targets exist. Fourteen per-user Desktop/Start Menu links passed target checks, all seven taskbar pins were inspected independently, and launch checks confirmed actual windows. The shortcut helper is idempotent and backs up repaired links. An obsolete protected Public Desktop PCSX2 link still points to its old missing path; per-user links work, and no protected shortcut was force-replaced.

## Risks and continuation

A ROM mismatch, save escape, invalid symbols or non-fast-forward remote stops the dependent operation. Local archive and original patches support rollback; normal saves are never recovery targets. Original legacy content remains in Git history. Full story/battle progression and LeafGreen semantic play require new observed evidence.

For local continuation, use the ignored runtime config and desktop-backed planner launcher, start `python -m tools.runtime.server --config ...` as documented in the runtime guide, and load the retained `first_overworld` checkpoint before the exact movement recipe. The local control deck listens on `http://127.0.0.1:8795/`. Keep one runtime per bridge port and close its owner before running the doctor.

## House-exit follow-up

Verification in progress on 2026-08-16: use the existing runtime and GPT-5.6 Luna xhigh planner to leave the upstairs bedroom, descend the stairs and exit into Pallet Town. Acceptance requires high-confidence field telemetry on `MAP_PALLET_TOWN` at `(6,8)`, an observed transition through the ground floor, a retained screenshot/trace, and unchanged normal-save fingerprints. Use only advertised actions and runtime-owned checkpoints.
