from __future__ import annotations

from pathlib import Path

from tools.runtime.action_executor import ActionExecutor
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.trace_recorder import TraceRecorder


def test_press_release_actions_should_track_held_buttons() -> None:
    emulator = FakeEmulatorBridge()
    executor = ActionExecutor(emulator, TraceRecorder())

    press = executor.execute({"action": "press", "button": "a"})
    release = executor.execute({"action": "release", "button": "a"})

    assert press["ok"] is True
    assert release["ok"] is True
    assert emulator.pressed_buttons == frozenset()


def test_control_markup_should_expose_accessible_hold_buttons() -> None:
    html = (Path.cwd() / "tools/runtime/static/index.html").read_text(encoding="utf-8")

    assert 'id="input-state" aria-live="polite"' in html
    for button in ("up", "down", "left", "right", "a", "b", "start", "select", "l", "r"):
        assert f'data-button="{button}"' in html
        assert 'aria-pressed="false"' in html
    assert '<script type="module" src="/app.js"></script>' in html
