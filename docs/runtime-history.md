# Runtime plan history

This note condenses the completed baseline plans 001-006. “Complete” records
what each plan reported at the time; it does not mean that the checks were
rerun during this documentation migration.

1. **FireRed runtime spike (2026-06-04).** Bootstrapped the repository and
   added a dedicated mGBA runtime, basic HTTP API, snapshots, input, traces,
   minimal telemetry, and an initial browser deck. Real mGBA launch/action
   checks were recorded; browser verification covered the deck. This established
   the runtime loop, not reliable semantic game-state decoding.
2. **FireRed telemetry adapter (2026-06-04).** Added source-backed symbol
   resolution, save-block and map readers, text decoding, and evidence-aware
   mode heuristics, with fixture and fake-memory coverage. The plan left a real
   mGBA memory smoke unchecked; generated-symbol live telemetry was still a
   later task.
3. **Runtime web control deck (2026-06-04).** Added manual controls, telemetry
   and trace panels, and runtime-owned save-state slots. The plan records
   desktop/mobile Playwright checks against a fake runtime and a final suite of
   50 passed, 5 skipped. Those checks did not establish the UI against live
   decoded game state.
4. **Codex agent loop (2026-06-04).** Added privacy-bounded agent context,
   validated action policy, opt-in planner clients, bounded objectives, and
   agent UI. Tests and endpoint/browser smokes used fake runtime/client paths;
   the plan explicitly left a real mGBA objective smoke and security review
   open.
5. **LeafGreen support and hardening (2026-06-04).** Added FireRed/LeafGreen
   Rev 1 profiles with hash checks, LeafGreen adapter selection, target-scoped
   runtime storage, and setup documentation. Basic real-runtime health,
   snapshot, and action smokes were recorded for both targets. LeafGreen
   location remained unavailable without symbols. The plan reports 77 passed,
   10 skipped in its full runtime suite; no BizHawk adapter was justified.
6. **Runtime reconnect and autonomy smoke (2026-07-09).** Added bounded Lua
   connection retries and an executed-action scoring condition. The plan
   reports 89 runtime tests passing and a real FireRed sequence of three
   planner-selected, policy-validated inputs (`tap_a`, `tap_start`, `tap_up`).
   This proves bounded input execution only; the plan explicitly did not claim
   a title-flow, location, or other semantic state transition.

## Resume context

The July 9 follow-up, [FireRed Semantic Progression](plans/007-firered-semantic-progression-2026-07-09.md),
reports that toolchain/symbol generation and disposable-save setup were
complete, but first-overworld telemetry was blocked before the Lua reverse
client connected. [Runtime recovery plan 008](plans/008-runtime-recovery-and-autonomous-play-2026-08-16.md)
is the current continuation point. The last baseline game-level evidence is
three executed inputs, not verified gameplay progress.
