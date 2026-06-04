"""FastAPI app factory for the local Pokemon runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .action_executor import ActionValidationError
from .emulators.fake import FakeEmulatorBridge
from .runtime_core import RuntimeCore


def create_app(runtime: RuntimeCore | None = None, static_dir: Path | None = None) -> FastAPI:
    """Create the runtime HTTP app with an injectable runtime core for tests."""

    app = FastAPI(title="Pokemon FireRed Runtime", version="0.1.0")
    runtime_core = runtime or RuntimeCore(FakeEmulatorBridge())

    @app.get("/health")
    def health() -> dict[str, Any]:
        return runtime_core.health()

    @app.get("/snapshot")
    def snapshot() -> dict[str, Any]:
        return runtime_core.snapshot()

    @app.get("/telemetry")
    def telemetry() -> dict[str, Any]:
        return runtime_core.telemetry()

    @app.get("/traces")
    def traces() -> dict[str, Any]:
        return {"traces": runtime_core.recent_traces()}

    @app.post("/action")
    def action(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return runtime_core.execute_action(payload)
        except ActionValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    resolved_static_dir = static_dir or Path(__file__).with_name("static")
    if resolved_static_dir.exists():
        app.mount("/", StaticFiles(directory=resolved_static_dir, html=True), name="static")

    return app

