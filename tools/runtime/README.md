# FireRed/LeafGreen Runtime

This directory contains the local programmable runtime inspired by Pocodex. The
runtime is intentionally separate from the `pret/pokefirered` build system: it
launches a dedicated emulator instance, exposes HTTP endpoints, records traces,
and delegates Pokemon-specific decoding to game adapters.

## Local Configuration

Copy `runtime.example.toml` to `runtime.local.toml` and adjust paths for the
local machine. `runtime.local.toml` is ignored by git because it may contain
private local paths.

ROM files must stay outside this repository. The first supported target is the
user-owned FireRed Rev 1 ROM under `C:\Emulation`, addressed from WSL through
`/mnt/c/...`.

## Verification

Use an isolated environment, then run:

```bash
python -m pytest -q tools/runtime/tests
```

