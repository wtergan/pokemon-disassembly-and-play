from __future__ import annotations

from pathlib import Path

import tools.runtime.emulators.mgba_bridge as mgba_bridge_module
from tools.runtime.emulators.mgba_bridge import MgbaLaunchConfig, MgbaSocketBridge, add_wslenv_exports


def test_mgba_launch_command_should_include_script_and_rom(tmp_path: Path) -> None:
    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("/opt/mgba/mgba-qt"),
            rom_path=Path("/roms/firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
        ),
        screenshot_dir=tmp_path,
    )

    assert bridge.build_launch_command() == [
        "/opt/mgba/mgba-qt",
        "--script",
        "tools/runtime/emulators/mgba_bridge.lua",
        "/roms/firered.gba",
    ]


def test_mgba_windows_launch_command_should_stage_lua_script(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lua_bridge = tmp_path / "mgba_bridge.lua"
    lua_bridge.write_text("-- test bridge\n", encoding="utf-8")
    cache_dir = tmp_path / "windows-cache"

    def fake_wsl_to_windows_path(path: Path) -> str:
        return "C:\\" + str(path).replace("/", "\\").lstrip("\\")

    monkeypatch.setattr(mgba_bridge_module, "wsl_to_windows_path", fake_wsl_to_windows_path)
    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("/mnt/c/Emulation/mGBA/mGBA.exe"),
            rom_path=Path("/mnt/c/roms/firered.gba"),
            lua_bridge=lua_bridge,
            windows_paths=True,
            script_cache_dir=cache_dir,
        ),
        screenshot_dir=tmp_path / "screenshots",
    )

    command = bridge.build_launch_command()

    assert command[0] == "/mnt/c/Emulation/mGBA/mGBA.exe"
    assert command[1] == "--script"
    assert command[2].endswith("\\windows-cache\\mgba_bridge.lua")
    assert command[3].endswith("\\mnt\\c\\roms\\firered.gba")
    assert (cache_dir / "mgba_bridge.lua").read_text(encoding="utf-8") == "-- test bridge\n"


def test_mgba_windows_env_should_export_runtime_variables_to_win32() -> None:
    env = {
        "WSLENV": "EXISTING/w",
        "POKEMON_RUNTIME_HOST": "127.0.0.1",
        "POKEMON_RUNTIME_PORT": "8766",
    }

    updated = add_wslenv_exports(env, ["POKEMON_RUNTIME_HOST", "POKEMON_RUNTIME_BIND_HOST", "POKEMON_RUNTIME_PORT"])

    assert updated["WSLENV"] == "EXISTING/w:POKEMON_RUNTIME_HOST/w:POKEMON_RUNTIME_PORT/w"
    assert env["WSLENV"] == "EXISTING/w"
