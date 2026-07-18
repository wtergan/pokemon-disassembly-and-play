"""Behavioral coverage for bounded bridge reads and fresh telemetry pages."""

from pathlib import Path
import socket
from threading import Thread

import pytest

from tools.runtime.emulators.mgba_bridge import MgbaLaunchConfig, MgbaSocketBridge, MgbaBridgeError
from tools.runtime.games.firered.memory import BufferedMemory


@pytest.mark.parametrize('encoded,expected', [('0102feff', b'\x01\x02\xfe\xff'), ('01', None), ('zz', None)])
def test_memory_reply_should_validate_exact_requested_bytes(tmp_path, encoded, expected):
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    seen = []

    def serve():
        conn, _ = server.accept()
        with conn, conn.makefile('rwb', buffering=0) as stream:
            seen.append(stream.readline())
            stream.write(b'ok\tframe=1\n')
            seen.append(stream.readline())
            stream.write(f'ok\tdata={encoded}\tframe=2\n'.encode())
        server.close()

    thread = Thread(target=serve)
    thread.start()
    bridge = MgbaSocketBridge(MgbaLaunchConfig(executable=Path('mgba'), rom_path=Path('game.gba'), lua_bridge=Path('bridge.lua'), port=server.getsockname()[1]), screenshot_dir=tmp_path)
    try:
        bridge.connect()
        if expected is None:
            with pytest.raises(MgbaBridgeError):
                bridge.read_range(0x02000000, 4)
        else:
            assert bridge.read_range(0x02000000, 4) == expected
    finally:
        bridge.close()
        thread.join(timeout=2)
    assert seen[-1] == b'read_range\t33554432\t4\n'


def test_observation_should_cache_pages_and_refresh_next_observation():
    class Memory:
        frame_count = 1
        calls = []
        value = 1

        def read_range(self, address, length):
            self.calls.append((address, length))
            return bytes([self.value]) * length

    source = Memory()
    first = BufferedMemory(source)
    assert first.read32(0x02000ffe) == 0x01010101
    source.value = 2
    assert first.read8(0x02001000) == 1
    assert len(source.calls) == 2
    assert BufferedMemory(source).read16(0x02001000) == 0x0202
