from __future__ import annotations

from pathlib import Path

import pytest

from tools.runtime.config import ConfigError, load_runtime_config
from tools.runtime.target_profiles import get_target_profile


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
