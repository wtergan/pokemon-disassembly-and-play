from __future__ import annotations

from tools.runtime.runtime_app import create_app
from tools.runtime.tests.http_client import request


def test_static_deck_should_serve_index() -> None:
    response = request(create_app(), "GET", "/")

    assert response.status_code == 200
    assert "FireRed Runtime" in response.text
    assert "/app.js" in response.text
