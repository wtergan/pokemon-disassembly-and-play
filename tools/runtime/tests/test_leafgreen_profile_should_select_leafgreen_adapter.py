from __future__ import annotations

from dataclasses import is_dataclass

from tools.runtime.games.leafgreen.telemetry import LeafGreenTelemetryReader
from tools.runtime.target_profiles import get_target_profile


def test_leafgreen_profile_should_select_leafgreen_adapter() -> None:
    profile = get_target_profile("leafgreen", "rev1")

    assert profile.adapter == "leafgreen"
    assert profile.symbol_basename == "pokeleafgreen_rev1.sym"
    assert is_dataclass(LeafGreenTelemetryReader)
