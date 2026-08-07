"""Tests for mGBA launch and emulator bridge behavior."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

import tools.runtime.emulators.mgba_bridge as mgba_bridge_module
from tools.runtime.emulators.mgba_bridge import (
    MgbaLaunchConfig,
    MgbaSocketBridge,
    add_wslenv_exports,
)


def test_mgba_launch_command_should_include_script_and_rom(tmp_path: Path) -> None:
    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("/opt/mgba/mgba-qt"),
            rom_path=Path("/roms/firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
        ),
        screenshot_dir=tmp_path,
    )

    assert bridge.build_launch_command() == [
        "/opt/mgba/mgba-qt",
        "--script",
        "tools/runtime/emulators/mgba_bridge.lua",
        "/roms/firered.gba",
    ]

def test_mgba_windows_launch_command_should_stage_lua_script(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lua_bridge = tmp_path / "mgba_bridge.lua"
    lua_bridge.write_text("-- test bridge\n", encoding="utf-8")
    cache_dir = tmp_path / "windows-cache"

    def fake_wsl_to_windows_path(path: Path) -> str:
        return "C:\\" + str(path).replace("/", "\\").lstrip("\\")

    monkeypatch.setattr(mgba_bridge_module, "wsl_to_windows_path", fake_wsl_to_windows_path)
    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("/mnt/c/Emulation/mGBA/mGBA.exe"),
            rom_path=Path("/mnt/c/roms/firered.gba"),
            lua_bridge=lua_bridge,
            windows_paths=True,
            script_cache_dir=cache_dir,
        ),
        screenshot_dir=tmp_path / "screenshots",
    )

    command = bridge.build_launch_command()

    assert command[0] == "/mnt/c/Emulation/mGBA/mGBA.exe"
    assert command[1] == "--script"
    assert command[2].endswith("\\windows-cache\\mgba_bridge.lua")
    assert command[3].endswith("\\mnt\\c\\roms\\firered.gba")
    assert (cache_dir / "mgba_bridge.lua").read_text(encoding="utf-8") == "-- test bridge\n"

def test_mgba_windows_env_should_export_runtime_variables_to_win32() -> None:
    env = {
        "WSLENV": "EXISTING/w",
        "POKEMON_RUNTIME_HOST": "127.0.0.1",
        "POKEMON_RUNTIME_PORT": "8766",
    }

    updated = add_wslenv_exports(env, ["POKEMON_RUNTIME_HOST", "POKEMON_RUNTIME_BIND_HOST", "POKEMON_RUNTIME_PORT"])

    assert updated["WSLENV"] == "EXISTING/w:POKEMON_RUNTIME_HOST/w:POKEMON_RUNTIME_PORT/w"
    assert env["WSLENV"] == "EXISTING/w"

# Regression contract for the WSL-to-Windows Lua client connection startup.


def test_mgba_lua_client_should_retry_transient_connection() -> None:
    """Keep the bridge alive while Windows loopback forwarding becomes ready."""

    bridge = Path("tools/runtime/emulators/mgba_bridge.lua").read_text(encoding="utf-8")

    assert "MAX_CLIENT_CONNECT_ATTEMPTS" in bridge
    assert "CLIENT_CONNECT_RETRY_FRAMES" in bridge
    assert "callbacks:add(\"frame\", retry_client_connection)" in bridge
    assert "socket.connect(connect_host, port)" in bridge

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000002000100a5f645400000000"
    "049454e44ae426082"
)


def require_local_socket() -> None:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        pytest.skip("local socket creation is unavailable in this execution sandbox")
    probe.close()

def test_mgba_socket_bridge_should_parse_socket_responses(tmp_path: Path) -> None:
    require_local_socket()
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
    require_local_socket()
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
    require_local_socket()
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

def test_mgba_socket_bridge_should_serialize_line_protocol_requests(tmp_path: Path) -> None:
    class ContentionFile:
        def __init__(self) -> None:
            self.active = 0
            self.max_active = 0
            self.lock = threading.Lock()

        def write(self, raw: bytes) -> None:
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.02)

        def readline(self) -> bytes:
            time.sleep(0.02)
            with self.lock:
                self.active -= 1
            return b"ok\tvalue=42\tframe=1\n"

    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("mgba-qt"),
            rom_path=Path("firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
        ),
        screenshot_dir=tmp_path,
    )
    bridge._file = ContentionFile()
    threads = [threading.Thread(target=lambda: assert_read8(bridge), daemon=True) for _ in range(5)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)

    assert bridge._file.max_active == 1

def test_mgba_memory_reads_should_update_frame_count(tmp_path: Path) -> None:
    class ReadFile:
        def write(self, _raw: bytes) -> None:
            pass

        def readline(self) -> bytes:
            return b"ok\tvalue=42\tframe=77\n"

    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("mgba-qt"),
            rom_path=Path("firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
        ),
        screenshot_dir=tmp_path,
    )
    bridge._file = ReadFile()

    assert bridge.read8(0x02000000) == 42
    assert bridge.frame_count == 77

def test_mgba_snapshots_should_use_unique_files(tmp_path: Path) -> None:
    class ScreenshotFile:
        def __init__(self) -> None:
            self.paths: list[Path] = []

        def write(self, raw: bytes) -> None:
            _command, path = raw.decode("utf-8").strip().split("\t")
            screenshot_path = Path(path)
            self.paths.append(screenshot_path)
            screenshot_path.write_bytes(PNG_BYTES)

        def readline(self) -> bytes:
            return b"ok\tframe=21\n"

    bridge = MgbaSocketBridge(
        MgbaLaunchConfig(
            executable=Path("mgba-qt"),
            rom_path=Path("firered.gba"),
            lua_bridge=Path("tools/runtime/emulators/mgba_bridge.lua"),
        ),
        screenshot_dir=tmp_path,
    )
    bridge._file = ScreenshotFile()

    first = bridge.snapshot()
    second = bridge.snapshot()

    assert first.image_base64 == second.image_base64
    assert len(set(bridge._file.paths)) == 2

def assert_read8(bridge: MgbaSocketBridge) -> None:
    assert bridge.read8(0x02000000) == 42
