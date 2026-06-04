---
date: 2026-06-04
related_plan: .vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md
---

# Target-Scoped Runtime Storage Pattern

## Pattern

Treat configured runtime paths as roots, then append the target profile key for
runtime-owned artifacts:

- `.runtime-state/firered_rev1`
- `.runtime-state/leafgreen_rev1`
- same shape for traces, logs, screenshots, and cache paths

## Why It Works

- FireRed and LeafGreen savestates cannot silently overwrite each other.
- The configured root remains simple and ignored by git.
- The target profile key is validated before becoming a path segment.
- Factory code can pass scoped state and screenshot paths without changing
  manual runtime APIs.

## Reuse Notes

- Use `target_scoped_runtime_paths()` when adding trace, log, screenshot, or
  cache writers.
- Keep user-provided absolute emulator cache paths separate from runtime-owned
  scoped cache paths unless a later change explicitly migrates them.
