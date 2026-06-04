from __future__ import annotations

from pathlib import Path

from tools.runtime.codex_client import FakeAgentClient
from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.tests.http_client import request


def test_agent_status_endpoint_should_preserve_disabled_default() -> None:
    response = request(create_app(RuntimeCore(FakeEmulatorBridge())), "GET", "/agent/status")

    assert response.status_code == 200
    assert response.json()["client"]["mode"] == "disabled"


def test_agent_step_endpoint_should_run_fake_client(tmp_path: Path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)
    runtime.configure_agent_client(FakeAgentClient([{"action_id": "tap_a", "reason": "advance"}]))

    response = request(create_app(runtime), "POST", "/agent/step", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["action_id"] == "tap_a"
    assert payload["result"]["result"]["frame"] == 12


def test_agent_objective_endpoint_should_run_bounded_goal(tmp_path: Path) -> None:
    runtime = RuntimeCore(FakeEmulatorBridge(), state_dir=tmp_path)
    runtime.configure_agent_client(FakeAgentClient())

    response = request(
        create_app(runtime),
        "POST",
        "/agent/objective",
        json={"objective": {"description": "wait", "max_steps": 1, "success": {"runtime_frame_at_least": 15}}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_agent_step_endpoint_should_report_disabled_client() -> None:
    response = request(create_app(RuntimeCore(FakeEmulatorBridge())), "POST", "/agent/step", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "agent planning is disabled"
