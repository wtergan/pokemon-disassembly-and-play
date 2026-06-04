"""FireRed character-map decoding for strings exposed through telemetry.

The English FireRed runtime stores names and UI text in a custom byte encoding
defined by `charmap.txt`. This module parses that source table and decodes
short, fixed-size runtime strings without expanding broader text-control
semantics into the emulator layer.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EOS_BYTE = 0xFF
_CHARMAP_RE = re.compile(r"^(?P<label>.+?)\s*=\s*(?P<bytes>[0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)$")


@dataclass(frozen=True)
class FireRedCharmap:
    """Greedy decoder for the English FireRed character map."""

    tokens: dict[tuple[int, ...], str]
    source: Path | None = None

    def decode(self, values: Iterable[int], stop_at_eos: bool = True) -> str:
        """Decode `values`, stopping at FireRed's EOS byte by default."""

        data = tuple(value & 0xFF for value in values)
        output: list[str] = []
        index = 0
        while index < len(data):
            if stop_at_eos and data[index] == EOS_BYTE:
                break
            token = self._longest_match(data, index)
            if token is None:
                output.append(f"\\x{data[index]:02X}")
                index += 1
                continue
            byte_sequence, text = token
            output.append(text)
            index += len(byte_sequence)
        return "".join(output)

    def _longest_match(self, data: tuple[int, ...], index: int) -> tuple[tuple[int, ...], str] | None:
        candidates = (
            (byte_sequence, text)
            for byte_sequence, text in self.tokens.items()
            if data[index : index + len(byte_sequence)] == byte_sequence
        )
        return max(candidates, key=lambda item: len(item[0]), default=None)


def load_charmap(path: Path) -> FireRedCharmap:
    """Load FireRed's English charmap from `path`."""

    return FireRedCharmap(tokens=parse_charmap_text(path.read_text(encoding="utf-8")), source=path)


def try_load_charmap(repo_root: Path) -> FireRedCharmap | None:
    """Load `charmap.txt` from `repo_root` when the source checkout has it."""

    path = repo_root / "charmap.txt"
    return load_charmap(path) if path.exists() else None


def parse_charmap_text(text: str) -> dict[tuple[int, ...], str]:
    """Parse the English section of `charmap.txt` into byte-sequence tokens."""

    tokens: dict[tuple[int, ...], str] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("@", 1)[0].strip()
        if raw_line.strip() == "@ Hiragana":
            break
        if not line:
            continue
        match = _CHARMAP_RE.match(line)
        if match is None:
            continue
        byte_sequence = tuple(int(part, 16) for part in match.group("bytes").split())
        label = _parse_label(match.group("label").strip())
        tokens[byte_sequence] = "" if byte_sequence == (EOS_BYTE,) else label
    return tokens


def _parse_label(label: str) -> str:
    if label.startswith("'") and label.endswith("'"):
        return ast.literal_eval(label)
    return f"{{{label}}}"
