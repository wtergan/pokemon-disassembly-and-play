---
name: verify-pokemon-runtime
description: Launch and verify the local FireRed/LeafGreen runtime, mGBA bridge, web deck, and bounded agent objectives using the repository's existing CLI and HTTP API.
---

# Verify the Pokémon runtime

Use this recipe for real local runtime checks. It uses the ignored
`tools/runtime/runtime.local.toml`; never print or copy that file. Keep HTTP
requests on loopback. The local config must select the owned FireRed Rev 1
target, its matching generated symbols, a dedicated Windows mGBA cache, and
target-scoped runtime state.

**Recipe status: Verified 2026-08-16** for the one-shot input/checkpoint checks,
the bounded live movement objective, and the selected live web-deck checks.
This does not verify full story or battle progression. The web deck's
agent-facing Run button passed a fresh-browser semantic movement check. Runtime reports and captures
are ignored local evidence; links to them will not work from a clean clone.
See [the behavior index](references/features/README.md) and the
[current recovery plan](../../../docs/plans/008-runtime-recovery-and-autonomous-play-2026-08-16.md).

## Launch

Run from the worktree root in WSL. Check that the environment and private local
config exist without displaying the config. Both ports must be free before
starting the one-shot check:

    test -x .venv/bin/python
    test -f tools/runtime/runtime.local.toml
    ss -ltnp '( sport = :8795 or sport = :8796 )'

If a listener belongs to another run, identify its owner. Stop only a process
owned by that run, or stop here if ownership is unclear. Never use `killall`
or kill by process name.

Run the existing verifier first. It launches and closes only its own mGBA
instance, checks all ten GBA key bits, saves and reloads a runtime checkpoint,
captures telemetry and a PNG snapshot, and compares normal ROM-adjacent save
fingerprints before and after. It creates `report.json` and `snapshot.png` in
the output folder, so choose a new ignored folder for each run.

    RUN_DIR=.runtime-logs/verification-$(date +%Y%m%d-%H%M%S)
    test ! -e "$RUN_DIR" || { printf 'Evidence folder already exists\n' >&2; exit 1; }
    ./.venv/bin/python -m tools.runtime.verify_runtime --config tools/runtime/runtime.local.toml --output "$RUN_DIR"
    printf 'Evidence directory: %s\n' "$RUN_DIR"

Wait for the verifier to exit before starting the persistent server; both use
the configured mGBA bridge port. Record the printed evidence directory. In
another WSL terminal, set `RUN_DIR` to that same relative path, then launch
the server in its own foreground terminal:

    ./.venv/bin/python -m tools.runtime.server --config tools/runtime/runtime.local.toml --host 127.0.0.1 --port 8795

Keep that terminal open. Ctrl-C stops this server and lets it close the
emulator instance it owns.

## Doctor

In the drive terminal, set `RUN_DIR` to the printed path. Check the verifier
report without dumping its full telemetry:

    jq -e '.ok == true and .rom_matches == true and (.input_checks | length == 10) and .checkpoint_reload.ok == true and .normal_saves_unchanged == true' "$RUN_DIR/report.json"

Then run read-only checks against the live server. Snapshot output is reduced
to metadata so the base64 image is not printed:

    curl -fsS http://127.0.0.1:8795/health | jq -e '.ok == true'
    curl -fsS http://127.0.0.1:8795/telemetry | jq '{target, symbols_available: .symbols.available, location_available: .location.available, mode: .mode.name, map: .location.map.id, x: .location.player_x, y: .location.player_y}'
    curl -fsS http://127.0.0.1:8795/snapshot | jq -e 'has("frame") and has("mime_type") and (.image_base64 | type == "string" and length > 0)'
    curl -fsS http://127.0.0.1:8795/agent/status | jq '{mode: .client.mode, available: .client.available}'

Expect a FireRed Rev 1 target and available symbols. A boot screen may still
report an unknown mode or unavailable map and save data; that is not gameplay
evidence. Before an objective, telemetry must report field mode, a known map,
and valid coordinates. The configured agent must also be available.

A model objective requires the private local config to select the app-server
client and a current signed-in Codex CLI context. If `client.available` is
false or the request returns an authentication error, stop. Do not read, print,
copy, or publish credentials or account files.

## Drive

Open `http://127.0.0.1:8795/` in a browser. Check the live frame, telemetry,
manual controls, trace, and runtime-owned state slots. On a narrow viewport,
confirm the game image remains visible. Press and release **Hold A**; confirm
the control returns to unpressed and the trace ends with no held inputs.
Enter a fresh slot name, select **Save**, then **Load**. Confirm the status
reports that same slot for both operations. State slots live in the dedicated
runtime cache and are separate from normal game saves.

For the retained one-step semantic check, the configured target must already
have the `first_overworld` checkpoint. Load it only when reproducing that
local FireRed check:

    curl -fsS -X POST http://127.0.0.1:8795/states/first_overworld/load | jq '{ok, slot: .slot.name, frame}'

Confirm telemetry shows high-confidence `field` mode, map
`MAP_PALLET_TOWN_PLAYERS_HOUSE_2F`, and position `(6,6)`. If the checkpoint
is missing or those values differ, stop and choose an objective supported by
the observed state; do not claim this result.

Only run a model objective when the task authorizes model-driven play. The
retained check asks for one leftward tile and stops after at most three planner
steps. Save the request and response in the run folder:

    mkdir -p "$RUN_DIR"
    jq -n '{objective:{description:"Walk left from bedroom position (6,6) to the adjacent floor tile (5,6). Take one bounded tap_left, then wait if needed for movement to settle. Preserve the same map and stop as soon as the exact coordinates are verified.",max_steps:3,save_before:true,success:{mode_is:"field",map_is:"MAP_PALLET_TOWN_PLAYERS_HOUSE_2F",position_is:{x:5,y:6},position_changed:true}},operator_prompt:"Use the observed map and position. Choose the bounded movement needed to reach the exact target; treat the screenshot as secondary."}' > "$RUN_DIR/movement-objective.json"
    curl -fsS -X POST http://127.0.0.1:8795/agent/objective -H 'content-type: application/json' --data-binary @"$RUN_DIR/movement-objective.json" | tee "$RUN_DIR/movement-result.json" | jq '{ok, status, steps, score, transitions: [.memory.steps[]?.delta | {mode_before, mode_after, map_before, map_after, position_before, position_after}]}'

A semantic pass needs `status: success`, `score.success: true`, all reported
semantic checks true, and the requested before/after map and position. A frame
advance or action count alone does not prove progress. Do not use the web
deck's **Run** button as verified until its current browser check completes.

## Evidence

Keep reports, snapshots, objective requests/results, and browser captures under
the ignored `.runtime-logs/` tree. Preserve earlier proof and use a fresh
folder for repeated runs. Record the local date, target, tested entry point,
literal result, and remaining limits in the matching
[behavior reference](references/features/README.md). Never include local ROM,
cache, account, or executable paths in shared notes.

The retained 2026-08-16 evidence covers both FireRed and LeafGreen verifier
runs, one FireRed semantic movement, and selected live deck interactions.
Those logs and screenshots are local-only; a clean checkout cannot reproduce
the evidence links without rerunning the recipe.

## Cleanup

Stop the server with Ctrl-C in the foreground terminal that launched it. Wait
for its clean exit, then check that the run's API and bridge ports no longer
have listeners:

    ss -ltnp '( sport = :8795 or sport = :8796 )'

The one-shot CLI and server close only the emulator process they own. Confirm
the owned Windows mGBA process has exited using the run's process identity;
never terminate by process name or disturb unrelated emulator sessions. Keep
reports, screenshots, traces, and target-scoped checkpoints. Do not delete
runtime cache files or normal saves as cleanup.
