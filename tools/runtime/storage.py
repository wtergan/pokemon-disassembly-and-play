"""Runtime storage helpers with target-profile path containment.

Config files provide root directories for runtime-owned artifacts. This module
maps those roots to per-target directories so FireRed and LeafGreen savestates,
screenshots, traces, logs, and cache files do not share mutable paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
from typing import Protocol


PROFILE_KEY_RE = re.compile(r"^[a-z0-9_]+$")


class RuntimePathRoots(Protocol):
    """Runtime path roots loaded from local configuration."""

    state_dir: Path
    trace_dir: Path
    log_dir: Path
    screenshot_dir: Path
    cache_dir: Path


@dataclass(frozen=True)
class RuntimeStoragePaths:
    """Target-scoped runtime-owned artifact directories."""

    state_dir: Path
    trace_dir: Path
    log_dir: Path
    screenshot_dir: Path
    cache_dir: Path


def target_scoped_runtime_paths(paths: RuntimePathRoots, profile_key: str) -> RuntimeStoragePaths:
    """Return target-scoped paths contained under each configured root."""

    if not PROFILE_KEY_RE.match(profile_key):
        raise ValueError("target profile key must contain only lowercase letters, numbers, or underscores")
    return RuntimeStoragePaths(
        state_dir=_scoped(paths.state_dir, profile_key),
        trace_dir=_scoped(paths.trace_dir, profile_key),
        log_dir=_scoped(paths.log_dir, profile_key),
        screenshot_dir=_scoped(paths.screenshot_dir, profile_key),
        cache_dir=_scoped(paths.cache_dir, profile_key),
    )


def prepare_disposable_rom(owned_rom: Path, workspace: Path) -> Path:
    """Copy `owned_rom` into a contained mGBA battery-save workspace.

    mGBA derives its battery-save filename from the ROM path. Launching the
    copy therefore forces the adjacent `.sav` file to remain runtime-owned,
    while configuration hash validation continues to identify the original ROM.
    """

    source = owned_rom.expanduser().resolve()
    root = workspace.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    destination = (root / source.name).resolve()
    if destination.parent != root:
        raise ValueError("disposable ROM path escaped runtime workspace")
    shutil.copy2(source, destination)
    return destination


def _scoped(root: Path, profile_key: str) -> Path:
    resolved_root = root.expanduser()
    return resolved_root / profile_key
