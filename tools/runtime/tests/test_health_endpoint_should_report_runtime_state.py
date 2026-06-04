from __future__ import annotations

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.tests.http_client import request


class CloseTrackingEmulator(FakeEmulatorBridge):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_health_endpoint_should_report_runtime_state() -> None:
    runtime = RuntimeCore(FakeEmulatorBridge())

    response = request(create_app(runtime), "GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "bridge": "fake", "frame": 0, "detail": ""}


def test_configured_runtime_app_should_disable_docs_routes() -> None:
    runtime = RuntimeCore(FakeEmulatorBridge())
    app = create_app(runtime)

    assert request(app, "GET", "/docs").status_code == 404
    assert request(app, "GET", "/openapi.json").status_code == 404


def test_runtime_close_should_release_emulator_resources() -> None:
    emulator = CloseTrackingEmulator()
    runtime = RuntimeCore(emulator)

    runtime.close()

    assert emulator.closed is True
