from __future__ import annotations

from pathlib import Path

import pytest

from tools.runtime.config import RuntimePaths
from tools.runtime.runtime_factory import create_runtime_from_config_path
from tools.runtime.storage import target_scoped_runtime_paths


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
