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
    symbol_path: Path | None


@dataclass(frozen=True)
class MgbaConfig:
    """mGBA executable and bridge script configuration."""

    executable: str
    lua_bridge: Path
    host: str
    bind_host: str | None
    port: int
    windows_paths: bool
    connection_mode: str
    frame_advance_mode: str
    script_cache_dir: Path | None
    log_file: Path | None


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
    symbol_path = _optional_path(target, "symbol_path")
    if symbol_path is not None and not symbol_path.exists():
        raise ConfigError(f"symbol path does not exist: {symbol_path}")

    return RuntimeConfig(
        target=TargetConfig(
            game=_required_str(target, "game").lower(),
            revision=_required_str(target, "revision").lower(),
            rom_path=rom_path,
            symbol_path=symbol_path,
        ),
        mgba=MgbaConfig(
            executable=_required_str(mgba, "executable"),
            lua_bridge=Path(_required_str(mgba, "lua_bridge")),
            host=_optional_str(mgba, "host", "127.0.0.1"),
            bind_host=_optional_str(mgba, "bind_host", None),
            port=_optional_int(mgba, "port", 8766),
            windows_paths=_optional_bool(mgba, "windows_paths", False),
            connection_mode=_optional_choice(mgba, "connection_mode", "lua_server", {"lua_server", "lua_client"}),
            frame_advance_mode=_optional_choice(
                mgba,
                "frame_advance_mode",
                "lua_run_frame",
                {"lua_run_frame", "realtime_wait"},
            ),
            script_cache_dir=_optional_path(mgba, "script_cache_dir"),
            log_file=_optional_path(mgba, "log_file"),
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


def _optional_str(data: dict[str, Any], name: str, default: str | None) -> str | None:
    value = data.get(name, default)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(f"invalid string config value: {name}")
    return value


def _optional_path(data: dict[str, Any], name: str) -> Path | None:
    value = _optional_str(data, name, None)
    if value is None:
        return None
    return Path(value)


def _optional_bool(data: dict[str, Any], name: str, default: bool) -> bool:
    value = data.get(name, default)
    if not isinstance(value, bool):
        raise ConfigError(f"invalid boolean config value: {name}")
    return value


def _optional_int(data: dict[str, Any], name: str, default: int) -> int:
    value = data.get(name, default)
    if not isinstance(value, int):
        raise ConfigError(f"invalid integer config value: {name}")
    return value


def _optional_choice(data: dict[str, Any], name: str, default: str, allowed: set[str]) -> str:
    value = _optional_str(data, name, default)
    if value not in allowed:
        raise ConfigError(f"invalid config value for {name}: {value}")
    return value
