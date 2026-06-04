from pathlib import Path

import pytest

from tools.runtime.config import ConfigError, load_runtime_config


def write_config(path: Path, rom_path: Path) -> None:
    path.write_text(
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
