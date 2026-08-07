"""Tests for runtime telemetry formatting and schema behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.state_models import TELEMETRY_SCHEMA_VERSION, normalize_telemetry_snapshot
from tools.runtime.tests.http_client import request


def test_telemetry_formatter_should_summarize_decoded_state() -> None:
    result = subprocess.run(
        ["node", "--input-type=module"],
        input="""
import assert from "node:assert/strict";
import { formatTrace, summarizeTelemetry } from "./tools/runtime/static/telemetry-format.js";

const summary = summarizeTelemetry({
  rom: { available: true, matches_expected: true },
  symbols: { available: true },
  mode: { name: "dialogue_textbox", confidence: "medium" },
  location: {
    available: true,
    map_group: 3,
    map_num: 0,
    player_x: 6,
    player_y: 7,
    map: { available: true, id: "MAP_PALLET_TOWN" },
  },
  camera: { available: true, x: 12, y: 34, active: true },
  save: {
    available: true,
    player: { available: true, name: "RED" },
    party: {
      count: 1,
      capacity: 6,
      members: [{ available: true, nickname: "PIKA", species: 25, level: 12 }],
    },
    bag_pockets: {
      items: { used_slots: 2, capacity: 42 },
      key_items: { used_slots: 0, capacity: 30 },
    },
    flags: { bytes: 288, nonzero_bytes: 3 },
    vars: { entries: 256, nonzero_entries: 4 },
  },
});

assert.equal(summary.rom, "rom: match");
assert.equal(summary.mode, "dialogue textbox / medium");
assert.equal(summary.map, "MAP_PALLET_TOWN (3:0)");
assert.equal(summary.player, "RED @ 6, 7");
assert.equal(summary.camera, "12, 34 active");
assert.equal(summary.party, "1/6: PIKA L12");
assert.equal(summary.bag, "items 2/42");
assert.equal(summary.events, "3/288 flag bytes; 4/256 vars");
assert.equal(summary.symbols, "available");
assert.match(summary.raw, /MAP_PALLET_TOWN/);
assert.equal(formatTrace({ id: 7, type: "action", status: "accepted", detail: { action: "press", button: "a" } }), "7 accepted press:a");
""",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

def test_telemetry_formatter_should_preserve_unavailable_reasons() -> None:
    result = subprocess.run(
        ["node", "--input-type=module"],
        input="""
import assert from "node:assert/strict";
import { summarizeTelemetry } from "./tools/runtime/static/telemetry-format.js";

const summary = summarizeTelemetry({
  rom: { available: false, reason: "not_configured" },
  symbols: { available: false, missing: ["gSaveBlock1Ptr"] },
  mode: { name: "unknown", reason: "missing_symbol" },
  location: { available: false, reason: "missing_save_block_1" },
  camera: { available: false, reason: "missing_symbol" },
  save: { available: false, reason: "missing_save_block_1" },
});

assert.equal(summary.rom, "rom: not_configured");
assert.equal(summary.mode, "unknown (missing_symbol)");
assert.equal(summary.map, "missing_save_block_1");
assert.equal(summary.player, "--");
assert.equal(summary.camera, "missing_symbol");
assert.equal(summary.party, "--");
assert.equal(summary.symbols, "gSaveBlock1Ptr");
""",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

def test_empty_runtime_telemetry_should_publish_unavailable_schema() -> None:
    telemetry = RuntimeCore(FakeEmulatorBridge()).telemetry()

    assert telemetry["schema_version"] == TELEMETRY_SCHEMA_VERSION
    assert telemetry["target"] == {"game": "unknown", "revision": "unknown"}
    assert telemetry["runtime"] == {"frame": 0}
    assert telemetry["location"] == {"available": False, "reason": "not_reported", "section": "location"}
    assert telemetry["capabilities"] == {
        "symbols": False,
        "location": False,
        "mode": False,
        "camera": False,
        "save": False,
        "party": False,
    }

def test_telemetry_normalizer_should_preserve_explicit_unavailable_sections() -> None:
    telemetry = normalize_telemetry_snapshot(
        {
            "game": "firered",
            "revision": "rev1",
            "frame": 123,
            "symbols": {"available": False, "source": Path("/private/pokefirered_rev1.sym")},
            "location": {"available": False, "reason": "missing_save_block_1"},
            "mode": {"name": "unknown", "confidence": "low"},
            "save": {"available": False, "reason": "missing_save_block_1"},
        }
    )

    assert telemetry["target"] == {"game": "firered", "revision": "rev1"}
    assert telemetry["runtime"] == {"frame": 123}
    assert telemetry["symbols"]["source"] == "pokefirered_rev1.sym"
    assert telemetry["location"]["reason"] == "missing_save_block_1"
    assert telemetry["camera"] == {"available": False, "reason": "not_reported", "section": "camera"}
    assert telemetry["capabilities"]["mode"] is False

def test_telemetry_normalizer_should_report_available_capabilities() -> None:
    telemetry = normalize_telemetry_snapshot(
        {
            "game": "firered",
            "revision": "rev1",
            "frame": 9,
            "symbols": {"available": True},
            "location": {"available": True},
            "mode": {"name": "field", "confidence": "medium"},
            "camera": {"available": True},
            "save": {"available": True, "party": {"count": 2}},
        }
    )

    assert telemetry["capabilities"] == {
        "symbols": True,
        "location": True,
        "mode": True,
        "camera": True,
        "save": True,
        "party": True,
    }

def test_telemetry_endpoint_should_return_normalized_schema() -> None:
    response = request(create_app(RuntimeCore(FakeEmulatorBridge())), "GET", "/telemetry")

    assert response.status_code == 200
    assert response.json()["schema_version"] == TELEMETRY_SCHEMA_VERSION
    assert response.json()["capabilities"]["save"] is False
