---
date: 2026-06-04
related_plan: .vault/plans/004-codex-agent-loop-2026-06-04.md
---

# Codex Agent Loop Solution Pattern

## Pattern

Keep the agent loop split into four bounded layers:

- `agent_context.py`: compact privacy-safe state and advertised affordances.
- `interaction_policy.py`: strict action ID validation and action traces.
- `agent_service.py` plus `codex_client.py`: one planner decision at a time, disabled by default.
- `objective_runner.py`: short capped loops that compare context before and after each step.

## Why It Works

- Manual runtime control remains independent from planner availability.
- Rejected or malformed planner output is traceable without reaching the emulator.
- Objective runs do not claim success from action count; they require explicit
  context criteria such as frame or mode checks.
- Quick-save and recovery hooks are local to the objective runner and can be
  strengthened without changing the planner client interface.

## Reuse Notes

- Add new success criteria in `objective_scoring.py`, not in the runner loop.
- Add new planner actions in `interaction_policy.py`, then expose them through
  `agent_context`.
- Keep objective endpoints/UI thin: they should call `RuntimeCore.run_objective()`
  and display `memory.steps`, not duplicate runner logic.
