from __future__ import annotations

from pathlib import Path

from tools.runtime.runtime_factory import create_runtime_from_config_path


def test_runtime_factory_should_create_configured_firered_runtime_without_launch(tmp_path: Path) -> None:
    rom_path = tmp_path / "firered_rev1.gba"
    config_path = tmp_path / "runtime.local.toml"
    rom_path.write_bytes(b"fixture rom")
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
