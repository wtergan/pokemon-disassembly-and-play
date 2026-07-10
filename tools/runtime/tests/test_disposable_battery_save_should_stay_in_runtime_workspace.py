"""Behavior tests for mGBA battery-save isolation."""

from __future__ import annotations

from pathlib import Path

from tools.runtime.config import AgentConfig, MgbaConfig, RuntimeConfig, RuntimePaths, TargetConfig
from tools.runtime.runtime_factory import create_runtime_from_config
from tools.runtime.storage import prepare_disposable_rom
from tools.runtime.target_profiles import get_target_profile


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
