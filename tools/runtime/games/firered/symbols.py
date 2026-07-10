"""Symbol table discovery and parsing for FireRed runtime telemetry.

`pret/pokefirered` can generate `pokefirered_rev1.sym` through `make syms`.
Those files are parsed into a tiny address lookup that the telemetry reader can
use without depending on the build system at runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


FIRERED_REV1_SYMBOL_BASENAME = "pokefirered_rev1.sym"
FIRERED_REV1_CORE_SYMBOLS = (
    "gSaveBlock1Ptr",
    "gSaveBlock2Ptr",
    "gCamera",
    "gMapHeader",
    "gPlayerAvatar",
    "gTasks",
    "gMain",
)
FIRERED_REV1_RUNTIME_SYMBOLS = (
    *FIRERED_REV1_CORE_SYMBOLS,
    "gPaletteFade",
)


_OBJDUMP_SYMBOL_RE = re.compile(
    r"^(?P<address>[0-9A-Fa-f]{8})\s+\S+\s+(?P<size>[0-9A-Fa-f]{8})\s+(?P<name>\S+)$"
)
_SIMPLE_SYMBOL_RE = re.compile(r"^(?P<address>[0-9A-Fa-f]{8})\s+(?P<name>\S+)$")
_LD_MAP_SYMBOL_RE = re.compile(r"^\s*0x(?P<address>[0-9A-Fa-f]{8,})\s+(?P<name>[A-Za-z_]\w*)$")


class SymbolTableError(ValueError):
    """Raised when a requested symbol is unavailable."""


class SymbolValidationError(ValueError):
    """Raised when symbols cannot safely describe the configured FireRed target."""


@dataclass(frozen=True)
class SymbolCoverage:
    """Coverage report for symbols required by a telemetry slice."""

    addresses: dict[str, int]
    missing: list[str]

    @property
    def available(self) -> bool:
        """Return whether every requested symbol was resolved."""

        return not self.missing


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

    def coverage(self, names: tuple[str, ...]) -> SymbolCoverage:
        """Return resolved addresses and missing names for `names`."""

        addresses = {name: address for name in names if (address := self.get(name)) is not None}
        return SymbolCoverage(addresses=addresses, missing=[name for name in names if name not in addresses])

    @classmethod
    def empty(cls) -> SymbolTable:
        """Return an explicitly empty symbol table."""

        return cls(addresses={})


def discover_symbol_table(
    repo_root: Path,
    explicit_path: Path | None = None,
    *,
    symbol_basename: str = FIRERED_REV1_SYMBOL_BASENAME,
    build_name: str = "firered_rev1",
) -> SymbolTable:
    """Load an explicit symbol file or a target-profile symbol file when present."""

    if explicit_path is not None:
        return load_symbol_table(explicit_path)
    discovered_path = find_symbol_file(repo_root, symbol_basename=symbol_basename, build_name=build_name)
    if discovered_path is None:
        return SymbolTable.empty()
    return load_symbol_table(discovered_path)


def find_default_symbol_file(repo_root: Path) -> Path | None:
    """Find the default generated FireRed Rev 1 symbol file under `repo_root`."""

    return find_symbol_file(repo_root, symbol_basename=FIRERED_REV1_SYMBOL_BASENAME, build_name="firered_rev1")


def find_symbol_file(repo_root: Path, *, symbol_basename: str, build_name: str) -> Path | None:
    """Find a generated symbol file for a target profile under `repo_root`."""

    candidates = (
        repo_root / symbol_basename,
        repo_root / "build" / build_name / symbol_basename,
    )
    return next((path for path in candidates if path.exists()), None)


def load_symbol_table(path: Path) -> SymbolTable:
    """Load a generated `pokefirered` symbol file."""

    return SymbolTable(addresses=parse_symbol_text(path.read_text(encoding="utf-8")), source=path)


def validate_firered_rev1_runtime_symbols(symbols: SymbolTable, *, rom_matches_expected: bool) -> SymbolTable:
    """Require a verified Rev 1 ROM and complete symbols before semantic decoding.

    A symbol table describes source addresses, not the bytes presently running in
    an emulator. The target hash gate is deliberately repeated here so a caller
    cannot accidentally enable stateful telemetry by passing a table alone.
    """

    if not rom_matches_expected:
        raise SymbolValidationError("semantic telemetry requires a verified FireRed Rev 1 ROM")
    coverage = symbols.coverage(FIRERED_REV1_RUNTIME_SYMBOLS)
    if coverage.missing:
        raise SymbolValidationError(f"missing required symbols: {', '.join(coverage.missing)}")
    invalid = [name for name, address in coverage.addresses.items() if not _is_gba_symbol_address(address)]
    if invalid:
        raise SymbolValidationError(f"symbols have invalid GBA addresses: {', '.join(invalid)}")
    return symbols


def parse_symbol_text(text: str) -> dict[str, int]:
    """Parse supported symbol text formats into `{name: address}`."""

    symbols: dict[str, int] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _OBJDUMP_SYMBOL_RE.match(line) or _SIMPLE_SYMBOL_RE.match(line) or _LD_MAP_SYMBOL_RE.match(line)
        if match is None:
            continue
        symbols[match.group("name")] = int(match.group("address"), 16)
    return symbols


def _is_gba_symbol_address(address: int) -> bool:
    """Return whether an address belongs to a GBA ROM or writable memory region."""

    return 0x02000000 <= address < 0x04000000 or 0x08000000 <= address < 0x0A000000
