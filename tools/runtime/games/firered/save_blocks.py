"""Source-backed FireRed SaveBlock offsets and readers used by runtime telemetry.

Offsets come from `include/global.h` in `pret/pokefirered`. SaveBlock1 begins
with player position and `struct WarpData`; SaveBlock2 begins with player
identity/options and stores the encryption key at `0xF20`.
"""

from __future__ import annotations

from typing import Any

from ...emulators.base import EmulatorBridge
from .text import FireRedCharmap


SAVE_BLOCK_1_POS_X = 0x0000
SAVE_BLOCK_1_POS_Y = 0x0002
SAVE_BLOCK_1_LOCATION = 0x0004
SAVE_BLOCK_1_LOCATION_MAP_GROUP = SAVE_BLOCK_1_LOCATION + 0x00
SAVE_BLOCK_1_LOCATION_MAP_NUM = SAVE_BLOCK_1_LOCATION + 0x01
SAVE_BLOCK_1_LOCATION_WARP_ID = SAVE_BLOCK_1_LOCATION + 0x02
SAVE_BLOCK_1_LOCATION_X = SAVE_BLOCK_1_LOCATION + 0x04
SAVE_BLOCK_1_LOCATION_Y = SAVE_BLOCK_1_LOCATION + 0x06
SAVE_BLOCK_1_PLAYER_PARTY_COUNT = 0x0034
SAVE_BLOCK_1_PLAYER_PARTY = 0x0038
SAVE_BLOCK_1_MONEY = 0x0290
SAVE_BLOCK_1_COINS = 0x0294
SAVE_BLOCK_1_BAG_POCKET_ITEMS = 0x0310
SAVE_BLOCK_1_BAG_POCKET_KEY_ITEMS = 0x03B8
SAVE_BLOCK_1_BAG_POCKET_POKE_BALLS = 0x0430
SAVE_BLOCK_1_BAG_POCKET_TMHM = 0x0464
SAVE_BLOCK_1_BAG_POCKET_BERRIES = 0x054C
SAVE_BLOCK_1_OBJECT_EVENTS = 0x06A0
SAVE_BLOCK_1_FLAGS = 0x0EE0
SAVE_BLOCK_1_VARS = 0x1000

SAVE_BLOCK_2_PLAYER_NAME = 0x0000
SAVE_BLOCK_2_PLAYER_GENDER = 0x0008
SAVE_BLOCK_2_TRAINER_ID = 0x000A
SAVE_BLOCK_2_PLAY_TIME_HOURS = 0x000E
SAVE_BLOCK_2_PLAY_TIME_MINUTES = 0x0010
SAVE_BLOCK_2_PLAY_TIME_SECONDS = 0x0011
SAVE_BLOCK_2_ENCRYPTION_KEY = 0x0F20

PLAYER_NAME_LENGTH = 7
TRAINER_ID_LENGTH = 4
POKEMON_NAME_LENGTH = 10
PARTY_SIZE = 6
POKEMON_SIZE = 100
BOX_POKEMON_SECURE = 0x20
POKEMON_STATUS = 0x50
POKEMON_LEVEL = 0x54
POKEMON_HP = 0x56
POKEMON_MAX_HP = 0x58
POKEMON_SUBSTRUCT_SIZE = 12
POKEMON_SECURE_WORDS = 12
ITEM_SLOT_SIZE = 4
NUM_FLAG_BYTES = 0x120
VARS_COUNT = 0x100
SUBSTRUCT_ORDERS = (
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 2, 1, 3),
    (0, 3, 1, 2),
    (0, 2, 3, 1),
    (0, 3, 2, 1),
    (1, 0, 2, 3),
    (1, 0, 3, 2),
    (2, 0, 1, 3),
    (3, 0, 1, 2),
    (2, 0, 3, 1),
    (3, 0, 2, 1),
    (1, 2, 0, 3),
    (1, 3, 0, 2),
    (2, 1, 0, 3),
    (3, 1, 0, 2),
    (2, 3, 0, 1),
    (3, 2, 0, 1),
    (1, 2, 3, 0),
    (1, 3, 2, 0),
    (2, 1, 3, 0),
    (3, 1, 2, 0),
    (2, 3, 1, 0),
    (3, 2, 1, 0),
)
BAG_POCKETS = (
    ("items", SAVE_BLOCK_1_BAG_POCKET_ITEMS, 42),
    ("key_items", SAVE_BLOCK_1_BAG_POCKET_KEY_ITEMS, 30),
    ("poke_balls", SAVE_BLOCK_1_BAG_POCKET_POKE_BALLS, 13),
    ("tmhm", SAVE_BLOCK_1_BAG_POCKET_TMHM, 58),
    ("berries", SAVE_BLOCK_1_BAG_POCKET_BERRIES, 43),
)

GBA_EWRAM_START = 0x02000000
GBA_EWRAM_END = 0x02040000
GBA_IWRAM_START = 0x03000000
GBA_IWRAM_END = 0x03008000
GBA_ROM_START = 0x08000000
GBA_ROM_END = 0x0A000000

# Exact Rev 1 sizes declared by struct SaveBlock1/SaveBlock2 in include/global.h.
SAVE_BLOCK_1_SIZE = 0x3D68
SAVE_BLOCK_2_SIZE = 0x0F24


def is_gba_address(address: int) -> bool:
    """Return whether `address` is in a normal GBA ROM/RAM range."""

    return (
        GBA_EWRAM_START <= address < GBA_EWRAM_END
        or GBA_IWRAM_START <= address < GBA_IWRAM_END
        or GBA_ROM_START <= address < GBA_ROM_END
    )


def is_save_block_pointer(pointer: int | None, size: int) -> bool:
    """Return whether an aligned full SaveBlock extent fits inside GBA EWRAM."""

    return (
        pointer is not None
        and pointer != 0
        and pointer % 4 == 0
        and GBA_EWRAM_START <= pointer
        and pointer + size <= GBA_EWRAM_END
    )


def read_save_block_summary(
    emulator: EmulatorBridge,
    save_block_1: int | None,
    save_block_2: int | None,
    text_decoder: FireRedCharmap | None = None,
) -> dict[str, Any]:
    """Decode source-backed SaveBlock summary fields with explicit unavailable states."""

    if not is_save_block_pointer(save_block_1, SAVE_BLOCK_1_SIZE):
        return {"available": False, "reason": "missing_save_block_1"}

    encryption_key = _read_encryption_key(emulator, save_block_2)
    return {
        "available": True,
        "player": _read_player_summary(emulator, save_block_2, text_decoder),
        "party": _read_party_summary(emulator, save_block_1, text_decoder),
        "money": _read_money(emulator, save_block_1, encryption_key),
        "coins": emulator.read16(save_block_1 + SAVE_BLOCK_1_COINS),
        "bag_pockets": _read_bag_pockets(emulator, save_block_1, encryption_key),
        "flags": _read_flag_summary(emulator, save_block_1),
        "vars": _read_var_summary(emulator, save_block_1),
    }


def _read_party_summary(
    emulator: EmulatorBridge,
    save_block_1: int,
    text_decoder: FireRedCharmap | None,
) -> dict[str, Any]:
    count = min(emulator.read8(save_block_1 + SAVE_BLOCK_1_PLAYER_PARTY_COUNT), PARTY_SIZE)
    return {
        "count": count,
        "capacity": PARTY_SIZE,
        "members": [
            _read_party_member(
                emulator,
                save_block_1 + SAVE_BLOCK_1_PLAYER_PARTY + (index * POKEMON_SIZE),
                index,
                text_decoder,
            )
            for index in range(count)
        ],
    }


def _read_party_member(
    emulator: EmulatorBridge,
    address: int,
    index: int,
    text_decoder: FireRedCharmap | None = None,
) -> dict[str, Any]:
    personality = emulator.read32(address)
    ot_id = emulator.read32(address + 0x04)
    decrypted_secure = _read_decrypted_secure_data(emulator, address, personality, ot_id)
    checksum = emulator.read16(address + 0x1C)
    calculated_checksum = _checksum_u16(decrypted_secure)
    if calculated_checksum != checksum:
        return {
            "available": False,
            "index": index,
            "reason": "checksum_mismatch",
            "personality": personality,
            "ot_id": ot_id,
            "checksum": checksum,
            "calculated_checksum": calculated_checksum,
        }

    substruct0 = _pokemon_substruct(decrypted_secure, personality, 0)
    nickname_bytes = _read_bytes(emulator, address + 0x08, POKEMON_NAME_LENGTH)
    member = {
        "available": True,
        "index": index,
        "personality": personality,
        "ot_id": ot_id,
        "nickname_bytes": nickname_bytes,
        "species": _u16(substruct0, 0x00),
        "held_item": _u16(substruct0, 0x02),
        "level": emulator.read8(address + POKEMON_LEVEL),
        "hp": emulator.read16(address + POKEMON_HP),
        "max_hp": emulator.read16(address + POKEMON_MAX_HP),
        "status": emulator.read32(address + POKEMON_STATUS),
        "checksum": checksum,
    }
    if text_decoder is not None:
        member["nickname"] = text_decoder.decode(nickname_bytes)
    return member


def _read_player_summary(
    emulator: EmulatorBridge,
    save_block_2: int | None,
    text_decoder: FireRedCharmap | None,
) -> dict[str, Any]:
    if not is_save_block_pointer(save_block_2, SAVE_BLOCK_2_SIZE):
        return {"available": False, "reason": "missing_save_block_2"}
    name_bytes = _read_bytes(emulator, save_block_2 + SAVE_BLOCK_2_PLAYER_NAME, PLAYER_NAME_LENGTH + 1)
    player = {
        "available": True,
        "name_bytes": name_bytes,
        "gender": emulator.read8(save_block_2 + SAVE_BLOCK_2_PLAYER_GENDER),
        "trainer_id": _read_bytes(emulator, save_block_2 + SAVE_BLOCK_2_TRAINER_ID, TRAINER_ID_LENGTH),
        "play_time": {
            "hours": emulator.read16(save_block_2 + SAVE_BLOCK_2_PLAY_TIME_HOURS),
            "minutes": emulator.read8(save_block_2 + SAVE_BLOCK_2_PLAY_TIME_MINUTES),
            "seconds": emulator.read8(save_block_2 + SAVE_BLOCK_2_PLAY_TIME_SECONDS),
        },
    }
    if text_decoder is not None:
        player["name"] = text_decoder.decode(name_bytes)
    return player


def _read_money(emulator: EmulatorBridge, save_block_1: int, encryption_key: int | None) -> dict[str, Any]:
    encrypted = emulator.read32(save_block_1 + SAVE_BLOCK_1_MONEY)
    if encryption_key is None:
        return {"available": False, "encrypted": encrypted, "reason": "missing_encryption_key"}
    return {"available": True, "value": encrypted ^ encryption_key}


def _read_bag_pockets(
    emulator: EmulatorBridge,
    save_block_1: int,
    encryption_key: int | None,
) -> dict[str, dict[str, Any]]:
    return {
        name: _read_bag_pocket(emulator, save_block_1 + offset, capacity, encryption_key)
        for name, offset, capacity in BAG_POCKETS
    }


def _read_bag_pocket(
    emulator: EmulatorBridge,
    address: int,
    capacity: int,
    encryption_key: int | None,
) -> dict[str, Any]:
    used_slots = 0
    total_quantity = 0
    for index in range(capacity):
        slot_address = address + (index * ITEM_SLOT_SIZE)
        item_id = emulator.read16(slot_address)
        if item_id == 0:
            continue
        used_slots += 1
        if encryption_key is not None:
            total_quantity += emulator.read16(slot_address + 2) ^ (encryption_key & 0xFFFF)
    return {
        "capacity": capacity,
        "used_slots": used_slots,
        "total_quantity": total_quantity if encryption_key is not None else None,
        "quantity_available": encryption_key is not None,
    }


def _read_flag_summary(emulator: EmulatorBridge, save_block_1: int) -> dict[str, int]:
    nonzero_bytes = sum(1 for value in _read_bytes(emulator, save_block_1 + SAVE_BLOCK_1_FLAGS, NUM_FLAG_BYTES) if value)
    return {"bytes": NUM_FLAG_BYTES, "nonzero_bytes": nonzero_bytes}


def _read_var_summary(emulator: EmulatorBridge, save_block_1: int) -> dict[str, int]:
    nonzero_entries = 0
    for index in range(VARS_COUNT):
        if emulator.read16(save_block_1 + SAVE_BLOCK_1_VARS + (index * 2)):
            nonzero_entries += 1
    return {"entries": VARS_COUNT, "nonzero_entries": nonzero_entries}


def _read_encryption_key(emulator: EmulatorBridge, save_block_2: int | None) -> int | None:
    if not is_save_block_pointer(save_block_2, SAVE_BLOCK_2_SIZE):
        return None
    return emulator.read32(save_block_2 + SAVE_BLOCK_2_ENCRYPTION_KEY)


def _read_bytes(emulator: EmulatorBridge, address: int, count: int) -> list[int]:
    return [emulator.read8(address + offset) for offset in range(count)]


def _read_decrypted_secure_data(
    emulator: EmulatorBridge,
    pokemon_address: int,
    personality: int,
    ot_id: int,
) -> bytes:
    key = personality ^ ot_id
    words = []
    for index in range(POKEMON_SECURE_WORDS):
        encrypted = emulator.read32(pokemon_address + BOX_POKEMON_SECURE + (index * 4))
        words.append((encrypted ^ key).to_bytes(4, "little"))
    return b"".join(words)


def _pokemon_substruct(secure_data: bytes, personality: int, substruct_type: int) -> bytes:
    storage_index = SUBSTRUCT_ORDERS[personality % len(SUBSTRUCT_ORDERS)][substruct_type]
    start = storage_index * POKEMON_SUBSTRUCT_SIZE
    return secure_data[start : start + POKEMON_SUBSTRUCT_SIZE]


def _checksum_u16(data: bytes) -> int:
    checksum = 0
    for offset in range(0, len(data), 2):
        checksum = (checksum + int.from_bytes(data[offset : offset + 2], "little")) & 0xFFFF
    return checksum


def _u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")
