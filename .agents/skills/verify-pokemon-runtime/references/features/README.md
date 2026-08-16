# Runtime behaviors

Use [the verification recipe](../../SKILL.md) for launch, checks, browser
interaction, and cleanup. These three behavior references separate
implementation from execution evidence. The
[visual map](../../../../../docs/visuals/runtime-feature-map.html) is an
overview, not proof.

| Behavior | Current status | Evidence |
| --- | --- | --- |
| Owned ROM, physical inputs, checkpoint, and save containment | Verified 2026-08-16 on FireRed Rev 1 and LeafGreen Rev 1 | [Reports and limits](owned-rom-inputs-save-containment.md) |
| Bounded model-driven semantic objective | One live movement verified 2026-08-16; broader progression in progress | [Objective path](semantic-agent-objective.md) |
| Manual web deck | Selected live controls and slot checks verified 2026-08-16; Run-button semantic movement verified | [Deck path](manual-web-control-deck.md) |

Suggested regression order: owned-target preflight and save containment,
read-only server/API checks, manual deck controls and state slots, then a
bounded semantic objective when the task authorizes model use and telemetry
meets its state preconditions.
