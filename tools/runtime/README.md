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

From the repo root, install the existing runtime requirements in a local environment:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r tools/runtime/requirements.txt
```

Alternatively, use `python3 -m venv .venv` and pip when Python's venv/ensurepip
package is installed. The commands below use `.venv/bin/python`.

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
rom_path = "/mnt/t/Emulation/ROMs/Game Boy Advance/Pokemon - FireRed Version (USA, Europe) (Rev 1).gba"
verify_hash = true
# symbol_path = "pokefirered_rev1.sym"
```

For LeafGreen Rev 1:

```toml
[target]
game = "leafgreen"
revision = "rev1"
rom_path = "/mnt/t/Emulation/ROMs/Game Boy Advance/Pokemon - LeafGreen Version (USA, Europe) (Rev 1).gba"
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
executable = "/mnt/t/Emulation/Emulators/mGBA-dev/mGBA.exe"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"
host = "127.0.0.1"
port = 8766
windows_paths = true
connection_mode = "lua_client"
frame_advance_mode = "realtime_wait"
script_cache_dir = "/mnt/t/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache"
log_file = "/mnt/t/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache/mgba_bridge.log"
```

Notes:

- Set `executable` to the actual `mGBA.exe` in your extracted development build directory.
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
manual controls, traces, or target hash verification. Semantic gameplay requires
compatible symbols. Build the same target and compare its ROM SHA-1 to the owned
ROM before trusting generated addresses.

## Run The Runtime

Start the server from the repo root:

```bash
.venv/bin/python -m tools.runtime.server \
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

Use `mode = "fake"` only for deterministic local tests. `mode = "app_server"` enables screenshot-aware planning through the local Codex
app-server. The planner receives structured state and a separate game image; it
can only select advertised actions. Objective scoring uses telemetry. The
configured model and reasoning effort are passed through unchanged.

```toml
[agent]
mode = "app_server"
executable = "codex"
model = "gpt-6-luna"
reasoning_effort = "xhigh"
```

Use a current signed-in CLI context. A workspace-routing 401 is an authentication
failure, not a game or bridge failure. On a workstation whose CLI wrapper can
select the desktop sign-in, set its existing context option only for the runtime
process; keep account paths in local configuration. Never copy or publish auth
files. The protocol follows the [official app-server documentation](https://developers.openai.com/codex/app-server).

## Verification

Run focused bridge checks:

```bash
.venv/bin/python -m pytest -q \
  tools/runtime/tests/test_mgba_launch_command_should_include_script_and_rom.py \
  tools/runtime/tests/test_mgba_socket_bridge_should_parse_socket_responses.py -vv
```

Run the full runtime test suite:

```bash
.venv/bin/python -m pytest -q tools/runtime/tests
```

Run compile and whitespace checks:

```bash
.venv/bin/python -m compileall -q tools/runtime
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


## Verified gameplay and repeatable checks

The runtime launches an isolated ROM copy for battery saves. Checkpoints stay
under the target's runtime-owned storage; Windows launches retain the actual
Windows PID and creation time so stopping the server closes its own GUI process.
The Lua input mapping follows mGBA's [single-key API](https://mgba.io/docs/scripting.html).

Run the real bridge/input/checkpoint check before a server session:

```bash
.venv/bin/python -m tools.runtime.verify_runtime \
  --config tools/runtime/runtime.local.toml \
  --output .runtime-logs/verification
```

Do not run this concurrently with a server using the same configured bridge
port. It preserves a JSON report and screenshot, checks all ten physical GBA key
bits and checkpoint round trips, and compares normal save fingerprints before
and after cleanup. This is a hardware/control check; it does not claim gameplay
progress.

For a semantic objective, use observed mode, map and coordinates together:

```json
{
  "objective": {
    "description": "Move one tile in the starting bedroom",
    "max_steps": 3,
    "save_before": true,
    "success": {
      "mode_is": "field",
      "map_is": "MAP_PALLET_TOWN_PLAYERS_HOUSE_2F",
      "position_changed": true
    }
  }
}
```

Post this to `/agent/objective` after the player is in that named map. Use
`position_is: {"x": 5, "y": 6}` for a specific target; combine it with
`position_changed: true` to require a transition. Unknown criteria and incomplete
semantic criteria fail before planning. A failed starting checkpoint stops the
run. `agent_steps_at_least` and `runtime_frame_at_least` remain explicitly labelled
smoke checks.

The default web-deck objective uses semantic criteria. Save a checkpoint before
exploration; press **Stop** to end an objective between decisions. New-game
navigation uses the screenshot until real field state exists. Naming screens may
require START followed by A; an empty name can use the game's default.

The reusable [verification skill](../../.agents/skills/verify-pokemon-runtime/SKILL.md)
covers Launch, Doctor, Drive, Evidence and Cleanup. The [feature map](../../docs/visuals/runtime-feature-map.html)
shows which paths have current proof. See the [roadmap](../../docs/PLAN.md) for
acceptance evidence and follow-up limits. No full-story or battle autonomy is
implied by a first-overworld demonstration.
