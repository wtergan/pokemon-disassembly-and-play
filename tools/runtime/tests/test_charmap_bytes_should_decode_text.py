from __future__ import annotations

from pathlib import Path

from tools.runtime.games.firered.text import load_charmap, parse_charmap_text


def test_charmap_bytes_should_decode_english_player_name() -> None:
    decoder = load_charmap(Path.cwd() / "charmap.txt")

    assert decoder.decode([0xCC, 0xBF, 0xBE, 0xFF, 0x00]) == "RED"


def test_multibyte_charmap_token_should_decode_greedily() -> None:
    decoder = load_charmap(Path.cwd() / "charmap.txt")

    assert decoder.decode([0x53, 0x54, 0x00, 0xFF]) == "{PKMN} "


def test_unknown_charmap_byte_should_preserve_hex_escape() -> None:
    decoder = load_charmap(Path.cwd() / "charmap.txt")

    assert decoder.decode([0x7D, 0xFF]) == "\\x7D"


def test_charmap_parser_should_ignore_japanese_section_duplicates() -> None:
    tokens = parse_charmap_text("'A' = BB\n'$' = FF\n@ Hiragana\n'あ' = 01\n")

    assert tokens == {(0xBB,): "A", (0xFF,): ""}
