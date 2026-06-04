from __future__ import annotations

from fastapi.testclient import TestClient

from tools.runtime.runtime_app import create_app


def test_static_deck_should_serve_index() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "FireRed Runtime" in response.text
    assert "/app.js" in response.text
