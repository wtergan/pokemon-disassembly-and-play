from __future__ import annotations

import pytest

from tools.runtime.action_executor import ActionExecutor, ActionValidationError
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.tests.http_client import request
from tools.runtime.trace_recorder import TraceRecorder


def test_action_not_allowed_should_be_rejected() -> None:
    emulator = FakeEmulatorBridge()
    traces = TraceRecorder()
    executor = ActionExecutor(emulator, traces)

    with pytest.raises(ActionValidationError):
        executor.execute({"action": "tap", "button": "power"})

    assert emulator.frame_count == 0
    assert traces.recent()[0]["status"] == "rejected"


def test_malformed_action_frames_should_return_validation_error() -> None:
    response = request(create_app(), "POST", "/action", json={"action": "wait", "frames": "oops"})

    assert response.status_code == 400
    assert response.json()["detail"] == "frames must be an integer"
