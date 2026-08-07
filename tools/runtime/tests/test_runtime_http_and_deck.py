"""Tests for runtime HTTP endpoints and the static deck."""

from __future__ import annotations

import subprocess

from tools.runtime.emulators.fake import FakeEmulatorBridge
from tools.runtime.runtime_app import create_app
from tools.runtime.runtime_core import RuntimeCore
from tools.runtime.tests.http_client import request


class CloseTrackingEmulator(FakeEmulatorBridge):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    def close(self) -> None:
        self.closed = True

def test_health_endpoint_should_report_runtime_state() -> None:
    runtime = RuntimeCore(FakeEmulatorBridge())

    response = request(create_app(runtime), "GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "bridge": "fake", "frame": 0, "detail": ""}

def test_configured_runtime_app_should_disable_docs_routes() -> None:
    runtime = RuntimeCore(FakeEmulatorBridge())
    app = create_app(runtime)

    assert request(app, "GET", "/docs").status_code == 404
    assert request(app, "GET", "/openapi.json").status_code == 404

def test_runtime_close_should_release_emulator_resources() -> None:
    emulator = CloseTrackingEmulator()
    runtime = RuntimeCore(emulator)

    runtime.close()

    assert emulator.closed is True

def test_runtime_api_client_should_call_expected_endpoints() -> None:
    result = subprocess.run(
        ["node", "--input-type=module"],
        input="""
import assert from "node:assert/strict";
import { RuntimeApiClient } from "./tools/runtime/static/api-client.js";

const calls = [];
const client = new RuntimeApiClient({
  timeoutMs: 100,
  fetchImpl: async (path, options = {}) => {
    calls.push({ path, options });
    return {
      ok: true,
      json: async () => ({ path, method: options.method || "GET" }),
      text: async () => "",
      statusText: "OK",
    };
  },
});

assert.deepEqual(await client.health(), { path: "/health", method: "GET" });
assert.deepEqual(await client.snapshot(), { path: "/snapshot", method: "GET" });
assert.deepEqual(await client.telemetry(), { path: "/telemetry", method: "GET" });
assert.deepEqual(await client.traces(), { path: "/traces", method: "GET" });
assert.deepEqual(await client.states(), { path: "/states", method: "GET" });
assert.deepEqual(await client.agentStatus(), { path: "/agent/status", method: "GET" });
assert.deepEqual(await client.agentStep({}), { path: "/agent/step", method: "POST" });
assert.deepEqual(await client.agentObjective({ objective: { max_steps: 1 } }), { path: "/agent/objective", method: "POST" });
assert.deepEqual(await client.agentStop(), { path: "/agent/stop", method: "POST" });
assert.deepEqual(await client.saveState("quick slot"), { path: "/states/quick%20slot/save", method: "POST" });
assert.deepEqual(await client.loadState("quick"), { path: "/states/quick/load", method: "POST" });
assert.deepEqual(await client.action({ action: "tap", button: "a", frames: 12 }), {
  path: "/action",
  method: "POST",
});
assert.equal(calls[6].options.body, JSON.stringify({}));
assert.equal(calls[7].options.body, JSON.stringify({ objective: { max_steps: 1 } }));
assert.equal(calls[11].options.body, JSON.stringify({ action: "tap", button: "a", frames: 12 }));
""",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

def test_runtime_api_client_should_surface_json_error_detail() -> None:
    result = subprocess.run(
        ["node", "--input-type=module"],
        input="""
import assert from "node:assert/strict";
import { RuntimeApiClient } from "./tools/runtime/static/api-client.js";

const client = new RuntimeApiClient({
  timeoutMs: 100,
  fetchImpl: async () => ({
    ok: false,
    json: async () => ({ detail: "bad action" }),
    text: async () => "",
    statusText: "Bad Request",
  }),
});

await assert.rejects(() => client.action({}), /bad action/);
""",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

def test_runtime_api_client_should_report_timeouts() -> None:
    result = subprocess.run(
        ["node", "--input-type=module"],
        input="""
import assert from "node:assert/strict";
import { RuntimeApiClient } from "./tools/runtime/static/api-client.js";

const client = new RuntimeApiClient({
  timeoutMs: 1,
  fetchImpl: (_path, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => {
      reject(new DOMException("aborted", "AbortError"));
    });
  }),
});

await assert.rejects(() => client.telemetry(), /request timed out: \\/telemetry/);
""",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

def test_static_deck_should_serve_index() -> None:
    response = request(create_app(), "GET", "/")

    assert response.status_code == 200
    assert "FireRed Runtime" in response.text
    assert 'id="agent-status"' in response.text
    assert 'id="agent-step"' in response.text
    assert 'id="run-objective"' in response.text
    assert 'id="stop-agent"' in response.text
    assert "/app.js" in response.text


def test_model_requests_should_outlive_short_health_timeout() -> None:
    result = subprocess.run(
        ['node', '--input-type=module'],
        input='''
import assert from "node:assert/strict";
import { RuntimeApiClient } from "./tools/runtime/static/api-client.js";
const client = new RuntimeApiClient({timeoutMs: 5, fetchImpl: (_path, {signal}) => new Promise((resolve,reject) => {
  const timer = setTimeout(() => resolve({ok:true,json:async()=>({ok:true})}),30);
  signal.addEventListener("abort",()=>{clearTimeout(timer);reject(new DOMException("aborted","AbortError"));});
})});
await assert.rejects(client.health(), /request timed out/);
assert.deepEqual(await client.agentStep(), {ok:true});
assert.deepEqual(await client.agentObjective({objective:{max_steps:1}}), {ok:true});
''', text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
