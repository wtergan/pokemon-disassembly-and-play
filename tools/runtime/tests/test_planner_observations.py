"""Behavioral checks for private, screenshot-aware planner observations."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from tools.runtime.agent_context import build_agent_context
from tools.runtime.codex_client import AgentClientUnavailable, CodexAppServerClient


def _context() -> dict[str, Any]:
    return build_agent_context(
        {
            "target": {"game": "firered", "revision": "rev1"},
            "rom": {
                "available": True,
                "name": "firered.gba",
                "path": "/private/roms/firered.gba",
                "matches_expected": True,
            },
            "runtime": {"frame": 12},
            "mode": {"name": "unknown", "confidence": "low"},
            "location": {"available": False, "reason": "boot is still running"},
            "debug": {"screenshot_path": "/private/runtime/snapshot.png"},
        },
        [],
        {"slots": []},
    )


def _decide_with_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    snapshot_provider: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _context()
    client = CodexAppServerClient(
        repo_root=Path.cwd(),
        snapshot_provider=snapshot_provider,
    )
    client.thread_id = "thread-1"
    monkeypatch.setattr("tools.runtime.codex_client.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr(client, "start", lambda: None)

    requests: list[tuple[str, dict[str, Any]]] = []

    def request(method: str, params: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        requests.append((method, params))
        return {"turn": {"id": "turn-1"}}

    monkeypatch.setattr(client, "_request", request)
    monkeypatch.setattr(client, "_wait_for_turn_text", lambda _turn_id, *, timeout: json.dumps({
        "action_id": "wait_short",
        "reason": "inspect the current screen",
    }))

    client.decide(context)
    turn = next(params for method, params in requests if method == "turn/start")
    return context, turn


def test_codex_client_should_add_screenshot_as_secondary_image_input(monkeypatch: pytest.MonkeyPatch) -> None:
    context, turn = _decide_with_snapshot(
        monkeypatch,
        lambda: {"mime_type": "image/png", "image_base64": "aGVsbG8="},
    )

    inputs = turn["input"]
    assert inputs[0]["type"] == "text"
    assert "secondary visual evidence" in inputs[1]["text"]
    assert inputs[3] == {"type": "image", "url": "data:image/png;base64,aGVsbG8="}
    encoded_context = json.dumps(context)
    assert "image_base64" not in encoded_context
    assert "/private/" not in encoded_context
    assert any("both structured telemetry and available screen evidence" in rule for rule in context["rules"])


@pytest.mark.parametrize("provider", [None, lambda: {"mime_type": "image/png", "image_base64": "not base64!"}])
def test_codex_client_should_keep_text_only_input_without_valid_screenshot(
    monkeypatch: pytest.MonkeyPatch,
    provider: Any,
) -> None:
    _context_value, turn = _decide_with_snapshot(monkeypatch, provider)

    assert len(turn["input"]) == 2
    assert all(item["type"] == "text" for item in turn["input"])


class _FakeProcess:
    def __init__(self) -> None:
        self.stdin = io.StringIO()
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def test_codex_client_should_start_read_only_thread_without_replacing_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()
    monkeypatch.setattr("tools.runtime.codex_client.subprocess.Popen", lambda *args, **kwargs: process)
    client = CodexAppServerClient(repo_root=Path.cwd(), model="gpt-5.6-luna", reasoning_effort="xhigh")
    requests: list[tuple[str, dict[str, Any]]] = []

    def request(method: str, params: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        requests.append((method, params))
        return {"thread": {"id": "thread-1"}} if method == "thread/start" else {}

    monkeypatch.setattr(client, "_request", request)
    client.start()
    client.close()

    params = next(params for method, params in requests if method == "thread/start")
    assert params["sandbox"] == "read-only"
    assert "sandboxPolicy" not in params
    assert params["model"] == "gpt-5.6-luna"
    assert params["effort"] == "xhigh"
    instructions = params["developerInstructions"].lower()
    assert "one" in instructions and "json" in instructions and "action" in instructions
    assert "tool" in instructions and "do not" in instructions


def test_codex_client_should_close_process_when_initialization_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _FakeProcess()
    monkeypatch.setattr("tools.runtime.codex_client.subprocess.Popen", lambda *args, **kwargs: process)
    client = CodexAppServerClient(repo_root=Path.cwd())

    def fail_initialize(method: str, params: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        raise AgentClientUnavailable(f"failed method: {method}")

    monkeypatch.setattr(client, "_request", fail_initialize)
    with pytest.raises(AgentClientUnavailable, match="initialize"):
        client.start()

    assert process.terminated is True
    assert process.stdin.closed is True
    assert client._process is None
