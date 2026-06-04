"""Planner client contracts for the runtime agent loop.

The runtime should remain useful without Codex credentials or an app-server
process. This module keeps the planner boundary injectable: disabled mode is
the default, fake mode supports deterministic tests, and the app-server adapter
fails closed unless explicitly configured and available.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import queue
import shutil
import subprocess
from pathlib import Path
from threading import Lock, Thread
import time
from typing import Any, Protocol


class AgentClientError(RuntimeError):
    """Base error raised by planner clients."""


class AgentClientDisabled(AgentClientError):
    """Raised when agent planning is intentionally disabled."""


class AgentClientUnavailable(AgentClientError):
    """Raised when a configured planner backend is unavailable."""


class PlannerClient(Protocol):
    """Client interface used by `AgentService` to choose one action."""

    def decide(self, context: dict[str, Any], *, operator_prompt: str | None = None) -> "PlannerDecision":
        """Return one planner decision for the supplied agent context."""

    def status(self) -> dict[str, Any]:
        """Return backend status safe for runtime APIs and logs."""


@dataclass(frozen=True)
class PlannerDecision:
    """One normalized planner decision."""

    action_id: str
    reason: str
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], context: dict[str, Any]) -> "PlannerDecision":
        """Validate planner output against the context's advertised actions."""

        action_id = str(payload.get("action_id") or payload.get("action") or "").strip()
        reason = str(payload.get("reason") or "").strip()
        if not action_id:
            raise AgentClientError("planner decision missing action_id")
        if not reason:
            raise AgentClientError("planner decision missing reason")
        allowed_ids = {action["id"] for action in context.get("allowed_actions", []) if isinstance(action, dict)}
        if action_id not in allowed_ids:
            raise AgentClientError(f"planner chose unsupported action: {action_id!r}")
        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"action", "action_id", "reason"} and value is not None
        }
        return cls(action_id=action_id, reason=reason[:500], metadata=metadata or None)

    def as_agent_action(self) -> dict[str, Any]:
        """Return the payload accepted by `RuntimeCore.execute_agent_action()`."""

        return {"action_id": self.action_id, "reason": self.reason}


class DisabledAgentClient:
    """Planner client used when no agent backend is configured."""

    def decide(self, context: dict[str, Any], *, operator_prompt: str | None = None) -> PlannerDecision:
        raise AgentClientDisabled("agent planning is disabled")

    def status(self) -> dict[str, Any]:
        return {"mode": "disabled", "available": False, "reason": "agent planning is disabled"}


class FakeAgentClient:
    """Deterministic planner client for tests and offline development."""

    def __init__(self, decisions: list[dict[str, Any]] | None = None) -> None:
        self._decisions: deque[dict[str, Any]] = deque(decisions or [])
        self.calls: list[dict[str, Any]] = []

    def decide(self, context: dict[str, Any], *, operator_prompt: str | None = None) -> PlannerDecision:
        self.calls.append({"context": context, "operator_prompt": operator_prompt})
        payload = self._decisions.popleft() if self._decisions else {"action_id": "wait_short", "reason": "default fake wait"}
        return PlannerDecision.from_mapping(payload, context)

    def status(self) -> dict[str, Any]:
        return {"mode": "fake", "available": True, "queued_decisions": len(self._decisions)}


class CodexAppServerClient:
    """Minimal JSON-line adapter for `codex app-server` structured decisions."""

    def __init__(
        self,
        *,
        repo_root: Path,
        executable: str = "codex",
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.executable = executable
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.thread_id: str | None = None
        self._process: subprocess.Popen[str] | None = None
        self._pending: dict[int, queue.Queue[dict[str, Any]]] = {}
        self._pending_lock = Lock()
        self._events: queue.Queue[dict[str, Any]] = queue.Queue()
        self._next_id = 1
        self._id_lock = Lock()
        self._stdout_thread: Thread | None = None
        self._stderr_thread: Thread | None = None
        self._stderr_lines: deque[str] = deque(maxlen=20)

    def decide(
        self,
        context: dict[str, Any],
        *,
        operator_prompt: str | None = None,
        timeout: float = 120.0,
    ) -> PlannerDecision:
        if shutil.which(self.executable) is None:
            raise AgentClientUnavailable(f"Codex executable not found: {self.executable}")
        self.start()
        allowed_ids = [action["id"] for action in context.get("allowed_actions", []) if isinstance(action, dict)]
        output_schema = {
            "type": "object",
            "properties": {
                "action_id": {"type": "string", "enum": allowed_ids},
                "reason": {"type": "string"},
            },
            "required": ["action_id", "reason"],
            "additionalProperties": False,
        }
        input_items = [
            {
                "type": "text",
                "text": (
                    "Choose exactly one safe Pokemon runtime action. Respond only with JSON matching the schema. "
                    "Use the supplied agent context as the source of truth."
                ),
            },
            {
                "type": "text",
                "text": json.dumps(context, ensure_ascii=True, separators=(",", ":")),
            },
        ]
        if operator_prompt:
            input_items.append({"type": "text", "text": f"Operator note: {operator_prompt}"})

        turn = self._request(
            "turn/start",
            {
                "threadId": self._require_thread_id(),
                "input": input_items,
                "cwd": str(self.repo_root),
                "approvalPolicy": "never",
                "sandboxPolicy": {"type": "readOnly"},
                "model": self.model,
                "effort": self.reasoning_effort,
                "personality": "pragmatic",
                "outputSchema": output_schema,
            },
            timeout=30.0,
        )
        turn_id = (turn.get("turn") or {}).get("id")
        if not turn_id:
            raise AgentClientUnavailable(f"missing turn id from codex app-server: {turn}")
        text = self._wait_for_turn_text(turn_id, timeout=timeout)
        try:
            payload = json.loads(_strip_fence(text))
        except json.JSONDecodeError as exc:
            raise AgentClientUnavailable(f"codex app-server returned non-JSON decision: {text[:240]}") from exc
        return PlannerDecision.from_mapping(payload, context)

    def start(self) -> None:
        """Start app-server stdio transport and create one planner thread."""

        if self._process is not None:
            return
        process = subprocess.Popen(
            [self.executable, "app-server", "--stdio"],
            cwd=self.repo_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        if process.stdin is None or process.stdout is None or process.stderr is None:
            process.kill()
            raise AgentClientUnavailable("codex app-server is missing a stdio pipe")
        self._process = process
        self._stdout_thread = Thread(target=self._read_stdout, daemon=True, name="pokemon-codex-stdout")
        self._stderr_thread = Thread(target=self._read_stderr, daemon=True, name="pokemon-codex-stderr")
        self._stdout_thread.start()
        self._stderr_thread.start()
        self._request(
            "initialize",
            {
                "clientInfo": {"name": "pokemon-runtime", "title": "Pokemon Runtime", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True},
            },
            timeout=15.0,
        )
        self._notify("initialized", {})
        result = self._request(
            "thread/start",
            {
                "cwd": str(self.repo_root),
                "approvalPolicy": "never",
                "sandboxPolicy": {"type": "readOnly"},
                "model": self.model,
                "effort": self.reasoning_effort,
                "personality": "pragmatic",
                "dynamicTools": [],
            },
            timeout=15.0,
        )
        self.thread_id = (result.get("thread") or {}).get("id")
        if not self.thread_id:
            raise AgentClientUnavailable(f"missing thread id from codex app-server: {result}")

    def close(self) -> None:
        """Stop the app-server subprocess if this client started it."""

        process = self._process
        if process is None:
            return
        if process.stdin is not None:
            process.stdin.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        self._process = None

    def status(self) -> dict[str, Any]:
        return {
            "mode": "app_server",
            "available": shutil.which(self.executable) is not None,
            "executable": self.executable,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "thread_id": self.thread_id,
            "stderr": list(self._stderr_lines),
        }

    def _request(self, method: str, params: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        request_id = self._next_request_id()
        response_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[request_id] = response_queue
        self._write({"id": request_id, "method": method, "params": params})
        try:
            message = response_queue.get(timeout=timeout)
        except queue.Empty as exc:
            with self._pending_lock:
                self._pending.pop(request_id, None)
            raise AgentClientUnavailable(f"timed out waiting for codex app-server method: {method}") from exc
        if "error" in message:
            raise AgentClientUnavailable(f"codex app-server {method} failed: {message['error']}")
        return message.get("result") or {}

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"method": method, "params": params})

    def _wait_for_turn_text(self, turn_id: str, *, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        message_text: dict[str, str] = {}
        final_text = ""
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                message = self._events.get(timeout=remaining)
            except queue.Empty as exc:
                raise AgentClientUnavailable(f"timed out waiting for codex turn: {turn_id}") from exc
            method = message.get("method")
            params = message.get("params") or {}
            if method == "item/agentMessage/delta":
                item_id = params.get("itemId")
                if item_id:
                    message_text[item_id] = message_text.get(item_id, "") + params.get("delta", "")
            elif method == "item/completed":
                item = params.get("item") or {}
                item_id = item.get("id")
                if item.get("type") == "agentMessage":
                    final_text = item.get("text") or (message_text.get(item_id) if item_id else "") or final_text
            elif method == "turn/completed":
                turn = params.get("turn") or {}
                if turn.get("id") != turn_id:
                    continue
                if turn.get("status") != "completed":
                    raise AgentClientUnavailable(f"codex turn ended with status {turn.get('status')!r}")
                if not final_text:
                    final_text = _agent_text_from_turn(turn, message_text)
                if not final_text:
                    raise AgentClientUnavailable("codex turn completed without an agent message")
                return final_text
        raise AgentClientUnavailable(f"timed out waiting for codex turn: {turn_id}")

    def _next_request_id(self) -> int:
        with self._id_lock:
            request_id = self._next_id
            self._next_id += 1
        return request_id

    def _write(self, payload: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise AgentClientUnavailable("codex app-server is not running")
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()

    def _read_stdout(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        for raw_line in self._process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = message.get("id")
            if request_id is not None and ("result" in message or "error" in message):
                with self._pending_lock:
                    response_queue = self._pending.pop(request_id, None)
                if response_queue is not None:
                    response_queue.put(message)
                    continue
            self._events.put(message)

    def _read_stderr(self) -> None:
        assert self._process is not None and self._process.stderr is not None
        for raw_line in self._process.stderr:
            line = raw_line.strip()
            if line:
                self._stderr_lines.append(line)

    def _require_thread_id(self) -> str:
        if not self.thread_id:
            raise AgentClientUnavailable("codex app-server thread is not initialized")
        return self.thread_id


def _strip_fence(text: str) -> str:
    normalized = text.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
            return "\n".join(lines[1:-1]).strip()
    return normalized


def _agent_text_from_turn(turn: dict[str, Any], deltas: dict[str, str]) -> str:
    for item in turn.get("items") or []:
        if item.get("type") != "agentMessage":
            continue
        item_id = item.get("id")
        text = item.get("text") or (deltas.get(item_id) if item_id else "")
        if text:
            return text
    return ""
