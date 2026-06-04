from __future__ import annotations

from pathlib import Path

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.state_models import TELEMETRY_SCHEMA_VERSION, normalize_telemetry_snapshot
from tools.runtime.tests.http_client import request


def test_empty_runtime_telemetry_should_publish_unavailable_schema() -> None:
    telemetry = RuntimeCore(FakeEmulatorBridge()).telemetry()

    assert telemetry["schema_version"] == TELEMETRY_SCHEMA_VERSION
    assert telemetry["target"] == {"game": "unknown", "revision": "unknown"}
    assert telemetry["runtime"] == {"frame": 0}
    assert telemetry["location"] == {"available": False, "reason": "not_reported", "section": "location"}
    assert telemetry["capabilities"] == {
        "symbols": False,
        "location": False,
        "mode": False,
        "camera": False,
        "save": False,
        "party": False,
    }


def test_telemetry_normalizer_should_preserve_explicit_unavailable_sections() -> None:
    telemetry = normalize_telemetry_snapshot(
        {
            "game": "firered",
            "revision": "rev1",
            "frame": 123,
            "symbols": {"available": False, "source": Path("/private/pokefirered_rev1.sym")},
            "location": {"available": False, "reason": "missing_save_block_1"},
            "mode": {"name": "unknown", "confidence": "low"},
            "save": {"available": False, "reason": "missing_save_block_1"},
        }
    )

    assert telemetry["target"] == {"game": "firered", "revision": "rev1"}
    assert telemetry["runtime"] == {"frame": 123}
    assert telemetry["symbols"]["source"] == "pokefirered_rev1.sym"
    assert telemetry["location"]["reason"] == "missing_save_block_1"
    assert telemetry["camera"] == {"available": False, "reason": "not_reported", "section": "camera"}
    assert telemetry["capabilities"]["mode"] is False


def test_telemetry_normalizer_should_report_available_capabilities() -> None:
    telemetry = normalize_telemetry_snapshot(
        {
            "game": "firered",
            "revision": "rev1",
            "frame": 9,
            "symbols": {"available": True},
            "location": {"available": True},
            "mode": {"name": "field", "confidence": "medium"},
            "camera": {"available": True},
            "save": {"available": True, "party": {"count": 2}},
        }
    )

    assert telemetry["capabilities"] == {
        "symbols": True,
        "location": True,
        "mode": True,
        "camera": True,
        "save": True,
        "party": True,
    }


def test_telemetry_endpoint_should_return_normalized_schema() -> None:
    response = request(create_app(RuntimeCore(FakeEmulatorBridge())), "GET", "/telemetry")

    assert response.status_code == 200
    assert response.json()["schema_version"] == TELEMETRY_SCHEMA_VERSION
    assert response.json()["capabilities"]["save"] is False
