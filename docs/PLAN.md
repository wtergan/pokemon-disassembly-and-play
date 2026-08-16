# Project roadmap

The runtime launches a dedicated mGBA instance, exposes a browser control deck and a bounded model planner, and decodes FireRed/LeafGreen Rev 1 state from the pret source tree.

## Current state

**GPT-5.6 Luna at xhigh** drove from the upstairs bedroom through the ground floor and out into Pallet Town at `(6,8)`. The route used 22 decisions across two bounded runs, with named-map, coordinate and high-confidence field telemetry. Normal saves stayed unchanged. Intro, movement, browser controls and FireRed/LeafGreen input/checkpoint checks are also verified. Full story, battles and LeafGreen autonomous progression remain unverified.

Seven installed emulators have working per-user Desktop/Start Menu shortcuts and verified taskbar pins. The runtime test suite has 123 passing cases in 11 responsibility modules; the 93 original cases were retained while 30 small files became seven grouped modules.

Use the [runtime guide](../tools/runtime/README.md), [verification recipe](../.agents/skills/verify-pokemon-runtime/SKILL.md), and [feature map](visuals/runtime-feature-map.html). Earlier milestones are condensed in [runtime history](runtime-history.md). Detailed working plans and raw execution evidence are retained locally.

## Backlog

- Add bounded dialogue/menu/route skills, each with an observed state transition and checkpoint recovery.
- Verify battles and broader story progression; verify LeafGreen semantics with matching symbols.
- Repair the obsolete protected Public Desktop PCSX2 shortcut if an administrator chooses to; the new per-user Desktop and taskbar links already work.
