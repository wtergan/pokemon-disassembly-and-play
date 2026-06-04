# Local Engineering Vault

This `.vault/` directory is the repo-local operational memory for the
FireRed/LeafGreen programmable runtime project.

It tracks plans, evidence, architecture decisions, reusable fixes, blockers,
and goal handoff state. It is not a transcript dump and should not mirror every
conversation detail.

## Structure

- `PLAN.md` - project-level roadmap, current state, active plan index, and cross-plan risks
- `plans/` - executable feature plans
- `research/` - local code research and external technical research
- `decisions/` - durable decision records that outlive a single plan
- `solutions/` - durable reusable fixes, patterns, and lessons worth reusing later
- `encounters/` - specific failures, blockers, root causes, fixes, and prevention notes
- `goals/` - optional long-running goal run overlays for native `/goal` or multi-plan `$lfg` orchestration
- `visuals/` - optional self-contained HTML companions for plans and architecture diagrams

## Usage Rules

- Keep this vault focused on active engineering work.
- Prefer updating an existing relevant note or plan over creating duplicates.
- Research notes use descriptive filenames such as `pocodex-pokefirered-runtime-YYYY-MM-DD.md`.
- Decisions, solutions, and encounters use `topic-YYYY-MM-DD.md` because they already live in typed directories.
- Feature plans use `###-feature-topic-YYYY-MM-DD.md`, where the sequence number stays sortable first.
- Feature plans include architecture diagrams, goal contracts, worktree guidance, TDD expectations, verification contracts, stop conditions, and artifact capture rules.
- Decisions are promoted out of plans when the choice affects future work.
- Solutions are captured only when a fix or pattern is likely to be reused.
- Encounters are captured only when a failure, blocker, or surprise is likely to recur or teaches a prevention rule.
- Goal runs use `.vault/goals/goal-topic-YYYY-MM-DD/` only when a long-running objective needs durable state. Link feature plans instead of moving or duplicating them.
- Visual companions should be self-contained and safe to open locally in a browser.

## PLAN.md vs Feature Plans

- `PLAN.md` answers: where is the project now, what plans exist, which risks matter across plans, and what is next?
- `plans/001-feature-topic-YYYY-MM-DD.md` answers: exactly how should one feature or change be executed and verified?
- `goals/goal-topic-YYYY-MM-DD/` answers: what long-running objective is active, which plans it coordinates, what milestone/task state changed, and how a future agent should resume.

## Relationship to Obsidian

This repo-local vault is operational memory. The user's Obsidian project note
under `~/Vault/01_Projects/` should remain the higher-level human-facing rollup.
