from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

from tools.runtime.emulators.mgba_bridge import MgbaLaunchConfig, MgbaSocketBridge


PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000002000100a5f645400000000"
    "049454e44ae426082"
)


def test_mgba_socket_bridge_should_parse_socket_responses(tmp_path: Path) -> None:
    host = "127.0.0.1"
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, 0))
    server.listen(1)
    port = server.getsockname()[1]
    seen: list[str] = []

    def serve() -> None:
        conn, _ = server.accept()
        with conn, conn.makefile("rwb", buffering=0) as file:
            while raw := file.readline():
                command = raw.decode("utf-8").strip()
                seen.append(command)
                name, *parts = command.split("\t")
                if name == "ping":
                    file.write(b"ok\tbridge=mgba\tframe=7\n")
                elif name == "press":
                    file.write(b"ok\tframe=7\n")
                elif name == "run":
                    file.write(b"ok\tframe=10\n")
                elif name == "release":
                    file.write(b"ok\tframe=10\n")
                elif name == "read8":
                    file.write(b"ok\tvalue=42\tframe=10\n")
                elif name == "screenshot":
                    Path(parts[0]).write_bytes(PNG_BYTES)
                    file.write(b"ok\tframe=10\n")
                    break
        server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("mgba-qt"),
            rom_path=Path("firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
            host=host,
            port=port,
        ),
        screenshot_dir=tmp_path,
    )

    bridge.connect()
    assert bridge.health().bridge == "mgba"
    bridge.press_button("a")
    bridge.run_frames(3)
    bridge.release_button("a")
    assert bridge.read8(0x02000000) == 42
    snapshot = bridge.snapshot()

    assert snapshot.frame == 10
    assert snapshot.mime_type == "image/png"
    assert "screenshot" in seen[-1]
    bridge.close()
    thread.join(timeout=1)


def test_mgba_socket_bridge_should_accept_lua_client_connection(tmp_path: Path) -> None:
    host = "127.0.0.1"
    probe_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe_socket.bind((host, 0))
    port = probe_socket.getsockname()[1]
    probe_socket.close()

    def client() -> None:
        deadline = time.monotonic() + 2.0
        while True:
            try:
                conn = socket.create_connection((host, port), timeout=0.2)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)
        with conn:
            with conn.makefile("rwb", buffering=0) as file:
                raw = file.readline()
                assert raw.decode("utf-8").strip() == "ping"
                file.write(b"ok\tbridge=mgba\tframe=12\n")

    thread = threading.Thread(target=client, daemon=True)
    thread.start()
    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("mgba-qt"),
            rom_path=Path("firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
            host=host,
            port=port,
            connection_mode="lua_client",
        ),
        screenshot_dir=tmp_path,
    )

    bridge.listen_for_client()

    assert bridge.frame_count == 12
    bridge.close()
    thread.join(timeout=1)


def test_mgba_realtime_wait_should_not_send_lua_run_command(tmp_path: Path, monkeypatch) -> None:
    host = "127.0.0.1"
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, 0))
    server.listen(1)
    port = server.getsockname()[1]
    seen: list[str] = []
    sleeps: list[float] = []

    def serve() -> None:
        conn, _ = server.accept()
        with conn, conn.makefile("rwb", buffering=0) as file:
            for frame in (3, 9):
                command = file.readline().decode("utf-8").strip()
                seen.append(command)
                file.write(f"ok\tbridge=mgba\tframe={frame}\n".encode("utf-8"))
        server.close()

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("tools.runtime.emulators.mgba_bridge.time.sleep", fake_sleep)
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("mgba-qt"),
            rom_path=Path("firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
            host=host,
            port=port,
            frame_advance_mode="realtime_wait",
        ),
        screenshot_dir=tmp_path,
    )

    bridge.connect()
    bridge.run_frames(6)

    assert seen == ["ping", "ping"]
    assert sleeps == [0.1]
    assert bridge.frame_count == 9
    bridge.close()
    thread.join(timeout=1)
