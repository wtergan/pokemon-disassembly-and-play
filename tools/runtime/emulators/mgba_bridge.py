"""mGBA socket bridge for the dedicated runtime instance.

The bridge talks to `mgba_bridge.lua` over a tiny line-oriented protocol. Python
owns process launch, path conversion, screenshot file reads, and API-facing
models; Lua owns the in-emulator memory/input/screenshot primitives.
"""

from __future__ import annotations

import base64
import os
import socket
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .base import EmulatorHealth, Snapshot


class MgbaBridgeError(RuntimeError):
    """Raised when the mGBA socket bridge cannot satisfy a runtime request."""


ConnectionMode = Literal["lua_server", "lua_client"]
FrameAdvanceMode = Literal["lua_run_frame", "realtime_wait"]


@dataclass(frozen=True)
class MgbaLaunchConfig:
    """Launch settings for a dedicated mGBA runtime process."""

    executable: Path
    rom_path: Path
    lua_bridge: Path
    host: str = "127.0.0.1"
    bind_host: str | None = None
    port: int = 8766
    windows_paths: bool = False
    connection_mode: ConnectionMode = "lua_server"
    frame_advance_mode: FrameAdvanceMode = "lua_run_frame"
    target_fps: float = 60.0
    script_cache_dir: Path | None = None
    log_file: Path | None = None


class MgbaSocketBridge:
    """Socket-backed implementation of the emulator bridge contract."""

    def __init__(
        self,
        launch_config: MgbaLaunchConfig,
        screenshot_dir: Path,
        connect_timeout: float = 20.0,
        request_timeout: float = 5.0,
    ) -> None:
        self._config = launch_config
        self._screenshot_dir = screenshot_dir
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout
        self._process: subprocess.Popen[bytes] | None = None
        self._socket: socket.socket | None = None
        self._listen_socket: socket.socket | None = None
        self._file = None
        self._frame_count = 0
        self._request_lock = threading.Lock()

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def build_launch_command(self) -> list[str]:
        """Build the mGBA command without starting a process."""

        return [
            str(self._config.executable),
            "--script",
            self._path_for_emulator(self._lua_bridge_for_emulator()),
            self._path_for_emulator(self._config.rom_path),
        ]

    def launch(self) -> None:
        """Start mGBA and connect to the Lua socket bridge."""

        env = os.environ.copy()
        env["POKEMON_RUNTIME_HOST"] = self._config.host
        if self._config.bind_host is not None:
            env["POKEMON_RUNTIME_BIND_HOST"] = self._config.bind_host
        env["POKEMON_RUNTIME_PORT"] = str(self._config.port)
        env["POKEMON_RUNTIME_CONNECTION_MODE"] = "client" if self._config.connection_mode == "lua_client" else "server"
        if self._config.log_file is not None:
            env["POKEMON_RUNTIME_LOG_FILE"] = self._path_for_emulator(self._config.log_file)
        if self._config.windows_paths:
            env = add_wslenv_exports(
                env,
                [
                    "POKEMON_RUNTIME_HOST",
                    "POKEMON_RUNTIME_BIND_HOST",
                    "POKEMON_RUNTIME_PORT",
                    "POKEMON_RUNTIME_CONNECTION_MODE",
                    "POKEMON_RUNTIME_LOG_FILE",
                ],
            )
            cwd = self._config.executable.parent
        else:
            cwd = None
        try:
            if self._config.connection_mode == "lua_client":
                self._start_listener()
            self._process = subprocess.Popen(self.build_launch_command(), env=env, cwd=cwd)
            if self._config.connection_mode == "lua_client":
                self._accept_connection()
            else:
                self.connect()
        except Exception:
            self.close()
            raise

    def connect(self) -> None:
        """Connect to an already-running Lua bridge."""

        deadline = time.monotonic() + self._connect_timeout
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            try:
                bridge_socket = socket.create_connection((self._config.host, self._config.port), timeout=1.0)
                self._attach_socket(bridge_socket)
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.1)
        raise MgbaBridgeError(f"could not connect to mGBA bridge: {last_error}") from last_error

    def listen_for_client(self) -> None:
        """Listen for a Lua-client bridge and finish the runtime handshake."""

        self._start_listener()
        self._accept_connection()

    def close(self) -> None:
        """Close socket and terminate the owned mGBA process if one was started."""

        if self._file is not None:
            self._file.close()
            self._file = None
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._listen_socket is not None:
            self._listen_socket.close()
            self._listen_socket = None
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            self._process = None

    def health(self) -> EmulatorHealth:
        fields = self._request("ping")
        self._update_frame_count(fields)
        return EmulatorHealth(running=True, frame=self._frame_count, bridge=fields.get("bridge", "mgba"))

    def snapshot(self) -> Snapshot:
        screenshot_path = self._next_screenshot_path()
        with self._request_lock:
            fields = self._request_unlocked("screenshot", self._path_for_emulator(screenshot_path))
            self._update_frame_count(fields)
            image_bytes = screenshot_path.read_bytes()
        return Snapshot(frame=self._frame_count, image_base64=base64.b64encode(image_bytes).decode("ascii"))

    def press_button(self, button: str) -> None:
        fields = self._request("press", button)
        self._update_frame_count(fields)

    def release_button(self, button: str) -> None:
        fields = self._request("release", button)
        self._update_frame_count(fields)

    def run_frames(self, frames: int) -> None:
        if self._config.frame_advance_mode == "realtime_wait":
            if frames > 0:
                time.sleep(frames / self._config.target_fps)
            self.health()
            return
        fields = self._request("run", str(frames))
        self._update_frame_count(fields)

    def read8(self, address: int) -> int:
        fields = self._request("read8", str(address))
        self._update_frame_count(fields)
        return int(fields["value"])

    def read16(self, address: int) -> int:
        fields = self._request("read16", str(address))
        self._update_frame_count(fields)
        return int(fields["value"])

    def read32(self, address: int) -> int:
        fields = self._request("read32", str(address))
        self._update_frame_count(fields)
        return int(fields["value"])

    def save_state(self, path: Path) -> None:
        """Save mGBA state to `path` through the Lua bridge."""

        fields = self._request("save_state", self._path_for_emulator(path))
        self._update_frame_count(fields)
        if fields.get("saved") != "true":
            raise MgbaBridgeError("mGBA did not save state")

    def load_state(self, path: Path) -> None:
        """Load mGBA state from `path` through the Lua bridge."""

        fields = self._request("load_state", self._path_for_emulator(path))
        self._update_frame_count(fields)
        if fields.get("loaded") != "true":
            raise MgbaBridgeError("mGBA did not load state")

    def _request(self, command: str, *parts: str) -> dict[str, str]:
        with self._request_lock:
            return self._request_unlocked(command, *parts)

    def _request_unlocked(self, command: str, *parts: str) -> dict[str, str]:
        if self._file is None:
            raise MgbaBridgeError("mGBA bridge is not connected")
        line = "\t".join((command, *parts)) + "\n"
        try:
            self._file.write(line.encode("utf-8"))
            raw = self._file.readline()
        except OSError as exc:
            raise MgbaBridgeError(f"mGBA bridge request timed out or failed for {command}: {exc}") from exc
        if not raw:
            raise MgbaBridgeError("mGBA bridge closed the connection")
        response = raw.decode("utf-8").strip()
        chunks = response.split("\t")
        status = chunks[0] if chunks else ""
        fields = _parse_fields(chunks[1:])
        if status != "ok":
            raise MgbaBridgeError(fields.get("error", response))
        return fields

    def _attach_socket(self, bridge_socket: socket.socket) -> None:
        self._socket = bridge_socket
        self._socket.settimeout(self._request_timeout)
        self._file = self._socket.makefile("rwb", buffering=0)
        self.health()

    def _update_frame_count(self, fields: dict[str, str]) -> None:
        if "frame" in fields:
            self._frame_count = int(fields["frame"])

    def _start_listener(self) -> None:
        if self._listen_socket is not None:
            self._listen_socket.close()
        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_socket.bind((self._config.host, self._config.port))
        self._listen_socket.listen(1)

    def _accept_connection(self) -> None:
        if self._listen_socket is None:
            raise MgbaBridgeError("mGBA bridge listener is not started")
        deadline = time.monotonic() + self._connect_timeout
        last_error: OSError | None = None
        self._listen_socket.settimeout(0.2)
        while time.monotonic() < deadline:
            try:
                bridge_socket, _ = self._listen_socket.accept()
                self._attach_socket(bridge_socket)
                return
            except OSError as exc:
                last_error = exc
        raise MgbaBridgeError(f"mGBA bridge client did not connect: {last_error}") from last_error

    def _path_for_emulator(self, path: Path) -> str:
        if not self._config.windows_paths:
            return str(path)
        return wsl_to_windows_path(path)

    def _lua_bridge_for_emulator(self) -> Path:
        if not self._config.windows_paths:
            return self._config.lua_bridge
        return self._stage_windows_lua_bridge()

    def _stage_windows_lua_bridge(self) -> Path:
        cache_dir = self._windows_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        staged_path = cache_dir / "mgba_bridge.lua"
        staged_path.write_text(self._config.lua_bridge.read_text(encoding="utf-8"), encoding="utf-8")
        return staged_path

    def _next_screenshot_path(self) -> Path:
        if self._config.windows_paths:
            screenshot_dir = self._windows_cache_dir() / "screenshots"
        else:
            screenshot_dir = self._screenshot_dir
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        return screenshot_dir / f"snapshot-{uuid.uuid4().hex}.png"

    def _windows_cache_dir(self) -> Path:
        if self._config.script_cache_dir is not None:
            return self._config.script_cache_dir
        return self._config.executable.parent / "pokemon-runtime-cache"


def _parse_fields(parts: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            fields[key] = value
    return fields


def wsl_to_windows_path(path: Path) -> str:
    """Convert a WSL path to a Windows path for Windows GUI emulators."""

    result = subprocess.run(["wslpath", "-w", str(path)], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def add_wslenv_exports(env: dict[str, str], variable_names: list[str]) -> dict[str, str]:
    """Return an environment with selected variables exported to Win32 children."""

    updated = dict(env)
    existing = [entry for entry in updated.get("WSLENV", "").split(":") if entry]
    exported_names = {entry.split("/", 1)[0] for entry in existing}
    for name in variable_names:
        if name in updated and name not in exported_names:
            existing.append(f"{name}/w")
            exported_names.add(name)
    updated["WSLENV"] = ":".join(existing)
    return updated
