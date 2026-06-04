"""Target profile registry and ROM identity checks.

Runtime targets are intentionally explicit. Each supported game/revision has a
profile with the expected SHA-1, display name, generated symbol basename, and
adapter key so config validation can reject mismatched ROMs before launch.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path


class TargetProfileError(ValueError):
    """Raised when a target profile or ROM identity check is invalid."""


@dataclass(frozen=True)
class TargetProfile:
    """Static metadata for one supported runtime target."""

    key: str
    game: str
    revision: str
    display_name: str
    expected_sha1: str
    rom_basename: str
    symbol_basename: str
    build_name: str
    adapter: str


TARGET_PROFILES: dict[str, TargetProfile] = {
    "firered_rev1": TargetProfile(
        key="firered_rev1",
        game="firered",
        revision="rev1",
        display_name="Pokemon FireRed Rev 1",
        expected_sha1="dd5945db9b930750cb39d00c84da8571feebf417",
        rom_basename="pokefirered_rev1.gba",
        symbol_basename="pokefirered_rev1.sym",
        build_name="firered_rev1",
        adapter="firered",
    ),
    "leafgreen_rev1": TargetProfile(
        key="leafgreen_rev1",
        game="leafgreen",
        revision="rev1",
        display_name="Pokemon LeafGreen Rev 1",
        expected_sha1="7862c67bdecbe21d1d69ce082ce34327e1c6ed5e",
        rom_basename="pokeleafgreen_rev1.gba",
        symbol_basename="pokeleafgreen_rev1.sym",
        build_name="leafgreen_rev1",
        adapter="leafgreen",
    ),
}


def get_target_profile(game: str, revision: str) -> TargetProfile:
    """Return the supported profile for a normalized game/revision pair."""

    key = f"{game.lower()}_{revision.lower()}"
    try:
        return TARGET_PROFILES[key]
    except KeyError as exc:
        raise TargetProfileError(f"unsupported target profile: {game} {revision}") from exc


def verify_rom_identity(path: Path, profile: TargetProfile, *, verify_hash: bool = True) -> dict[str, object]:
    """Hash `path` and optionally reject it when it does not match `profile`."""

    sha1 = sha1_file(path)
    matches_expected = sha1 == profile.expected_sha1
    if verify_hash and not matches_expected:
        raise TargetProfileError(
            f"ROM SHA-1 mismatch for {profile.display_name}: expected {profile.expected_sha1}, got {sha1}"
        )
    return {
        "sha1": sha1,
        "expected_sha1": profile.expected_sha1,
        "matches_expected": matches_expected,
    }


def sha1_file(path: Path) -> str:
    """Return the SHA-1 digest for `path`."""

    digest = hashlib.sha1()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
