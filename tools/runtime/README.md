# FireRed/LeafGreen Runtime

This directory contains the local programmable runtime inspired by Pocodex. It
is intentionally separate from the `pret/pokefirered` build system: it launches
a dedicated emulator instance, exposes HTTP endpoints, records traces, renders a
browser control deck, and delegates Pokemon-specific decoding to game adapters.

The supported runtime targets are:

- FireRed Rev 1: `pokefirered_rev1.gba`
- LeafGreen Rev 1: `pokeleafgreen_rev1.gba`

ROM SHA-1 verification is enabled by default for real configs. ROM files, save
files, emulator binaries, and local config stay outside git.

## Layout

- `runtime.example.toml`: committed template for local runtime config.
- `runtime.local.toml`: ignored local config for real ROM/emulator paths.
- `server.py`: CLI entrypoint for the HTTP runtime and web deck.
- `emulators/`: emulator bridge contract plus the mGBA socket bridge.
- `games/firered/` and `games/leafgreen/`: target telemetry adapters.
- `static/`: browser control deck assets.
- `.runtime-*`: ignored runtime-owned artifacts at the repo root, scoped by
  target profile when loaded through config.

## Safety Boundaries

- Use only ROMs you own and keep them outside this repository.
- Do not commit `runtime.local.toml`, screenshots, savestates, traces, logs,
  cache files, or emulator binaries.
- Use a dedicated runtime emulator instance. Do not point the runtime at an
  emulator session used for normal play.
- Leave `verify_hash = true` for real use so wrong games, revisions, hacks, or
  damaged files fail before launch.
- The Codex agent client defaults to disabled. Manual controls, telemetry, and
  savestates work without Codex credentials or an app-server.

## Python Setup

From the repo root, create an isolated Python environment and install the runtime
dependencies:

```bash
python3 -m venv /tmp/pokemon-runtime-venv
/tmp/pokemon-runtime-venv/bin/python -m pip install -r tools/runtime/requirements.txt
```

Use another venv path if you prefer. The commands below assume
`/tmp/pokemon-runtime-venv`.

## Local Config

Copy the template and edit local paths:

```bash
cp tools/runtime/runtime.example.toml tools/runtime/runtime.local.toml
```

For FireRed Rev 1:

```toml
[target]
game = "firered"
revision = "rev1"
rom_path = "/mnt/c/Emulation/ROMs/Game Boy Advance/Pokemon - FireRed Version (USA, Europe) (Rev 1).gba"
verify_hash = true
# symbol_path = "pokefirered_rev1.sym"
```

For LeafGreen Rev 1:

```toml
[target]
game = "leafgreen"
revision = "rev1"
rom_path = "/mnt/c/Emulation/ROMs/Game Boy Advance/Pokemon - LeafGreen Version (USA, Europe) (Rev 1).gba"
verify_hash = true
# symbol_path = "pokeleafgreen_rev1.sym"
```

If `symbol_path` is omitted, the runtime tries to discover the target symbol file
from the repo root and the matching build directory. Without symbols, the runtime
still reports target identity and explicit unavailable telemetry sections rather
than guessing decoded state.

## mGBA On Windows/WSL

The proven Windows/WSL setup uses Windows mGBA launched from WSL with a
Lua-client reverse socket:

```toml
[mgba]
executable = "/mnt/c/Emulation/Emulators/mGBA-dev/mgba-qt.exe"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"
host = "127.0.0.1"
port = 8766
windows_paths = true
connection_mode = "lua_client"
frame_advance_mode = "realtime_wait"
script_cache_dir = "/mnt/c/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache"
log_file = "/mnt/c/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache/mgba_bridge.log"
```

Notes:

- The stable Windows mGBA `0.10.5` frontend rejected `--script` in local smoke
  testing. Use a development build whose Qt frontend accepts `--script`.
- `windows_paths = true` lets Python convert WSL paths with `wslpath`.
- `connection_mode = "lua_client"` makes Python listen on WSL localhost and lets
  the Lua script connect back from Windows.
- `frame_advance_mode = "realtime_wait"` avoids blocking the visible mGBA GUI
  core from the Lua socket callback.
- Keep `script_cache_dir` and `log_file` on a Windows-local path.

On non-Windows or native Linux setups, the template defaults may be enough:

```toml
[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"
host = "127.0.0.1"
port = 8766
windows_paths = false
connection_mode = "lua_server"
frame_advance_mode = "lua_run_frame"
```

## Runtime Artifacts

Keep the runtime directories under ignored roots:

```toml
[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
```

When loaded through target profiles, these roots are scoped by profile key, for
example `.runtime-state/firered_rev1` and `.runtime-state/leafgreen_rev1`.

## Symbols

Source-backed telemetry is best with generated symbols:

```bash
make syms GAME_VERSION=FIRERED GAME_REVISION=1
make syms GAME_VERSION=LEAFGREEN GAME_REVISION=1
```

Expected symbol filenames are:

- `pokefirered_rev1.sym`
- `pokeleafgreen_rev1.sym`

If the GBA toolchain is not set up yet, follow the upstream build instructions in
`INSTALL.md` first. Symbol generation is not required for launch, screenshots,
manual controls, traces, or target hash verification.

## Run The Runtime

Start the server from the repo root:

```bash
/tmp/pokemon-runtime-venv/bin/python -m tools.runtime.server \
  --config tools/runtime/runtime.local.toml \
  --host 127.0.0.1 \
  --port 8765
```

Open `http://127.0.0.1:8765/` for the web control deck.

Useful endpoints:

- `GET /health`
- `GET /snapshot`
- `GET /telemetry`
- `POST /action`
- `GET /states`
- `POST /states/{slot}/save`
- `POST /states/{slot}/load`
- `GET /agent_context`
- `GET /agent/status`
- `POST /agent/step`
- `POST /agent/objective`
- `POST /agent/stop`

## Agent Mode

The default agent config is safe for manual operation:

```toml
[agent]
mode = "disabled"
executable = "codex"
```

Use `mode = "fake"` only for deterministic local tests. `mode = "app_server"` is
opt-in and should stay behind the bounded action policy and objective runner.

## Verification

Run focused bridge checks:

```bash
/tmp/pokemon-runtime-venv/bin/python -m pytest -q \
  tools/runtime/tests/test_mgba_launch_command_should_include_script_and_rom.py \
  tools/runtime/tests/test_mgba_socket_bridge_should_parse_socket_responses.py -vv
```

Run the full runtime test suite:

```bash
/tmp/pokemon-runtime-venv/bin/python -m pytest -q tools/runtime/tests
```

Run compile and whitespace checks:

```bash
/tmp/pokemon-runtime-venv/bin/python -m compileall -q tools/runtime
git diff --check
```

Some endpoint tests may skip if the local venv has an incompatible stale
Starlette version. The repo requirements pin `starlette<1.0`; reinstall the
runtime requirements if endpoint tests unexpectedly skip or fail because of ASGI
dependency drift.

## Troubleshooting

`runtime config does not exist`

Check that `tools/runtime/runtime.local.toml` exists and that the server command
uses `--config tools/runtime/runtime.local.toml`.

`ROM path does not exist`

Use a WSL path such as `/mnt/c/...` for Windows files. Keep the ROM outside the
repo and verify the path in WSL with `test -f "<path>"`.

`ROM SHA-1 mismatch`

The configured ROM is not the supported target revision. Keep
`verify_hash = true` for real runtime use and correct the local ROM path.

`mGBA rejects --script`

Use a Windows mGBA development build whose Qt frontend supports `--script`.

`could not connect to mGBA bridge`

For Windows mGBA launched from WSL, use `connection_mode = "lua_client"`,
`windows_paths = true`, and a free local port. Check the configured
`mgba_bridge.log` path if mGBA opens but the runtime never connects.

`snapshot` or browser refresh is slow

Use the dedicated runtime mGBA instance and keep screenshots under the configured
runtime-owned screenshot/cache directories. The bridge serializes socket
requests, so many concurrent browser refreshes will queue rather than corrupt
the line protocol.

Telemetry reports unavailable sections

This is expected before generated symbols exist or before the game has initialized
save-block pointers. Generate the matching `.sym` file and keep the game running
past boot/title screens before expecting decoded location/save data.
