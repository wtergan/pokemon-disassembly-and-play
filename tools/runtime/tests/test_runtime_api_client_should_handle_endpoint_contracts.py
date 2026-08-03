from __future__ import annotations

import subprocess


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
