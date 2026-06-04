from __future__ import annotations

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_core import RuntimeCore


def test_fake_emulator_should_capture_snapshot_after_input() -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator)

    result = runtime.execute_action({"action": "tap", "button": "a", "frames": 3})
    snapshot = runtime.snapshot()

    assert result["ok"] is True
    assert result["frame"] == 3
    assert snapshot["frame"] == 3
    assert snapshot["mime_type"] == "image/png"
    assert emulator.pressed_buttons == frozenset()

