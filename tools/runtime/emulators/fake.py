"""In-memory emulator bridge used by behavior tests and offline development."""

from __future__ import annotations

import base64
from pathlib import Path

from .base import EmulatorHealth, Snapshot


_ONE_PIXEL_PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000a49444154789c6360000002000100a5f645400000000"
        "049454e44ae426082"
    )
).decode("ascii")


class FakeEmulatorBridge:
    """Deterministic emulator substitute implementing the bridge contract."""

    def __init__(self, memory: bytes | None = None) -> None:
        self._frame_count = 0
        self._buttons: set[str] = set()
        self._memory = bytearray(memory or b"\x00" * 0x400)

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def pressed_buttons(self) -> frozenset[str]:
        return frozenset(self._buttons)

    def health(self) -> EmulatorHealth:
        return EmulatorHealth(running=True, frame=self._frame_count, bridge="fake")

    def snapshot(self) -> Snapshot:
        return Snapshot(frame=self._frame_count, image_base64=_ONE_PIXEL_PNG)

    def press_button(self, button: str) -> None:
        self._buttons.add(button)

    def release_button(self, button: str) -> None:
        self._buttons.discard(button)

    def run_frames(self, frames: int) -> None:
        self._frame_count += frames

    def read8(self, address: int) -> int:
        return self._memory[address]

    def read16(self, address: int) -> int:
        return int.from_bytes(self._memory[address : address + 2], "little")

    def read32(self, address: int) -> int:
        return int.from_bytes(self._memory[address : address + 4], "little")

    def save_state(self, path: Path) -> None:
        path.write_bytes(self._frame_count.to_bytes(8, "little") + ",".join(sorted(self._buttons)).encode("ascii"))

    def load_state(self, path: Path) -> None:
        data = path.read_bytes()
        self._frame_count = int.from_bytes(data[:8], "little")
