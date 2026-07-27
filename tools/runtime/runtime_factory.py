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
from .codex_client import CodexAppServerClient, FakeAgentClient
from .emulators.mgba_bridge import ConnectionMode, FrameAdvanceMode, MgbaLaunchConfig, MgbaSocketBridge
from .games.firered.map_data import try_load_map_registry
from .games.firered.symbols import (
    FIRERED_REV1_RUNTIME_SYMBOLS,
    discover_symbol_table,
    validate_firered_rev1_runtime_symbols,
)
from .games.firered.telemetry import FireRedTelemetryReader
from .games.firered.text import try_load_charmap
from .games.leafgreen.telemetry import LeafGreenTelemetryReader
from .runtime_core import RuntimeCore
from .storage import target_scoped_runtime_paths


def create_runtime_from_config_path(config_path: Path, launch: bool = True) -> RuntimeCore:
    """Load `config_path` and build the configured runtime core."""

    return create_runtime_from_config(load_runtime_config(config_path), launch=launch, repo_root=Path.cwd())


def create_runtime_from_config(config: RuntimeConfig, launch: bool = True, repo_root: Path | None = None) -> RuntimeCore:
    """Build a runtime core for the configured target and emulator."""

    telemetry_reader = _create_telemetry_reader(config, repo_root=repo_root or Path.cwd())
    storage = target_scoped_runtime_paths(config.runtime, config.target.profile.key)
    battery_workspace = storage.cache_dir / "battery"
    if config.mgba.windows_paths and config.mgba.script_cache_dir is not None:
        # Windows mGBA cannot read the Linux-only worktree. Reuse the existing
        # Windows-visible staging root while retaining a target-scoped battery
        # subdirectory.
        battery_workspace = config.mgba.script_cache_dir / "battery" / config.target.profile.key
    emulator = _create_mgba_bridge(
        config,
        screenshot_dir=storage.screenshot_dir,
        battery_workspace=battery_workspace,
    )
    state_dir = storage.state_dir
    if config.mgba.windows_paths and config.mgba.script_cache_dir is not None:
        # Savestates are written by mGBA, so they require the same
        # Windows-visible staging boundary as the disposable ROM/battery file.
        state_dir = config.mgba.script_cache_dir / "states" / config.target.profile.key
    runtime = RuntimeCore(emulator, telemetry_reader=telemetry_reader, state_dir=state_dir)
    try:
        _configure_agent(runtime, config, repo_root=repo_root or Path.cwd())
        if launch:
            emulator.launch()
    except Exception:
        runtime.close()
        raise
    return runtime


def _create_mgba_bridge(config: RuntimeConfig, *, screenshot_dir: Path, battery_workspace: Path) -> MgbaSocketBridge:
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
            battery_workspace=battery_workspace,
        ),
        screenshot_dir=screenshot_dir,
    )


def _create_telemetry_reader(config: RuntimeConfig, repo_root: Path) -> FireRedTelemetryReader:
    if config.target.revision != "rev1" or config.target.profile.adapter not in {"firered", "leafgreen"}:
        raise ValueError(f"unsupported target: {config.target.game} {config.target.revision}")
    symbols = discover_symbol_table(
        repo_root,
        explicit_path=config.target.symbol_path,
        symbol_basename=config.target.profile.symbol_basename,
        build_name=config.target.profile.build_name,
    )
    if config.target.profile.adapter == "firered" and (
        symbols.coverage(FIRERED_REV1_RUNTIME_SYMBOLS).available
        or (config.target.verify_hash and symbols.source is not None)
    ):
        # Fixture configs may deliberately disable hashing. Real local configs
        # default to verification and cannot reach this point on a mismatch.
        validate_firered_rev1_runtime_symbols(
            symbols,
            rom_matches_expected=config.target.matches_expected or not config.target.verify_hash,
        )
    reader_class = FireRedTelemetryReader if config.target.profile.adapter == "firered" else LeafGreenTelemetryReader
    return reader_class(
        symbols=symbols,
        rom_path=config.target.rom_path,
        map_registry=try_load_map_registry(repo_root),
        text_decoder=try_load_charmap(repo_root),
        expected_sha1=config.target.expected_sha1,
    )


def _configure_agent(runtime: RuntimeCore, config: RuntimeConfig, repo_root: Path) -> None:
    if config.agent.mode == "fake":
        runtime.configure_agent_client(FakeAgentClient())
    elif config.agent.mode == "app_server":
        runtime.configure_agent_client(
            CodexAppServerClient(
                repo_root=repo_root,
                executable=config.agent.executable,
                model=config.agent.model,
                reasoning_effort=config.agent.reasoning_effort,
                snapshot_provider=runtime.snapshot,
            )
        )
