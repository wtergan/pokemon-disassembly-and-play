"""Behavior tests for binding generated FireRed symbols to a verified target."""

from __future__ import annotations

import pytest

from tools.runtime.games.firered.symbols import (
    FIRERED_REV1_RUNTIME_SYMBOLS,
    SymbolTable,
    SymbolValidationError,
    validate_firered_rev1_runtime_symbols,
)


def test_generated_symbols_with_unverified_rom_should_reject_runtime_telemetry() -> None:
    """A complete symbol file cannot override a failed FireRed Rev 1 hash check."""

    symbols = SymbolTable({name: 0x03000000 + index * 4 for index, name in enumerate(FIRERED_REV1_RUNTIME_SYMBOLS)})

    with pytest.raises(SymbolValidationError, match="verified FireRed Rev 1 ROM"):
        validate_firered_rev1_runtime_symbols(symbols, rom_matches_expected=False)


def test_generated_symbols_with_missing_runtime_symbol_should_reject_runtime_telemetry() -> None:
    """A verified ROM still needs all state readers before semantic telemetry activates."""

    symbols = SymbolTable({name: 0x03000000 + index * 4 for index, name in enumerate(FIRERED_REV1_RUNTIME_SYMBOLS[:-1])})

    with pytest.raises(SymbolValidationError, match="missing required symbols"):
        validate_firered_rev1_runtime_symbols(symbols, rom_matches_expected=True)
