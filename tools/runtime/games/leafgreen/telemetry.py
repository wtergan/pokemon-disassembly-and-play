"""LeafGreen Rev 1 telemetry reader."""

from __future__ import annotations

from dataclasses import dataclass

from ..firered.telemetry import FireRedTelemetryReader


@dataclass(frozen=True)
class LeafGreenTelemetryReader(FireRedTelemetryReader):
    """Callable telemetry reader for LeafGreen Rev 1 runtime state."""

    game: str = "leafgreen"
    revision: str = "rev1"
