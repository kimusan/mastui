import asyncio
import os
import pytest
from mastui.web import MastuiWebBridge, WEB_HTML, WebSocketConnection


def test_web_html_template():
    assert "xterm" in WEB_HTML
    assert "FitAddon" in WEB_HTML
    assert "Unicode11Addon" in WEB_HTML
    assert "terminal-container" in WEB_HTML
    assert "WebSocket" in WEB_HTML


def test_web_bridge_init():
    bridge = MastuiWebBridge(cols=100, rows=30, args=["--debug"])
    assert bridge.cols == 100
    assert bridge.rows == 30
    assert "--debug" in bridge.cli_args
    assert bridge.master_fd is None
    assert bridge.pid is None


def test_web_bridge_resize():
    bridge = MastuiWebBridge(cols=80, rows=24)
    # Master fd is None, should handle gracefully without crashing
    bridge.resize_pty(120, 40)
    assert bridge.cols == 120
    assert bridge.rows == 40


@pytest.mark.asyncio
async def test_websocket_connection_framing():
    # Mock asyncio reader/writer with mock stream
    class MockWriter:
        def __init__(self):
            self.data = bytearray()
            self.closed = False

        def write(self, d):
            self.data.extend(d)

        async def drain(self):
            pass

        def close(self):
            self.closed = True

    class MockReader:
        def __init__(self, data: bytes):
            self._buffer = bytearray(data)

        async def readexactly(self, n: int) -> bytes:
            if len(self._buffer) < n:
                raise asyncio.IncompleteReadError(bytes(self._buffer), n)
            chunk = bytes(self._buffer[:n])
            del self._buffer[:n]
            return chunk

    writer = MockWriter()
    conn = WebSocketConnection(reader=None, writer=writer)
    await conn.send_text("hello mastui")
    assert len(writer.data) > 0
    assert b"hello mastui" in bytes(writer.data)

    # Test reading masked client frame
    raw_payload = b"test message"
    mask_key = b"\x12\x34\x56\x78"
    masked_data = bytes([b ^ mask_key[i % 4] for i, b in enumerate(raw_payload)])
    frame = bytearray([0x81, 0x80 | len(raw_payload)]) + mask_key + masked_data

    reader = MockReader(bytes(frame))
    conn = WebSocketConnection(reader=reader, writer=writer)
    received = await conn.read_frame()
    assert received == "test message"

    # Test unmasked frame is rejected
    unmasked_frame = bytearray([0x81, len(raw_payload)]) + raw_payload
    reader_unmasked = MockReader(bytes(unmasked_frame))
    conn_unmasked = WebSocketConnection(reader=reader_unmasked, writer=writer)
    received_unmasked = await conn_unmasked.read_frame()
    assert received_unmasked is None
    assert conn_unmasked.closed is True

    # Test fragmented frame assembly (frame 1 + continuation frame 2)
    part1 = b"hello "
    part2 = b"world"
    mask1 = b"\x11\x22\x33\x44"
    mask2 = b"\x55\x66\x77\x88"
    m_part1 = bytes([b ^ mask1[i % 4] for i, b in enumerate(part1)])
    m_part2 = bytes([b ^ mask2[i % 4] for i, b in enumerate(part2)])

    f1 = bytearray([0x01, 0x80 | len(part1)]) + mask1 + m_part1  # FIN=0, text (0x1)
    f2 = bytearray([0x80, 0x80 | len(part2)]) + mask2 + m_part2  # FIN=1, cont (0x0)

    frag_reader = MockReader(bytes(f1 + f2))
    frag_conn = WebSocketConnection(reader=frag_reader, writer=writer)
    full_msg = await frag_conn.read_frame()
    assert full_msg == "hello world"
