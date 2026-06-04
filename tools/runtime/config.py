"""Runtime configuration loading and validation.

The committed project provides only example configuration. Real ROM paths,
emulator paths, state directories, and trace locations are read from ignored
local config so user-owned game files and machine-specific paths stay out of
version control.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]


class ConfigError(ValueError):
    """Raised when runtime configuration is missing or unsafe."""


@dataclass(frozen=True)
class TargetConfig:
    """Selected Pokemon target and owned ROM path."""

    game: str
    revision: str
    rom_path: Path


@dataclass(frozen=True)
class MgbaConfig:
    """mGBA executable and bridge script configuration."""

    executable: str
    lua_bridge: Path


@dataclass(frozen=True)
class RuntimePaths:
    """Runtime-owned local artifact directories."""

    state_dir: Path
    trace_dir: Path
    log_dir: Path
    screenshot_dir: Path
    cache_dir: Path


@dataclass(frozen=True)
class RuntimeConfig:
    """Validated local runtime configuration."""

    target: TargetConfig
    mgba: MgbaConfig
    runtime: RuntimePaths


def load_runtime_config(path: Path) -> RuntimeConfig:
    """Load and validate runtime config from a TOML file."""

    if not path.exists():
        raise ConfigError(f"runtime config does not exist: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    target = _required_table(data, "target")
    mgba = _required_table(data, "mgba")
    runtime = _required_table(data, "runtime")

    rom_path = Path(_required_str(target, "rom_path")).expanduser()
    if not rom_path.exists():
        raise ConfigError(f"ROM path does not exist: {rom_path}")

    return RuntimeConfig(
        target=TargetConfig(
            game=_required_str(target, "game").lower(),
            revision=_required_str(target, "revision").lower(),
            rom_path=rom_path,
        ),
        mgba=MgbaConfig(
            executable=_required_str(mgba, "executable"),
            lua_bridge=Path(_required_str(mgba, "lua_bridge")),
        ),
        runtime=RuntimePaths(
            state_dir=Path(_required_str(runtime, "state_dir")),
            trace_dir=Path(_required_str(runtime, "trace_dir")),
            log_dir=Path(_required_str(runtime, "log_dir")),
            screenshot_dir=Path(_required_str(runtime, "screenshot_dir")),
            cache_dir=Path(_required_str(runtime, "cache_dir")),
        ),
    )


def _required_table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"missing [{name}] config section")
    return value


def _required_str(data: dict[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"missing string config value: {name}")
    return value

