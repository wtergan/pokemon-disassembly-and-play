---
date: 2026-06-04
status: accepted
related_plan: .vault/plans/005-leafgreen-support-and-hardening-2026-06-04.md
---

# Target Profile Hash Verification

## Decision

Runtime config resolves supported targets through explicit profiles and verifies
ROM SHA-1 by default before constructing the runtime.

## Rationale

- FireRed Rev 1 and LeafGreen Rev 1 have known upstream SHA-1 files and
  research-confirmed user ROM hashes.
- Early rejection prevents confusing telemetry when a ROM is the wrong game,
  revision, hack, or damaged file.
- Tests still need tiny fixture ROMs, so `verify_hash = false` is available as
  an explicit opt-out that keeps mismatch metadata visible.

## Consequences

- Real local configs should leave hash verification enabled.
- Fixture tests must opt out intentionally with `verify_hash = false`.
- Adding a new target requires a profile entry, expected SHA-1, symbol basename,
  build name, and adapter key.
