from __future__ import annotations

from tools.runtime.games.firered.mode import classify_runtime_mode
from tools.runtime.games.firered.symbols import SymbolTable
from tools.runtime.tests.test_firered_saveblock_fixture_should_decode_position import AddressedMemoryEmulator


def test_missing_mode_symbols_should_report_unknown_with_evidence() -> None:
    emulator = AddressedMemoryEmulator()

    mode = classify_runtime_mode(emulator, SymbolTable.empty(), location_available=False)

    assert mode["name"] == "unknown"
    assert mode["reason"] == "insufficient_symbols_or_state"
    assert mode["evidence"]["gMain"]["reason"] == "missing_symbol"


def test_in_battle_flag_should_classify_battle_mode() -> None:
    symbols = SymbolTable({"gMain": 0x03003000, "gPaletteFade": 0x02002000, "gTasks": 0x03004000})
    emulator = AddressedMemoryEmulator()
    emulator.write8(0x03003000 + 0x439, 0x02)

    mode = classify_runtime_mode(emulator, symbols, location_available=True)

    assert mode["name"] == "battle"
    assert mode["confidence"] == "high"
    assert mode["evidence"]["gMain"]["in_battle"] is True


def test_palette_fade_should_classify_transition_loading_mode() -> None:
    symbols = SymbolTable({"gMain": 0x03003000, "gPaletteFade": 0x02002000, "gTasks": 0x03004000})
    emulator = AddressedMemoryEmulator()
    emulator.write8(0x02002000 + 0x07, 0x80)

    mode = classify_runtime_mode(emulator, symbols, location_available=True)

    assert mode["name"] == "transition_loading"
    assert mode["confidence"] == "high"
    assert mode["evidence"]["gPaletteFade"]["active"] is True


def test_callback_name_should_classify_menu_mode() -> None:
    symbols = SymbolTable(
        {
            "gMain": 0x03003000,
            "gPaletteFade": 0x02002000,
            "gTasks": 0x03004000,
            "CB2_BagMenuRun": 0x08003000,
        }
    )
    emulator = AddressedMemoryEmulator()
    emulator.write32(0x03003000 + 0x04, 0x08003000)

    mode = classify_runtime_mode(emulator, symbols, location_available=True)

    assert mode["name"] == "menu"
    assert mode["reason"] == "callback_or_task_menu_name"


def test_active_message_task_should_classify_dialogue_textbox_mode() -> None:
    symbols = SymbolTable(
        {
            "gMain": 0x03003000,
            "gPaletteFade": 0x02002000,
            "gTasks": 0x03004000,
            "Task_DrawFieldMessageBox": 0x08004000,
        }
    )
    emulator = AddressedMemoryEmulator()
    emulator.write32(0x03004000, 0x08004000)
    emulator.write8(0x03004000 + 0x04, 1)

    mode = classify_runtime_mode(emulator, symbols, location_available=True)

    assert mode["name"] == "dialogue_textbox"
    assert mode["evidence"]["gTasks"]["active"][0]["func_name"] == "Task_DrawFieldMessageBox"
