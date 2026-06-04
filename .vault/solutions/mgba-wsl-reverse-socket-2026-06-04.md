# mGBA Windows From WSL Reverse Socket

## Context

The runtime launches Windows mGBA from WSL while the Python runtime remains in WSL. The official stable `0.10.5` Windows frontend does not expose `--script`; the official dev build does.

## Solution

- Use a dev Windows mGBA build whose Qt frontend accepts `--script`.
- Stage `mgba_bridge.lua` and screenshots into a Windows-local cache under the mGBA directory, then pass `C:\...` paths to the emulator.
- Export `POKEMON_RUNTIME_*` variables to Win32 children with `WSLENV`.
- Use `connection_mode = "lua_client"` so Python listens on WSL `127.0.0.1` and mGBA connects back from Windows.
- Use `frame_advance_mode = "realtime_wait"` for visible GUI mGBA; do not call `emu:runFrame()` from the socket callback.

## Validation

- Runtime tests: `/tmp/pokemon-runtime-venv/bin/python -m pytest -q tools/runtime/tests` -> 12 passed.
- Real smoke: health frame 3, `read8(0x08000000) == 127`, press/wait/release advanced to frame 21, screenshot frame 22 with nonempty PNG payload.

## Reuse

Apply this mode for Windows emulator launches from WSL. Native Linux/macOS mGBA can keep the default Lua-server mode until evidence says otherwise.
