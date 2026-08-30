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

    writer = MockWriter()
    conn = WebSocketConnection(reader=None, writer=writer)
    await conn.send_text("hello mastui")
    assert len(writer.data) > 0
    assert b"hello mastui" in bytes(writer.data)
