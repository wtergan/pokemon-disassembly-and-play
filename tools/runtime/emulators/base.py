"""Emulator bridge contract used by runtime core and game adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Snapshot:
    """A captured emulator frame suitable for browser or API transport."""

    frame: int
    image_base64: str
    mime_type: str = "image/png"


@dataclass(frozen=True)
class EmulatorHealth:
    """Observable bridge health without exposing private local configuration."""

    running: bool
    frame: int
    bridge: str
    detail: str = ""


class EmulatorBridge(Protocol):
    """Small primitive interface implemented by mGBA, BizHawk, or test fakes."""

    @property
    def frame_count(self) -> int:
        """Current emulator frame count."""

    def health(self) -> EmulatorHealth:
        """Return current bridge health."""

    def snapshot(self) -> Snapshot:
        """Capture the current frame."""

    def press_button(self, button: str) -> None:
        """Press one whitelisted input button."""

    def release_button(self, button: str) -> None:
        """Release one whitelisted input button."""

    def run_frames(self, frames: int) -> None:
        """Advance the emulator by `frames` frames."""

    def read8(self, address: int) -> int:
        """Read an unsigned byte from emulator memory."""

    def read16(self, address: int) -> int:
        """Read a little-endian unsigned halfword from emulator memory."""

    def read32(self, address: int) -> int:
        """Read a little-endian unsigned word from emulator memory."""

    def save_state(self, path: Path) -> None:
        """Save emulator state to a runtime-owned path."""

    def load_state(self, path: Path) -> None:
        """Load emulator state from a runtime-owned path."""
