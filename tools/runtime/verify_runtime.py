"""Exercise an owned mGBA instance and retain real verification evidence.

This CLI uses the same factory and public runtime operations as the HTTP app.
It checks actual GBA key bits, isolated checkpoint round trips and telemetry;
it never treats an input smoke as proof of autonomous gameplay. Normal ROM-
adjacent save files are hashed before launch and after cleanup.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import time

from .config import load_runtime_config
from .runtime_factory import create_runtime_from_config


KEY_BITS = {"a": 0, "b": 1, "select": 2, "start": 3, "right": 4,
            "left": 5, "up": 6, "down": 7, "r": 8, "l": 9}


def save_fingerprints(rom: Path) -> dict[str, str | None]:
    """Hash normal ROM-adjacent saves without creating or opening them for write."""

    return {
        suffix: hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        for suffix in (".sav", ".srm", ".rtc")
        for path in (rom.with_suffix(suffix),)
    }


def verify(config_path: Path, output: Path) -> dict:
    """Launch, drive, capture and close only the emulator owned by this run."""

    config = load_runtime_config(config_path)
    output.mkdir(parents=True, exist_ok=True)
    before = save_fingerprints(config.target.rom_path)
    report = {"target": config.target.profile.key, "rom_matches": config.target.matches_expected,
              "observed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "normal_saves_before": before}
    runtime = None
    try:
        runtime = create_runtime_from_config(config)
        report["health"] = runtime.health()
        checks = []
        for button, bit in KEY_BITS.items():
            try:
                runtime.emulator.press_button(button)
                runtime.emulator.run_frames(3)
                mask = ~runtime.emulator.read16(0x04000130) & 0x3FF
                checks.append({"button": button, "active_mask": mask, "expected_mask": 1 << bit})
                if mask != 1 << bit:
                    raise RuntimeError(f"incorrect physical input for {button}: {mask:#x}")
            finally:
                runtime.emulator.release_button(button)
        report["input_checks"] = checks
        report["checkpoint"] = runtime.save_state("verification")
        runtime.execute_action({"action": "wait", "frames": 6})
        report["checkpoint_reload"] = runtime.load_state("verification")
        report["telemetry"] = runtime.telemetry()
        snapshot = runtime.snapshot()
        (output / "snapshot.png").write_bytes(base64.b64decode(snapshot["image_base64"]))
        report["snapshot_frame"] = snapshot["frame"]
        report["ok"] = True
    except Exception as exc:
        report["ok"] = False
        report["error"] = str(exc)
        raise
    finally:
        if runtime is not None:
            runtime.close()
        after = save_fingerprints(config.target.rom_path)
        report["normal_saves_after"] = after
        report["normal_saves_unchanged"] = before == after
        if before != after:
            report["ok"] = False
            report["error"] = "normal save fingerprints changed during verification"
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if before != after:
            raise RuntimeError("normal save fingerprints changed during verification")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(".runtime-logs/verification"))
    args = parser.parse_args()
    report = verify(args.config, args.output)
    print(json.dumps({"ok": report["ok"], "target": report["target"],
                      "normal_saves_unchanged": report["normal_saves_unchanged"],
                      "evidence": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
