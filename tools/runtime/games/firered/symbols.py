"""Symbol table parsing for FireRed runtime telemetry.

`pret/pokefirered` can generate `pokefirered_rev1.sym` through `make syms`.
Those files are parsed into a tiny address lookup that the telemetry reader can
use without depending on the build system at runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_OBJDUMP_SYMBOL_RE = re.compile(
    r"^(?P<address>[0-9A-Fa-f]{8})\s+\S+\s+(?P<size>[0-9A-Fa-f]{8})\s+(?P<name>\S+)$"
)
_SIMPLE_SYMBOL_RE = re.compile(r"^(?P<address>[0-9A-Fa-f]{8})\s+(?P<name>\S+)$")


class SymbolTableError(ValueError):
    """Raised when a requested symbol is unavailable."""


@dataclass(frozen=True)
class SymbolTable:
    """Runtime lookup for generated FireRed symbol addresses."""

    addresses: dict[str, int]
    source: Path | None = None

    def get(self, name: str) -> int | None:
        """Return the address for `name` when known."""

        return self.addresses.get(name)

    def require(self, name: str) -> int:
        """Return `name`'s address or raise a precise symbol error."""

        address = self.get(name)
        if address is None:
            raise SymbolTableError(f"missing symbol: {name}")
        return address

    @classmethod
    def empty(cls) -> SymbolTable:
        """Return an explicitly empty symbol table."""

        return cls(addresses={})


def load_symbol_table(path: Path) -> SymbolTable:
    """Load a generated `pokefirered` symbol file."""

    return SymbolTable(addresses=parse_symbol_text(path.read_text(encoding="utf-8")), source=path)


def parse_symbol_text(text: str) -> dict[str, int]:
    """Parse supported symbol text formats into `{name: address}`."""

    symbols: dict[str, int] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _OBJDUMP_SYMBOL_RE.match(line) or _SIMPLE_SYMBOL_RE.match(line)
        if match is None:
            continue
        symbols[match.group("name")] = int(match.group("address"), 16)
    return symbols
