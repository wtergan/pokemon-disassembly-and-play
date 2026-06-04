from __future__ import annotations

import pytest

from tools.runtime.action_executor import ActionExecutor, ActionValidationError
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.trace_recorder import TraceRecorder


def test_action_not_allowed_should_be_rejected() -> None:
    emulator = FakeEmulatorBridge()
    traces = TraceRecorder()
    executor = ActionExecutor(emulator, traces)

    with pytest.raises(ActionValidationError):
        executor.execute({"action": "tap", "button": "power"})

    assert emulator.frame_count == 0
    assert traces.recent()[0]["status"] == "rejected"

