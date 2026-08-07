"""Tests for runtime configuration, target identity, and storage."""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path

import pytest

from tools.runtime.config import (
    AgentConfig,
    ConfigError,
    MgbaConfig,
    RuntimeConfig,
    RuntimePaths,
    TargetConfig,
    load_runtime_config,
)
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.games.firered.symbols import (
    FIRERED_REV1_RUNTIME_SYMBOLS,
    SymbolTable,
    SymbolValidationError,
    validate_firered_rev1_runtime_symbols,
)
from tools.runtime.games.leafgreen.telemetry import LeafGreenTelemetryReader
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.runtime_factory import (
    create_runtime_from_config,
    create_runtime_from_config_path,
)
from tools.runtime.state_slots import StateSlotError
from tools.runtime.storage import (
    prepare_disposable_rom,
    target_scoped_runtime_paths,
)
from tools.runtime.target_profiles import get_target_profile


def write_config(path: Path, rom_path: Path) -> None:
    path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

def test_missing_rom_config_should_fail_fast(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.local.toml"
    missing_rom_path = tmp_path / "missing.gba"
    write_config(config_path, missing_rom_path)

    with pytest.raises(ConfigError, match="ROM path does not exist"):
        load_runtime_config(config_path)

def test_fixture_rom_config_should_load_runtime_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.local.toml"
    fixture_rom_path = tmp_path / "fixtures" / "firered_rev1.gba"
    fixture_rom_path.parent.mkdir()
    fixture_rom_path.write_bytes(b"fixture rom")
    write_config(config_path, fixture_rom_path)

    config = load_runtime_config(config_path)

    assert config.target.game == "firered"
    assert config.target.revision == "rev1"
    assert config.target.rom_path == fixture_rom_path
    assert config.target.symbol_path is None
    assert config.mgba.executable == "mgba"
    assert config.mgba.lua_bridge == Path("tools/runtime/emulators/mgba_bridge.lua")
    assert config.mgba.host == "127.0.0.1"
    assert config.mgba.bind_host is None
    assert config.mgba.port == 8766
    assert config.mgba.windows_paths is False
    assert config.mgba.connection_mode == "lua_server"
    assert config.mgba.frame_advance_mode == "lua_run_frame"
    assert config.mgba.script_cache_dir is None
    assert config.mgba.log_file is None
    assert config.runtime.state_dir == Path(".runtime-state")
    assert config.runtime.trace_dir == Path(".runtime-traces")
    assert config.runtime.log_dir == Path(".runtime-logs")
    assert config.runtime.screenshot_dir == Path(".runtime-screenshots")
    assert config.runtime.cache_dir == Path(".runtime-cache")
    assert config.agent.mode == "disabled"
    assert config.agent.executable == "codex"
    assert config.agent.model is None
    assert config.agent.reasoning_effort is None

def test_windows_mgba_config_should_load_bridge_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.local.toml"
    fixture_rom_path = tmp_path / "fixtures" / "firered_rev1.gba"
    fixture_rom_path.parent.mkdir()
    fixture_rom_path.write_bytes(b"fixture rom")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{fixture_rom_path}"
verify_hash = false

[mgba]
executable = "/mnt/c/Emulation/Emulators/mGBA-dev/mGBA.exe"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"
host = "127.0.0.1"
port = 8766
windows_paths = true
connection_mode = "lua_client"
frame_advance_mode = "realtime_wait"
script_cache_dir = "/mnt/c/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache"
log_file = "/mnt/c/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache/mgba_bridge.log"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.mgba.windows_paths is True
    assert config.mgba.connection_mode == "lua_client"
    assert config.mgba.frame_advance_mode == "realtime_wait"
    assert config.mgba.script_cache_dir == Path("/mnt/c/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache")
    assert config.mgba.log_file == Path("/mnt/c/Emulation/Emulators/mGBA-dev/pokemon-runtime-cache/mgba_bridge.log")

def test_runtime_config_should_load_optional_symbol_path(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.local.toml"
    fixture_rom_path = tmp_path / "fixtures" / "firered_rev1.gba"
    symbol_path = tmp_path / "pokefirered_rev1.sym"
    fixture_rom_path.parent.mkdir()
    fixture_rom_path.write_bytes(b"fixture rom")
    symbol_path.write_text("03005008 gSaveBlock1Ptr\n", encoding="utf-8")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{fixture_rom_path}"
symbol_path = "{symbol_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.target.symbol_path == symbol_path

def test_runtime_config_should_load_agent_section(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.local.toml"
    fixture_rom_path = tmp_path / "fixtures" / "firered_rev1.gba"
    fixture_rom_path.parent.mkdir()
    fixture_rom_path.write_bytes(b"fixture rom")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{fixture_rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"

[agent]
mode = "app_server"
executable = "codex"
model = "gpt-5"
reasoning_effort = "medium"
""",
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.agent.mode == "app_server"
    assert config.agent.executable == "codex"
    assert config.agent.model == "gpt-5"
    assert config.agent.reasoning_effort == "medium"

def test_runtime_config_should_reject_unknown_agent_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.local.toml"
    fixture_rom_path = tmp_path / "fixtures" / "firered_rev1.gba"
    fixture_rom_path.parent.mkdir()
    fixture_rom_path.write_bytes(b"fixture rom")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{fixture_rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"

[agent]
mode = "raw"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="invalid config value for mode"):
        load_runtime_config(config_path)

def test_runtime_factory_should_create_configured_firered_runtime_without_launch(tmp_path: Path, monkeypatch) -> None:
    rom_path = tmp_path / "firered_rev1.gba"
    config_path = tmp_path / "runtime.local.toml"
    rom_path.write_bytes(b"fixture rom")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    runtime = create_runtime_from_config_path(config_path, launch=False)
    telemetry = runtime.telemetry()

    assert telemetry["game"] == "firered"
    assert telemetry["revision"] == "rev1"
    assert telemetry["rom"]["available"] is True
    assert telemetry["symbols"]["available"] is False

def test_runtime_factory_should_auto_discover_default_firered_symbols(tmp_path: Path, monkeypatch) -> None:
    rom_path = tmp_path / "firered_rev1.gba"
    config_path = tmp_path / "runtime.local.toml"
    symbol_path = tmp_path / "pokefirered_rev1.sym"
    rom_path.write_bytes(b"fixture rom")
    symbol_path.write_text(
        """
03005008 gSaveBlock1Ptr
0300500c gSaveBlock2Ptr
02001000 gCamera
""",
        encoding="utf-8",
    )
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    runtime = create_runtime_from_config_path(config_path, launch=False)
    telemetry_reader = runtime._telemetry_reader

    assert telemetry_reader.symbols.coverage(("gSaveBlock1Ptr", "gSaveBlock2Ptr", "gCamera")).available is True
    assert telemetry_reader.symbols.source == symbol_path

def test_runtime_factory_should_configure_fake_agent_client(tmp_path: Path) -> None:
    rom_path = tmp_path / "firered_rev1.gba"
    config_path = tmp_path / "runtime.local.toml"
    rom_path.write_bytes(b"fixture rom")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"

[agent]
mode = "fake"
""",
        encoding="utf-8",
    )

    runtime = create_runtime_from_config_path(config_path, launch=False)

    assert runtime.agent_status()["client"]["mode"] == "fake"

def test_runtime_factory_should_create_configured_leafgreen_runtime_without_launch(tmp_path: Path) -> None:
    rom_path = tmp_path / "leafgreen_rev1.gba"
    config_path = tmp_path / "runtime.local.toml"
    rom_path.write_bytes(b"leafgreen fixture")
    config_path.write_text(
        f"""
[target]
game = "leafgreen"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

    runtime = create_runtime_from_config_path(config_path, launch=False)
    telemetry = runtime.telemetry()

    assert telemetry["game"] == "leafgreen"
    assert telemetry["revision"] == "rev1"
    assert telemetry["rom"]["expected_sha1"] == "7862c67bdecbe21d1d69ce082ce34327e1c6ed5e"

def test_runtime_factory_should_auto_discover_default_leafgreen_symbols(tmp_path: Path, monkeypatch) -> None:
    rom_path = tmp_path / "leafgreen_rev1.gba"
    config_path = tmp_path / "runtime.local.toml"
    symbol_path = tmp_path / "pokeleafgreen_rev1.sym"
    rom_path.write_bytes(b"leafgreen fixture")
    symbol_path.write_text("03005008 gSaveBlock1Ptr\n", encoding="utf-8")
    config_path.write_text(
        f"""
[target]
game = "leafgreen"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    runtime = create_runtime_from_config_path(config_path, launch=False)
    telemetry_reader = runtime._telemetry_reader

    assert telemetry_reader.symbols.source == symbol_path

def test_wrong_rom_hash_should_fail_target_profile(tmp_path: Path) -> None:
    rom_path = tmp_path / "not_firered.gba"
    config_path = tmp_path / "runtime.local.toml"
    rom_path.write_bytes(b"not the expected ROM")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{rom_path}"

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="ROM SHA-1 mismatch for Pokemon FireRed Rev 1"):
        load_runtime_config(config_path)

def test_hash_bypass_should_keep_mismatch_visible_for_fixtures(tmp_path: Path) -> None:
    rom_path = tmp_path / "fixture.gba"
    config_path = tmp_path / "runtime.local.toml"
    rom_path.write_bytes(b"fixture rom")
    config_path.write_text(
        f"""
[target]
game = "firered"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.target.verify_hash is False
    assert config.target.matches_expected is False
    assert config.target.expected_sha1 == get_target_profile("firered", "rev1").expected_sha1

def test_leafgreen_profile_should_load_expected_identity(tmp_path: Path) -> None:
    rom_path = tmp_path / "leafgreen_fixture.gba"
    config_path = tmp_path / "runtime.local.toml"
    rom_path.write_bytes(b"leafgreen fixture")
    config_path.write_text(
        f"""
[target]
game = "leafgreen"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = ".runtime-state"
trace_dir = ".runtime-traces"
log_dir = ".runtime-logs"
screenshot_dir = ".runtime-screenshots"
cache_dir = ".runtime-cache"
""",
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.target.profile.key == "leafgreen_rev1"
    assert config.target.profile.display_name == "Pokemon LeafGreen Rev 1"
    assert config.target.profile.symbol_basename == "pokeleafgreen_rev1.sym"
    assert config.target.expected_sha1 == "7862c67bdecbe21d1d69ce082ce34327e1c6ed5e"

def test_leafgreen_profile_should_select_leafgreen_adapter() -> None:
    profile = get_target_profile("leafgreen", "rev1")

    assert profile.adapter == "leafgreen"
    assert profile.symbol_basename == "pokeleafgreen_rev1.sym"
    assert is_dataclass(LeafGreenTelemetryReader)

def test_runtime_storage_should_stay_under_target_directory() -> None:
    paths = RuntimePaths(
        state_dir=Path(".runtime-state"),
        trace_dir=Path(".runtime-traces"),
        log_dir=Path(".runtime-logs"),
        screenshot_dir=Path(".runtime-screenshots"),
        cache_dir=Path(".runtime-cache"),
    )

    scoped = target_scoped_runtime_paths(paths, "firered_rev1")

    assert scoped.state_dir == Path(".runtime-state") / "firered_rev1"
    assert scoped.trace_dir == Path(".runtime-traces") / "firered_rev1"
    assert scoped.log_dir == Path(".runtime-logs") / "firered_rev1"
    assert scoped.screenshot_dir == Path(".runtime-screenshots") / "firered_rev1"
    assert scoped.cache_dir == Path(".runtime-cache") / "firered_rev1"

def test_runtime_storage_should_reject_unsafe_target_key() -> None:
    paths = RuntimePaths(
        state_dir=Path(".runtime-state"),
        trace_dir=Path(".runtime-traces"),
        log_dir=Path(".runtime-logs"),
        screenshot_dir=Path(".runtime-screenshots"),
        cache_dir=Path(".runtime-cache"),
    )

    with pytest.raises(ValueError, match="target profile key"):
        target_scoped_runtime_paths(paths, "../leafgreen")

def test_runtime_factory_should_scope_state_slots_by_target(tmp_path: Path) -> None:
    firered = _write_config(tmp_path, "firered", "firered fixture")
    leafgreen = _write_config(tmp_path, "leafgreen", "leafgreen fixture")

    firered_runtime = create_runtime_from_config_path(firered, launch=False)
    leafgreen_runtime = create_runtime_from_config_path(leafgreen, launch=False)

    assert firered_runtime.states.state_dir == tmp_path / ".runtime-state" / "firered_rev1"
    assert leafgreen_runtime.states.state_dir == tmp_path / ".runtime-state" / "leafgreen_rev1"

def _write_config(tmp_path: Path, game: str, contents: str) -> Path:
    rom_path = tmp_path / f"{game}.gba"
    config_path = tmp_path / f"{game}.toml"
    rom_path.write_bytes(contents.encode("ascii"))
    config_path.write_text(
        f"""
[target]
game = "{game}"
revision = "rev1"
rom_path = "{rom_path}"
verify_hash = false

[mgba]
executable = "mgba"
lua_bridge = "tools/runtime/emulators/mgba_bridge.lua"

[runtime]
state_dir = "{tmp_path / ".runtime-state"}"
trace_dir = "{tmp_path / ".runtime-traces"}"
log_dir = "{tmp_path / ".runtime-logs"}"
screenshot_dir = "{tmp_path / ".runtime-screenshots"}"
cache_dir = "{tmp_path / ".runtime-cache"}"
""",
        encoding="utf-8",
    )
    return config_path

def test_state_slot_should_save_and_load_runtime_owned_file(tmp_path) -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator, state_dir=tmp_path)
    emulator.run_frames(42)

    saved = runtime.save_state("quick")
    emulator.run_frames(5)
    loaded = runtime.load_state("quick")
    slots = runtime.list_states()["slots"]

    assert saved["ok"] is True
    assert loaded["ok"] is True
    assert emulator.frame_count == 42
    assert slots[0]["name"] == "quick"
    assert slots[0]["exists"] is True
    assert slots[0]["size_bytes"] > 0
    assert "path" not in slots[0]
    assert runtime.recent_traces()[-2]["detail"]["slot"] == "quick"

def test_state_slot_should_reject_path_like_slot_names(tmp_path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)

    with pytest.raises(StateSlotError, match="slot must be"):
        runtime.save_state("../outside")

    assert not list(tmp_path.iterdir())

def test_state_slot_should_reject_missing_load_slot(tmp_path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)

    with pytest.raises(StateSlotError, match="does not exist"):
        runtime.load_state("missing")

# Behavior tests for mGBA battery-save isolation.


def test_disposable_battery_save_should_stay_in_runtime_workspace(tmp_path: Path) -> None:
    """mGBA receives a runtime-owned ROM copy so its adjacent battery file is contained."""

    owned_rom = tmp_path / "owned" / "firered_rev1.gba"
    owned_rom.parent.mkdir()
    owned_rom.write_bytes(b"owned FireRed Rev 1 ROM")
    workspace = tmp_path / "runtime" / "firered_rev1" / "battery"

    disposable_rom = prepare_disposable_rom(owned_rom, workspace)

    assert disposable_rom == workspace / owned_rom.name
    assert disposable_rom.read_bytes() == owned_rom.read_bytes()
    assert disposable_rom != owned_rom
    assert disposable_rom.with_suffix(".sav").parent == workspace

def test_windows_mgba_checkpoint_should_stay_in_windows_runtime_workspace(tmp_path: Path) -> None:
    """Savestates use the Windows-visible cache because mGBA writes them directly."""

    rom_path = tmp_path / "firered_rev1.gba"
    rom_path.write_bytes(b"fixture")
    profile = get_target_profile("firered", "rev1")
    windows_cache = tmp_path / "windows-cache"
    config = RuntimeConfig(
        target=TargetConfig("firered", "rev1", profile, rom_path, None, False, "fixture", profile.expected_sha1, False),
        mgba=MgbaConfig("mgba", Path("bridge.lua"), "127.0.0.1", None, 8766, True, "lua_client", "realtime_wait", windows_cache, None),
        runtime=RuntimePaths(tmp_path / "states", tmp_path / "traces", tmp_path / "logs", tmp_path / "screens", tmp_path / "cache"),
        agent=AgentConfig("disabled", "codex", None, None),
    )

    runtime = create_runtime_from_config(config, launch=False, repo_root=tmp_path)

    assert runtime.states.state_dir == windows_cache / "states" / "firered_rev1"

# Behavior tests for binding generated FireRed symbols to a verified target.


def test_generated_symbols_with_unverified_rom_should_reject_runtime_telemetry() -> None:
    """A complete symbol file cannot override a failed FireRed Rev 1 hash check."""

    symbols = SymbolTable({name: 0x03000000 + index * 4 for index, name in enumerate(FIRERED_REV1_RUNTIME_SYMBOLS)})

    with pytest.raises(SymbolValidationError, match="verified FireRed Rev 1 ROM"):
        validate_firered_rev1_runtime_symbols(symbols, rom_matches_expected=False)

def test_generated_symbols_with_missing_runtime_symbol_should_reject_runtime_telemetry() -> None:
    """A verified ROM still needs all state readers before semantic telemetry activates."""

    symbols = SymbolTable({name: 0x03000000 + index * 4 for index, name in enumerate(FIRERED_REV1_RUNTIME_SYMBOLS[:-1])})

    with pytest.raises(SymbolValidationError, match="missing required symbols"):
        validate_firered_rev1_runtime_symbols(symbols, rom_matches_expected=True)
