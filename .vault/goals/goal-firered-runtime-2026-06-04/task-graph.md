# Goal Task Graph

## Milestones

### M1: FireRed Runtime Spike

- Goal: Bootstrap the source tree and prove a dedicated mGBA-backed FireRed Rev 1 runtime loop.
- Depends on: Planning complete
- Validation level: L1 smoke plus focused Python tests
- Review gate: pre-merge and post-smoke

| Task ID | Plan | Task | State | Depends On | Owner/Lane | Validation |
|---|---|---|---|---|---|---|
| M1.T1 | `.vault/plans/001-firered-runtime-spike-2026-06-04.md` | Bootstrap `pret/pokefirered` source tree while preserving `.vault`. | complete | None | implementer | `test -f Makefile`; `test -f include/global.h`; no owned ROMs imported |
| M1.T2 | `.vault/plans/001-firered-runtime-spike-2026-06-04.md` | Add ignored runtime config and local artifact boundaries. | complete | M1.T1 | implementer/security | Config tests and git status review |
| M1.T3 | `.vault/plans/001-firered-runtime-spike-2026-06-04.md` | Add Python runtime skeleton and fake emulator contract tests. | complete | M1.T2 | implementer | `python -m pytest -q tools/runtime/tests` |
| M1.T4 | `.vault/plans/001-firered-runtime-spike-2026-06-04.md` | Prove mGBA launch, Lua/socket IPC, screenshot, input, and memory reads. | complete | M1.T3 | implementer/validator | mGBA manual smoke plus focused tests |
| M1.T5 | `.vault/plans/001-firered-runtime-spike-2026-06-04.md` | Add minimal FireRed telemetry. | complete | M1.T4 | implementer | Telemetry fixture tests |
| M1.T6 | `.vault/plans/001-firered-runtime-spike-2026-06-04.md` | Expose minimal API and basic browser deck. | complete | M1.T5 | implementer/validator | API and browser smoke |

### M2: FireRed Telemetry Adapter

- Goal: Replace minimal telemetry with reliable source-backed FireRed state decoding.
- Depends on: M1
- Validation level: L2 targeted fixture suite plus runtime telemetry smoke
- Review gate: source evidence review

| Task ID | Plan | Task | State | Depends On | Owner/Lane | Validation |
|---|---|---|---|---|---|---|
| M2.T1 | `.vault/plans/002-firered-telemetry-adapter-2026-06-04.md` | Stabilize symbol resolution. | complete | M1 | implementer | Symbol fixture tests |
| M2.T2 | `.vault/plans/002-firered-telemetry-adapter-2026-06-04.md` | Add source-backed save-block readers. | complete | M2.T1 | implementer | Save-block fixture tests |
| M2.T3 | `.vault/plans/002-firered-telemetry-adapter-2026-06-04.md` | Load map/layout metadata. | complete | M2.T2 | implementer | Map fixture tests |
| M2.T4 | `.vault/plans/002-firered-telemetry-adapter-2026-06-04.md` | Add text decoding and mode heuristics. | complete | M2.T2 | implementer/reviewer | Text and mode tests |
| M2.T5 | `.vault/plans/002-firered-telemetry-adapter-2026-06-04.md` | Publish versioned telemetry schema. | complete | M2.T3 M2.T4 | implementer/validator | Schema/API tests |

### M3: Runtime Web Control Deck

- Goal: Build the manual observation/control surface for runtime operation.
- Depends on: M1 and M2
- Validation level: L2 API tests plus browser verification
- Review gate: browser/UI review

| Task ID | Plan | Task | State | Depends On | Owner/Lane | Validation |
|---|---|---|---|---|---|---|
| M3.T1 | `.vault/plans/003-runtime-web-control-deck-2026-06-04.md` | Stabilize browser API client. | complete | M1.T6 | implementer | API client/browser smoke |
| M3.T2 | `.vault/plans/003-runtime-web-control-deck-2026-06-04.md` | Build frame and manual controls. | complete | M3.T1 | implementer/accessibility-auditor | Keyboard/click smoke |
| M3.T3 | `.vault/plans/003-runtime-web-control-deck-2026-06-04.md` | Render telemetry and trace panels. | complete | M2.T5 M3.T1 | implementer | Browser smoke |
| M3.T4 | `.vault/plans/003-runtime-web-control-deck-2026-06-04.md` | Add runtime-owned savestate controls. | complete | M3.T2 | implementer/security | State directory tests |
| M3.T5 | `.vault/plans/003-runtime-web-control-deck-2026-06-04.md` | Run browser and accessibility verification. | complete | M3.T4 | validator/accessibility-auditor | Screenshot/check summary |

### M4: Codex Agent Loop

- Goal: Add bounded agent context, action policy, planner client, and objective runner.
- Depends on: M1 through M3
- Validation level: L2 fake-runtime tests plus short real-runtime smoke
- Review gate: security and policy review

| Task ID | Plan | Task | State | Depends On | Owner/Lane | Validation |
|---|---|---|---|---|---|---|
| M4.T1 | `.vault/plans/004-codex-agent-loop-2026-06-04.md` | Define compact agent context schema. | complete | M2.T5 | implementer/security | Privacy/context tests |
| M4.T2 | `.vault/plans/004-codex-agent-loop-2026-06-04.md` | Implement action policy and blocked-action traces. | complete | M1.T6 | implementer/security | Policy tests |
| M4.T3 | `.vault/plans/004-codex-agent-loop-2026-06-04.md` | Add Codex client/app-server integration. | complete | M4.T1 M4.T2 | implementer | Fake client tests |
| M4.T4 | `.vault/plans/004-codex-agent-loop-2026-06-04.md` | Add bounded objective runner. | complete | M4.T3 | implementer/reviewer | Runner stop-condition tests |
| M4.T5 | `.vault/plans/004-codex-agent-loop-2026-06-04.md` | Expose agent endpoints and UI state. | complete | M4.T4 M3.T5 | implementer/validator | Short objective smoke |

### M5: LeafGreen Support And Hardening

- Goal: Add LeafGreen Rev 1 and harden target profiles, storage, docs, and fallback decisions.
- Depends on: M1 through M4
- Validation level: L3 full runtime test/smoke gate
- Review gate: final hardening review

| Task ID | Plan | Task | State | Depends On | Owner/Lane | Validation |
|---|---|---|---|---|---|---|
| M5.T1 | `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md` | Add target profiles and hash checks. | complete | M1.T6 | implementer/security | Profile/hash tests |
| M5.T2 | `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md` | Add LeafGreen adapter path. | complete | M5.T1 M2.T5 | implementer | LeafGreen fixture/smoke tests |
| M5.T3 | `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md` | Harden runtime storage by target. | ready | M5.T1 M3.T4 | implementer/security | Path containment tests |
| M5.T4 | `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md` | Evaluate BizHawk fallback only if evidence requires it. | planned | M1.T4 | reviewer/implementer | Adapter contract tests if implemented |
| M5.T5 | `.vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md` | Write setup and operating docs. | planned | M5.T3 | implementer/reviewer | Fresh-read docs review |

## State Values

- planned
- ready
- in_progress
- verifying
- review_pending
- blocked
- complete
