"""Regression contract for the WSL-to-Windows Lua client connection startup."""

from pathlib import Path


def test_mgba_lua_client_should_retry_transient_connection() -> None:
    """Keep the bridge alive while Windows loopback forwarding becomes ready."""

    bridge = Path("tools/runtime/emulators/mgba_bridge.lua").read_text(encoding="utf-8")

    assert "MAX_CLIENT_CONNECT_ATTEMPTS" in bridge
    assert "CLIENT_CONNECT_RETRY_FRAMES" in bridge
    assert "callbacks:add(\"frame\", retry_client_connection)" in bridge
    assert "socket.connect(connect_host, port)" in bridge
