# FireRed Minimal Telemetry Research

Date: 2026-06-04

## Scope

CODE / PRIOR_ARTIFACTS research for M1.T5 in `.vault/plans/001-firered-runtime-spike-2026-06-04.md`.

## Sources

- `include/global.h`
- `include/global.fieldmap.h`
- `src/load_save.c`
- `src/fieldmap.c`
- `Makefile`
- `.vault/research/pocodex-pokefirered-runtime-2026-06-03.md`

## Findings

- `struct SaveBlock1` starts with `pos` at `0x0000`, `location` at `0x0004`, `playerPartyCount` at `0x0034`, object events at `0x06A0`, flags at `0x0EE0`, and vars at `0x1000` (`include/global.h`).
- `struct WarpData` stores `mapGroup`, `mapNum`, `warpId`, then aligned `x`/`y`; within `SaveBlock1.location`, map group is `0x0004`, map num is `0x0005`, warp id is `0x0006`, location x is `0x0008`, and location y is `0x000A` (`include/global.h`).
- `struct SaveBlock2` stores player identity/options and `encryptionKey` at `0x0F20` (`include/global.h`).
- `src/load_save.c` declares `gSaveBlock1Ptr` and `gSaveBlock2Ptr` as COMMON_DATA globals and randomizes SaveBlock addresses with a small offset in `SetSaveBlocksPointers`.
- `src/fieldmap.c` declares `gMapHeader` and `gCamera`; `SaveMapView` reads player position from `gSaveBlock1Ptr->pos`.
- `include/global.fieldmap.h` defines `struct Camera` with active bit plus signed 32-bit x/y fields; camera x/y decode at offsets `0x04` and `0x08`.
- No generated `poke*.sym` exists in the workspace or reference clone. `make syms` depends on the GBA build/toolchain path; `arm-none-eabi-*` tools are not currently installed in this environment.

## Implementation Consequence

M1.T5 should load generated symbols when `target.symbol_path` is configured and should report explicit unavailable fields when the symbol file is absent. The first implementation should not hardcode unknown global addresses for `gSaveBlock1Ptr`, `gSaveBlock2Ptr`, or `gCamera`.

## Validation

- Fixture tests decode SaveBlock pointers, map group/number, player position, camera position, SaveBlock2 encryption key, and generated-symbol text formats.
- Real mGBA telemetry smoke without a symbol file produced:
  - ROM SHA-1 match: true
  - missing symbols: `gSaveBlock1Ptr`, `gSaveBlock2Ptr`
  - location unavailable reason: `missing_save_block_1`

## Unresolved

- Generate or provide `pokefirered_rev1.sym` after the GBA toolchain is available.
- Plan 002 should stabilize symbol generation/loading and broaden telemetry beyond the M1 fixture-backed slice.
