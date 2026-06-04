"""Synchronous ASGI request helper for runtime endpoint tests.

The pinned FastAPI/Starlette/TestClient stack in the local runtime venv can hang
under `fastapi.testclient.TestClient`. These tests use httpx's ASGI transport
directly so endpoint behavior remains covered without depending on that wrapper.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
import starlette
from fastapi import FastAPI


def request(app: FastAPI, method: str, path: str, json: dict[str, Any] | None = None) -> httpx.Response:
    """Run one ASGI request and return the httpx response."""

    if _major_version(starlette.__version__) >= 1:
        pytest.skip("endpoint ASGI tests require the repo-pinned starlette<1.0 runtime dependency")

    async def _request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, json=json)

    return asyncio.run(_request())


def _major_version(version: str) -> int:
    return int(version.split(".", 1)[0])
