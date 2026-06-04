---
date: 2026-06-04
plan: .vault/plans/002-firered-telemetry-adapter-2026-06-04.md
scope: FireRed generated symbol discovery
---

# FireRed Symbol Resolution

## Context

Plan 002 needs generated FireRed Rev 1 symbols before telemetry can safely read
SaveBlock pointers, camera state, callbacks, tasks, and current-map state. The
checked-in `sym_*.txt` files are linker layout inputs, not generated runtime
symbol tables.

## Pattern

- Keep symbol behavior in `tools/runtime/games/firered/symbols.py`.
- Parse objdump-like, simple, and linker-map symbol lines.
- When `target.symbol_path` is omitted, discover `pokefirered_rev1.sym` from
  the repo root or `build/firered_rev1/`.
- Report coverage as explicit `available`/`missing` data.
- Expose only the symbol file basename through telemetry to avoid leaking local
  absolute paths.

## Validation

- `timeout 60s /tmp/pokemon-runtime-venv/bin/python -m pytest -q tools/runtime/tests`
  - Result in current execution wrapper: `21 passed, 7 skipped`.
  - Skips are environment-limited socket tests and ASGI endpoint tests in a
    stale local venv with `starlette 1.2.1`; the repo now pins `starlette<1.0`.

## Follow-Up

M2.T2 can depend on `SymbolTable.coverage()` and factory auto-discovery. Real
runtime decoding still requires generating `pokefirered_rev1.sym` once the GBA
build toolchain is available.
