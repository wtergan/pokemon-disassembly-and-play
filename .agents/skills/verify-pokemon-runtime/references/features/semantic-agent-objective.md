# Bounded model-driven semantic objective

**Implementation:** present in the bounded objective runner and semantic
scoring path. **Live verification:** a FireRed movement and a GPT-5.6 Luna house exit passed. Broader story and battle progression remains unverified.

For the retained check, a fresh server loaded the model-created
`first_overworld` checkpoint. Telemetry showed high-confidence field mode
from `CB2_Overworld`, map `MAP_PALLET_TOWN_PLAYERS_HOUSE_2F`, and starting
position `(6,6)`. The configured planner made one `tap_left` decision. The
runtime observed `(6,6) → (5,6)` on the same map and returned
`semantic_state_verified`; all six checks passed: location, coordinates,
mode, map, target position, and changed position.

The request, result and starting checkpoint remain local.
The result proves this bounded transition from the retained checkpoint. It
does not prove the path from a new game through the story, battles, or later
maps. The web deck's Run button independently passed the same bounded movement check in a fresh browser context.

Read the [roadmap](../../../../../docs/PLAN.md) for current acceptance and limits. Run objectives only when model-driven play is authorized, the client is available, and telemetry meets the preconditions in the [verification recipe](../../SKILL.md).

Source anchors: `tools/runtime/runtime_app.py`,
`tools/runtime/objective_runner.py`, `tools/runtime/objective_scoring.py`,
and `tools/runtime/tests/test_semantic_objectives.py`. Source and fixture
checks establish implementation, not live gameplay evidence.

## Repeat the house exit

Verified with GPT-5.6 Luna at xhigh: the planner moved from
`MAP_PALLET_TOWN_PLAYERS_HOUSE_2F` at `(6,6)`, through the ground floor,
to `MAP_PALLET_TOWN` at `(6,8)`. One 20-step run stopped at the doorway;
a two-step continuation passed all five semantic checks. The normal save
fingerprints matched before and after both segments. An earlier timed-out
turn recovered to its checkpoint and is retained as an incomplete attempt.

Use the runtime's existing model configuration and `house_exit_start`
checkpoint only when available. Confirm the named bedroom map and `(6,6)`
before the first segment. Send this payload to `POST /agent/objective` and
retain every result under a fresh ignored run directory:

```json
{
  "objective": {
    "description": "Leave the house and stand in Pallet Town at (6,8). Use the screenshot and telemetry to navigate stairs and the front door. Wait for transitions.",
    "max_steps": 20,
    "save_before": true,
    "recover_on_error": false,
    "success": {
      "mode_is": "field",
      "map_is": "MAP_PALLET_TOWN",
      "position_is": {"x": 6, "y": 8}
    }
  },
  "operator_prompt": "Source map context: upstairs stairs are at (10,2); stand on that tile then press LEFT to trigger the directional stair warp. Ground-floor exit tiles are (4,8) and (5,8); leave downward. Choose your route around obstacles, use advertised actions only, and stop outside at the target."
}
```

A `step_limit` result is incomplete. Inspect the returned map, coordinates and
error first. When progress is valid, at most one further 20-step segment may
continue from the current state with the same payload. Retain both segments;
only `success`, all semantic checks true, and outdoor field telemetry count
as completion. On an error, preserve the report and checkpoint; do not
blindly retry or call the failed segment successful.

The local evidence retains both segment results, a verified summary,
before/after snapshots and normal-save fingerprints.
The retained checkpoint is `outside_luna_5_6`. This verifies the house route,
not battles or subsequent story progression.
