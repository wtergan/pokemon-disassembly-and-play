from __future__ import annotations

import pytest

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.state_slots import StateSlotError


def test_state_slot_should_save_and_load_runtime_owned_file(tmp_path) -> None:
    emulator = FakeEmulatorBridge()
    runtime = RuntimeCore(emulator, state_dir=tmp_path)
    emulator.run_frames(42)

    saved = runtime.save_state("quick")
    emulator.run_frames(5)
    loaded = runtime.load_state("quick")
    slots = runtime.list_states()["slots"]

    assert saved["ok"] is True
    assert loaded["ok"] is True
    assert emulator.frame_count == 42
    assert slots[0]["name"] == "quick"
    assert slots[0]["exists"] is True
    assert slots[0]["size_bytes"] > 0
    assert "path" not in slots[0]
    assert runtime.recent_traces()[-2]["detail"]["slot"] == "quick"


def test_state_slot_should_reject_path_like_slot_names(tmp_path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)

    with pytest.raises(StateSlotError, match="slot must be"):
        runtime.save_state("../outside")

    assert not list(tmp_path.iterdir())


def test_state_slot_should_reject_missing_load_slot(tmp_path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)

    with pytest.raises(StateSlotError, match="does not exist"):
        runtime.load_state("missing")
