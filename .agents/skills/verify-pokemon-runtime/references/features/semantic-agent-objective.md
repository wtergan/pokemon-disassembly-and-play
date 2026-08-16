# Bounded model-driven semantic objective

**Implementation:** present in the bounded objective runner and semantic
scoring path. **Live verification:** one FireRed movement passed on
2026-08-16; broader story and battle progression remains in progress.

For the retained check, a fresh server loaded the model-created
`first_overworld` checkpoint. Telemetry showed high-confidence field mode
from `CB2_Overworld`, map `MAP_PALLET_TOWN_PLAYERS_HOUSE_2F`, and starting
position `(6,6)`. The configured planner made one `tap_left` decision. The
runtime observed `(6,6) → (5,6)` on the same map and returned
`semantic_state_verified`; all six checks passed: location, coordinates,
mode, map, target position, and changed position.

Local ignored proof:
[movement objective](../../../../../.runtime-logs/recovery-2026-08-16/movement-objective.json) ·
[one-step result](../../../../../.runtime-logs/recovery-2026-08-16/movement-result.json) ·
[start checkpoint](../../../../../.runtime-logs/recovery-2026-08-16/first-overworld-checkpoint.json).
The result proves this bounded transition from the retained checkpoint. It
does not prove the path from a new game through the story, battles, or later
maps. The web deck's Run button independently passed the same bounded movement check in a fresh browser context.

Read [plan 007](../../../../../docs/plans/007-firered-semantic-progression-2026-07-09.md)
for the progression acceptance boundary and
[plan 008](../../../../../docs/plans/008-runtime-recovery-and-autonomous-play-2026-08-16.md)
for current recovery context. Run the objective only when model-driven play
is authorized, the client is available, and telemetry meets the preconditions
in the [verification recipe](../../SKILL.md).

Source anchors: `tools/runtime/runtime_app.py`,
`tools/runtime/objective_runner.py`, `tools/runtime/objective_scoring.py`,
and `tools/runtime/tests/test_semantic_objectives.py`. Source and fixture
checks establish implementation, not live gameplay evidence.
