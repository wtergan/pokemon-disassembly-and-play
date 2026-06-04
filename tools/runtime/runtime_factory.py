"""Build runtime cores from validated local configuration.

This module is the boundary between machine-specific config and the runtime's
portable app/core layers. It constructs emulator and game telemetry adapters,
optionally launches the emulator bridge, and leaves HTTP routing to
`runtime_app`.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from .config import RuntimeConfig, load_runtime_config
from .emulators.mgba_bridge import ConnectionMode, FrameAdvanceMode, MgbaLaunchConfig, MgbaSocketBridge
from .games.firered.map_data import try_load_map_registry
from .games.firered.symbols import discover_symbol_table
from .games.firered.telemetry import FireRedTelemetryReader
from .games.firered.text import try_load_charmap
from .runtime_core import RuntimeCore


def create_runtime_from_config_path(config_path: Path, launch: bool = True) -> RuntimeCore:
    """Load `config_path` and build the configured runtime core."""

    return create_runtime_from_config(load_runtime_config(config_path), launch=launch, repo_root=Path.cwd())


def create_runtime_from_config(config: RuntimeConfig, launch: bool = True, repo_root: Path | None = None) -> RuntimeCore:
    """Build a runtime core for the configured target and emulator."""

    emulator = _create_mgba_bridge(config)
    if launch:
        emulator.launch()
    telemetry_reader = _create_telemetry_reader(config, repo_root=repo_root or Path.cwd())
    return RuntimeCore(emulator, telemetry_reader=telemetry_reader, state_dir=config.runtime.state_dir)


def _create_mgba_bridge(config: RuntimeConfig) -> MgbaSocketBridge:
    return MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path(config.mgba.executable),
            rom_path=config.target.rom_path,
            lua_bridge=config.mgba.lua_bridge,
            host=config.mgba.host,
            bind_host=config.mgba.bind_host,
            port=config.mgba.port,
            windows_paths=config.mgba.windows_paths,
            connection_mode=cast(ConnectionMode, config.mgba.connection_mode),
            frame_advance_mode=cast(FrameAdvanceMode, config.mgba.frame_advance_mode),
            script_cache_dir=config.mgba.script_cache_dir,
            log_file=config.mgba.log_file,
        ),
        screenshot_dir=config.runtime.screenshot_dir,
    )


def _create_telemetry_reader(config: RuntimeConfig, repo_root: Path) -> FireRedTelemetryReader:
    if config.target.game != "firered" or config.target.revision != "rev1":
        raise ValueError(f"unsupported target: {config.target.game} {config.target.revision}")
    symbols = discover_symbol_table(repo_root, explicit_path=config.target.symbol_path)
    return FireRedTelemetryReader(
        symbols=symbols,
        rom_path=config.target.rom_path,
        map_registry=try_load_map_registry(repo_root),
        text_decoder=try_load_charmap(repo_root),
    )
