# Pocodex To FireRed/LeafGreen Runtime Research

Date: 2026-06-03

## Research Question

How should a Windows-friendly programmable runtime, telemetry stack, web UI, and Codex agent loop be built for Pokemon FireRed/LeafGreen, using `pret/pokefirered` and the user's owned ROMs, while preserving the useful architecture from `Dimillian/Pocodex`?

## Local Context

- Working directory: `/home/gilgames/Code/pokemon-disassembly-and-play`
- The workspace was empty when research began.
- Screenshot inspected: `/mnt/c/Users/gilgames/Pictures/Screenshots/pokemon-disassembly-play/Screenshot 2026-06-02 182825.png`
- The screenshot shows a Pocodex-like browser control deck with:
  - live ROM framebuffer
  - manual input buttons
  - parsed mode/map/dialogue/menu state
  - runtime and agent logs
  - agent context and allowed actions
  - screen buffer / telemetry panels

## Reference Repositories

### `Dimillian/Pocodex`

- URL: https://github.com/Dimillian/Pocodex
- Local reference clone: `/home/gilgames/Code/github-clones/Dimillian-Pocodex`
- Inspected commit: `e4e7aeb3b8152effb03da0fde65eeba5b027fa44`

Key files inspected:

- `README.md`
- `TELEMETRY_RUNTIME_PLAN.md`
- `tools/runtime/README.md`
- `tools/runtime/runtime_core.py`
- `tools/runtime/symbols.py`
- `tools/runtime/telemetry.py`
- `tools/runtime/controls.py`
- `tools/runtime/codex_client.py`
- `tools/runtime/agent_service.py`
- `tools/runtime/static/app.js`
- top-level `runtime`
- top-level `agent-runner`

Observed architecture:

- Pocodex is a `pret/pokered` fork plus a local programmable runtime.
- Fork additions are primarily under `tools/runtime/` plus top-level launchers.
- Runtime uses PyBoy for Game Boy/Game Boy Color execution.
- Runtime exposes HTTP endpoints such as `/health`, `/snapshot`, `/telemetry`, `/agent_context`, `/action`, `/execute_action`, `/states`, `/save_state`, `/load_state`, `/traces`, `/routine`, `/planner_step`, and built-in agent endpoints.
- Telemetry is symbol-aware through generated `.sym` files, with direct reads of Game Boy symbols such as `wTileMap`, `wCurMap`, `wXCoord`, `wYCoord`, `wIsInBattle`, `hJoyPressed`, party state, bag state, badge state, and event flags.
- UI is intentionally minimal and integration-focused, not a final polished app.
- Agent control uses `codex app-server` over stdio, a small dynamic tool set, validated runtime actions, action traces, and a planner-safe observe-decide-act-verify loop.

Useful pieces to port conceptually:

- HTTP API shape
- web control deck structure
- action whitelist and validation
- quick save/load state model
- recent traces and event logs
- `agent_context` as the compact model-facing contract
- Codex `app-server` bridge and model/reasoning selectors
- separate runtime controller loop

Pieces that cannot be copied directly:

- PyBoy-specific emulator core
- Game Boy memory addressing assumptions
- `pokered` symbol names and `.sym` parser assumptions
- `wTileMap` text/dialogue/menu extraction
- Gen 1 party, bag, badge, event, map, and navigation readers

### `pret/pokefirered`

- URL: https://github.com/pret/pokefirered
- Local reference clone: `/home/gilgames/Code/github-clones/pret-pokefirered`
- Inspected commit: `b8560820f3717a65f0cc8758297d021c1064a391`

Key files inspected:

- `README.md`
- `INSTALL.md`
- `Makefile`
- `config.mk`
- `ld_script.ld`
- `ld_script_rev10.ld`
- `sym_ewram.txt`
- `sym_bss.txt`
- `sym_common.txt`
- `include/global.h`
- `src/main.c`
- `src/event_data.c`
- `src/fieldmap.c`
- `data/maps/*/map.json`
- `data/layouts/*/map.bin`

Build facts:

- `pokefirered` builds multiple targets:
  - `firered`
  - `firered_rev1`
  - `firered_switch`
  - `leafgreen`
  - `leafgreen_rev1`
  - `leafgreen_switch`
- `config.mk` defaults to `GAME_VERSION=FIRERED` and `GAME_REVISION=0`.
- `Makefile` defines `ELF`, `MAP`, and `SYM` outputs:
  - `poke$(BUILD_NAME).elf`
  - `poke$(BUILD_NAME).map`
  - `poke$(BUILD_NAME).sym`
- `make syms` creates a `.sym` file from `arm-none-eabi-objdump -t`.
- For Rev 1 builds, the standard linker script still uses non-Rev10 symbol layout files; Rev10 has separate `sym_*_rev10.txt`.

FireRed/LeafGreen runtime implications:

- This is a GBA decompilation, not a Game Boy disassembly.
- Runtime telemetry should read GBA EWRAM/IWRAM/ROM addresses, not GB WRAM/HRAM.
- Critical game state is represented by C structs and pointers, not simple fixed Gen 1 `w*` globals.
- `include/global.h` defines `struct SaveBlock1` and `struct SaveBlock2`.
- `struct SaveBlock1` includes:
  - `pos` at offset `0x0000`
  - `location` at offset `0x0004`
  - `playerPartyCount` at offset `0x0034`
  - `playerParty` at offset `0x0038`
  - `money` at offset `0x0290`
  - bag pockets starting at `0x0310`
  - flags at `0x0EE0`
  - vars at `0x1000`
  - object events at `0x06A0`
- `struct SaveBlock2` includes:
  - `playerName` at offset `0x000`
  - `playerGender` at offset `0x008`
  - trainer id at `0x00A`
  - play time at `0x00E`
  - `encryptionKey` at `0xF20`
- `src/main.c` initializes `gSaveBlock1Ptr` and `gSaveBlock2Ptr`.
- `src/event_data.c` accesses flags and variables through `gSaveBlock1Ptr`.
- `src/fieldmap.c` uses `gSaveBlock1Ptr->pos` for camera/player position and `gMapHeader` for map layout/connection behavior.
- Map data is already available as JSON under `data/maps/*/map.json`.
- Layout binary data exists under `data/layouts/*/map.bin` and `border.bin`.

## User ROM Inventory

The user's ROM directory includes:

- `/mnt/c/Emulation/ROMs/Game Boy Advance/Pokemon - FireRed Version (USA, Europe) (Rev 1).gba`
- `/mnt/c/Emulation/ROMs/Game Boy Advance/Pokemon - LeafGreen Version (USA, Europe) (Rev 1).gba`
- `/mnt/c/Emulation/ROMs/Game Boy Advance/Pokemon - Emerald Version (USA, Europe).gba`
- `/mnt/c/Emulation/ROMs/Game Boy Color/Pokemon - Crystal Version (USA, Europe) (Rev 1).gbc`
- `/mnt/c/Emulation/ROMs/Game Boy Color/Pokemon - Gold Version (USA, Europe) (SGB Enhanced) (GB Compatible).gbc`
- `/mnt/c/Emulation/ROMs/Game Boy Color/Pokemon - Silver Version (USA, Europe) (SGB Enhanced) (GB Compatible).gbc`

Verified SHA-1 values:

```text
dd5945db9b930750cb39d00c84da8571feebf417  /mnt/c/Emulation/ROMs/Game Boy Advance/Pokemon - FireRed Version (USA, Europe) (Rev 1).gba
7862c67bdecbe21d1d69ce082ce34327e1c6ed5e  /mnt/c/Emulation/ROMs/Game Boy Advance/Pokemon - LeafGreen Version (USA, Europe) (Rev 1).gba
```

These match the Rev 1 SHA-1 targets listed by `pret/pokefirered`:

- `pokefirered_rev1.gba` SHA-1 `dd5945db9b930750cb39d00c84da8571feebf417`
- `pokeleafgreen_rev1.gba` SHA-1 `7862c67bdecbe21d1d69ce082ce34327e1c6ed5e`

Conclusion:

- The first runtime target should be `firered_rev1`.
- LeafGreen Rev 1 can be added after the FireRed runtime adapter works.
- ROM files must remain local-only and outside git.

## Emulator And Runtime Options

### Option A: Separate dedicated runtime emulator instance

Status: confirmed preferred direction.

Shape:

- Run a dedicated emulator instance for the automation runtime.
- Point the runtime at the user's local FireRed/LeafGreen ROM paths.
- Keep the user's live Mesen2 play sessions separate.
- Store runtime savestates/traces under repo-local ignored directories.

Why this is the recommended default:

- Protects the user's real saves and current play sessions.
- Gives deterministic checkpoints for agent testing.
- Makes action traces and reproduction cleaner.
- Allows runtime-specific emulator configuration.
- Keeps the Codex/web UI loop independent from casual play.

### Option B: Attach to existing Mesen2 session

Observed local emulator:

- `/mnt/c/Emulation/Emulators/Mesen/Mesen.exe`

Possible because Mesen2 has Lua/memory/input APIs, but this path has higher uncertainty:

- Mesen2 v2 API documentation appears less stable and less official than mGBA's scripting docs.
- Attaching to a live play session risks save corruption or unwanted input.
- The integration would be Windows-app-centric instead of runtime-centric.

This is a future nice-to-have, not the first implementation path.

### Option C: mGBA bridge

Status: accepted as first emulator bridge target on 2026-06-04.

Evidence from official mGBA docs and repository:

- mGBA supports Game Boy Advance and Game Boy/Game Boy Color.
- mGBA includes Lua scripting.
- Lua API exposes:
  - `emu:read8`, `read16`, `read32`
  - `emu:write8`, `write16`, `write32`
  - `emu:currentFrame`
  - `emu:runFrame`
  - `emu:screenshot`
  - `emu:saveStateBuffer`, `loadStateBuffer`, `saveStateFile`, `loadStateFile`
  - `emu:addKey`, `clearKey`, `setKeys`, `getKeys`
  - GBA memory domains such as EWRAM at `0x02000000`, IWRAM at `0x03000000`, VRAM at `0x06000000`, ROM at `0x08000000`
  - Lua sockets through `socket.bind`, `socket.connect`, `receive`, `send`
- mGBA also supports a command-line debugger and GDB remote support.

Likely strengths:

- Clean GBA fit.
- Official memory/input/savestate APIs.
- Potential Lua socket bridge directly to Python runtime.
- Cross-platform and not tied to Mesen2's current UI session.

Risks to validate:

- Confirm how to launch mGBA with a Lua script non-interactively on Windows or WSL.
- Confirm headless or windowed behavior for local runtime use.
- Confirm screenshot capture quality and frame timing.

### Option D: BizHawk bridge

Evidence from BizHawk docs and ecosystem:

- BizHawk supports GBA via mGBA core.
- It has mature Lua scripting, memory domains, joypad APIs, savestates, screenshots, and command-line `--lua` launching.
- Existing Pokemon memory-reader projects use BizHawk Lua to expose Gen 1-3 Pokemon state.

Likely strengths:

- Strong automation/TAS ecosystem.
- Script launch and external process behavior may be easier than mGBA.
- Windows-native and well suited to savestate/input workflows.

Risks:

- Adds another emulator installation.
- More Windows-centric than a pure WSL Python runtime.
- Need to verify GBA memory domains and IPC strategy.

## Architecture Hypothesis

Create a new `pret/pokefirered`-based repo with a runtime package modeled after Pocodex, but with explicit platform/game adapters.

Possible structure:

```text
tools/runtime/
  README.md
  requirements.txt
  server.py
  runtime_app.py
  runtime_core.py
  emulators/
    base.py
    mgba_bridge.py
    bizhawk_bridge.py
  games/
    firered/
      symbols.py
      telemetry.py
      save_blocks.py
      map_data.py
      text.py
      controls.py
  agent_context.py
  action_executor.py
  trace_recorder.py
  codex_client.py
  agent_service.py
  static/
    index.html
    styles.css
    app.js
```

The important boundary:

- `runtime_core` should not know FireRed struct details.
- `games/firered` owns symbol resolution, offsets, map data, text decoding, telemetry, and action affordances.
- `emulators/*` owns launch, frame stepping, screenshots, memory reads/writes, button presses, and savestates.

## First Minimal Spike

A good first implementation plan should prove the narrowest useful loop:

1. Configure a FireRed Rev 1 ROM path from local config or environment.
2. Launch a dedicated emulator instance.
3. Read a frame/screenshot.
4. Press/release a button.
5. Read a minimal telemetry snapshot:
   - frame count
   - ROM identity/hash
   - current callback or mode heuristic if available
   - raw `gSaveBlock1Ptr` and `gSaveBlock2Ptr` pointer values
   - player/camera coordinates from `gSaveBlock1Ptr->pos`
   - current map group/number from `gSaveBlock1Ptr->location`
6. Expose `/health`, `/snapshot`, `/action`, and `/telemetry`.
7. Serve a basic web control deck.

Success criteria:

- Runtime can launch FireRed Rev 1 from the user's local ROM path.
- Browser can show a live frame.
- Manual input from the web UI changes game state.
- Telemetry updates after input.
- Runtime savestates/traces are separate from the user's normal emulator saves.

## Resolved Planning Choices

- The first runtime instance should use a visible dedicated mGBA window by default; headless mode can be added later after bridge behavior is proven.
- The current empty workspace should be bootstrapped from `pret/pokefirered` before adding runtime files.
- The first spike should use the existing owned ROM path under `C:\Emulation` through ignored local configuration instead of copying the ROM into the repo.
- First-spike telemetry should stop at ROM identity, raw save-block pointers, map/location, and player/camera coordinates. Rich party, bag, battle, menu, text, and event telemetry belongs in follow-up plans.

Related decision:

- `.vault/decisions/first-spike-scope-boundaries-2026-06-04.md`

## Remaining Open Questions

1. Which exact mGBA executable path should local runtime configuration use on this machine?
2. Does mGBA Lua/socket launch reliably from WSL, or does the process need to launch through Windows shell integration?
3. Should symbol/struct metadata be generated from source or maintained as explicit constants after implementation evidence exists?

## Accepted Bridge Decision

Use mGBA as the first emulator bridge target, with BizHawk as the fallback if
mGBA's Windows launch, Lua/socket IPC, screenshot capture, frame/input control,
or memory access proves too awkward for the first spike.

Related decision:

- `.vault/decisions/mgba-first-runtime-bridge-2026-06-04.md`

Reason:

- mGBA is directly GBA-focused, cross-platform, and officially exposes the memory/input/savestate primitives needed by this project.
- BizHawk is the strongest fallback because it is mature for scripting and external automation, especially on Windows.
