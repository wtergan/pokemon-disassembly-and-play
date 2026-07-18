"""Cache bounded memory pages for one FireRed telemetry observation.

The mGBA bridge services requests once per frame. Save decoding must reuse
pages within one observation rather than issue thousands of scalar requests.
Create a new view for each observation so data never survives into a later one.
"""

from __future__ import annotations

from typing import Any


class BufferedMemory:
    """Read little-endian values from per-observation 4 KiB memory pages."""

    def __init__(self, emulator: Any) -> None:
        self._emulator = emulator
        self._pages: dict[int, bytes] = {}

    @property
    def frame_count(self) -> int:
        return self._emulator.frame_count

    def read8(self, address: int) -> int:
        base = address & ~4095
        if base not in self._pages:
            self._pages[base] = self._emulator.read_range(base, 4096)
        return self._pages[base][address - base]

    def read16(self, address: int) -> int:
        return self.read8(address) | (self.read8(address + 1) << 8)

    def read32(self, address: int) -> int:
        return self.read16(address) | (self.read16(address + 2) << 16)
