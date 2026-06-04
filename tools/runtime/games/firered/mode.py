"""Runtime-mode heuristics for FireRed telemetry snapshots.

These readers use source-backed global structs from `include/main.h`,
`include/task.h`, and `include/palette.h`. Every classification includes the
memory evidence used so callers can distinguish hard signals from heuristics.
"""

from __future__ import annotations

from typing import Any

from ...emulators.base import EmulatorBridge
from .symbols import SymbolTable


G_MAIN_CALLBACK2 = 0x004
G_MAIN_FLAGS = 0x439
G_MAIN_IN_BATTLE = 0x02
G_PALETTE_FADE_ACTIVE_BYTE = 0x08
G_PALETTE_FADE_ACTIVE_MASK = 0x80
TASK_SIZE = 40
TASK_FUNC = 0x00
TASK_IS_ACTIVE = 0x04
TASK_COUNT = 16

_BATTLE_CALLBACKS = {"BattleMainCB2", "CB2_InitBattle", "CB2_HandleStartBattle", "CB2_InitBattleInternal"}
_FIELD_CALLBACK_PREFIXES = ("CB2_ReturnToField", "CB2_LoadMap", "CB2_EnterField")
_MENU_CALLBACK_KEYWORDS = ("Menu", "Bag", "Party", "Pokedex", "Option", "Summary", "Trade", "Shop", "PC")
_DIALOGUE_TASK_KEYWORDS = ("Message", "Text", "Dialogue")
_MENU_TASK_KEYWORDS = ("Menu", "Bag", "Party", "Pokedex", "Option", "Shop", "PC")


def classify_runtime_mode(emulator: EmulatorBridge, symbols: SymbolTable, location_available: bool) -> dict[str, Any]:
    """Classify the broad FireRed runtime mode from callbacks, tasks, and fades."""

    evidence: dict[str, Any] = {
        "gMain": _read_main_evidence(emulator, symbols),
        "gPaletteFade": _read_palette_fade_evidence(emulator, symbols),
        "gTasks": _read_task_evidence(emulator, symbols),
    }

    if evidence["gPaletteFade"].get("active") is True:
        return _mode("transition_loading", "high", "gPaletteFade.active", evidence)
    if evidence["gMain"].get("in_battle") is True or evidence["gMain"].get("callback2_name") in _BATTLE_CALLBACKS:
        return _mode("battle", "high", "gMain.inBattle_or_battle_callback", evidence)

    task_names = [task["func_name"] for task in evidence["gTasks"].get("active", []) if task.get("func_name")]
    callback_name = evidence["gMain"].get("callback2_name")
    names = [name for name in [callback_name, *task_names] if name]
    if any(_contains_keyword(name, _DIALOGUE_TASK_KEYWORDS) for name in task_names):
        return _mode("dialogue_textbox", "medium", "active_text_or_message_task", evidence)
    if any(_contains_keyword(name, _MENU_CALLBACK_KEYWORDS) for name in names):
        return _mode("menu", "medium", "callback_or_task_menu_name", evidence)
    if callback_name and callback_name.startswith(_FIELD_CALLBACK_PREFIXES):
        return _mode("field", "medium", "field_callback", evidence)
    if location_available:
        return _mode("field", "low", "valid_location_without_stronger_mode_signal", evidence)
    return _mode("unknown", "low", "insufficient_symbols_or_state", evidence)


def _read_main_evidence(emulator: EmulatorBridge, symbols: SymbolTable) -> dict[str, Any]:
    address = symbols.get("gMain")
    if address is None:
        return {"available": False, "reason": "missing_symbol"}
    callback2 = emulator.read32(address + G_MAIN_CALLBACK2)
    flags = emulator.read8(address + G_MAIN_FLAGS)
    return {
        "available": True,
        "symbol_address": address,
        "callback2": callback2,
        "callback2_name": _symbol_name_for_address(symbols, callback2),
        "flags": flags,
        "in_battle": bool(flags & G_MAIN_IN_BATTLE),
    }


def _read_palette_fade_evidence(emulator: EmulatorBridge, symbols: SymbolTable) -> dict[str, Any]:
    address = symbols.get("gPaletteFade")
    if address is None:
        return {"available": False, "reason": "missing_symbol"}
    active_byte = emulator.read8(address + G_PALETTE_FADE_ACTIVE_BYTE)
    return {
        "available": True,
        "symbol_address": address,
        "active_byte": active_byte,
        "active": bool(active_byte & G_PALETTE_FADE_ACTIVE_MASK),
    }


def _read_task_evidence(emulator: EmulatorBridge, symbols: SymbolTable) -> dict[str, Any]:
    address = symbols.get("gTasks")
    if address is None:
        return {"available": False, "reason": "missing_symbol", "active": []}
    active_tasks = []
    for index in range(TASK_COUNT):
        task_address = address + (index * TASK_SIZE)
        if emulator.read8(task_address + TASK_IS_ACTIVE) == 0:
            continue
        func = emulator.read32(task_address + TASK_FUNC)
        active_tasks.append(
            {
                "index": index,
                "func": func,
                "func_name": _symbol_name_for_address(symbols, func),
                "priority": emulator.read8(task_address + 0x07),
            }
        )
    return {"available": True, "symbol_address": address, "active": active_tasks}


def _symbol_name_for_address(symbols: SymbolTable, address: int) -> str | None:
    for name, symbol_address in symbols.addresses.items():
        if symbol_address == address:
            return name
    return None


def _contains_keyword(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)


def _mode(name: str, confidence: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "confidence": confidence, "reason": reason, "evidence": evidence}
