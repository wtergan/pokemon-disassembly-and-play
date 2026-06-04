from __future__ import annotations

from fastapi.testclient import TestClient

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore


def test_health_endpoint_should_report_runtime_state() -> None:
    runtime = RuntimeCore(FakeEmulatorBridge())
    client = TestClient(create_app(runtime))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "bridge": "fake", "frame": 0, "detail": ""}

