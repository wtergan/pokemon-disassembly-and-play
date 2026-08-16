# Project roadmap

The runtime launches a dedicated mGBA instance, exposes a browser control deck and a bounded model planner, and decodes FireRed/LeafGreen Rev 1 state from the pret source tree.

## Current state

Verified on 2026-08-16: GPT-6 Luna xhigh completed the FireRed intro into the first controllable overworld, then performed a one-step movement confirmed by named map, coordinates and high-confidence field telemetry. The live browser Run path passed too. FireRed and LeafGreen input/checkpoint checks preserved normal saves. Full story, battles and LeafGreen autonomous progression remain unverified.

Seven installed emulators have working per-user Desktop/Start Menu shortcuts and verified taskbar pins. The runtime test suite has 123 passing cases in 11 responsibility modules; the 93 original cases were retained while 30 small files became seven grouped modules.

## Feature plans

| Plan | Status | Evidence |
|---|---|---|
| [Recovery and autonomous play](plans/008-runtime-recovery-and-autonomous-play-2026-08-16.md) | Verified bounded acceptance | Real mGBA, model, browser and Windows launch checks |
| [Semantic progression](plans/007-firered-semantic-progression-2026-07-09.md) | First-overworld acceptance achieved | Exact map/coordinate movement; broader actions deferred |

Use the [runtime guide](../tools/runtime/README.md), [verification recipe](../.agents/skills/verify-pokemon-runtime/SKILL.md), and [feature map](visuals/runtime-feature-map.html). Earlier milestones are condensed in [runtime history](runtime-history.md).

## Backlog

- Add bounded dialogue/menu/route skills, each with an observed state transition and checkpoint recovery.
- Verify battles and broader story progression; verify LeafGreen semantics with matching symbols.
- Repair the obsolete protected Public Desktop PCSX2 shortcut if an administrator chooses to; the new per-user Desktop and taskbar links already work.
