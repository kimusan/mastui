"""
mastui/web.py

Web-based terminal interface for Mastui.
Provides a local HTTP and WebSocket server that bridges interactive Mastui
sessions to web browsers and Android WebView containers.
"""

from __future__ import annotations

import asyncio
import base64
import codecs
import fcntl
import hashlib
import json
import logging
import os
import pty
import select
import selectors
import struct
import sys
import termios
import threading
import time
import webbrowser
from typing import TYPE_CHECKING, Optional, Set

from textual import events
from textual._xterm_parser import XTermParser
from textual.driver import Driver
from textual.geometry import Size

if TYPE_CHECKING:
    from textual.app import App

log = logging.getLogger(__name__)

# Minimal HTML5 + Xterm.js web client with touch & mobile support
WEB_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Mastui Web</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css">
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-unicode11@0.6.0/lib/xterm-addon-unicode11.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 100%;
      height: 100%;
      background: #0d1117;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    }
    #terminal-container {
      width: 100%;
      height: 100%;
      padding: 2px;
    }
    .xterm {
      height: 100%;
    }
    .xterm .xterm-screen {
      image-rendering: pixelated;
    }
    .xterm .xterm-rows {
      line-height: 1.0 !important;
    }
    #status-bar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      background: rgba(22, 27, 34, 0.9);
      color: #8b949e;
      font-size: 12px;
      padding: 4px 12px;
      display: none;
      justify-content: space-between;
      align-items: center;
      z-index: 100;
      border-bottom: 1px solid #30363d;
    }
    #status-bar.show { display: flex; }
    #reconnect-btn {
      background: #238636;
      color: #fff;
      border: none;
      border-radius: 4px;
      padding: 2px 8px;
      cursor: pointer;
      font-size: 11px;
    }
  </style>
</head>
<body>
  <div id="status-bar">
    <span id="status-msg">Connecting to Mastui...</span>
    <button id="reconnect-btn" onclick="connect()">Reconnect</button>
  </div>
  <div id="terminal-container"></div>

  <script>
    const term = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontFamily: '"Cascadia Code", "Fira Code", "Source Code Pro", Menlo, Monaco, Consolas, "Courier New", monospace',
      fontSize: window.innerWidth < 600 ? 12 : 14,
      lineHeight: 1.0,
      letterSpacing: 0,
      customGlyphs: true,
      allowProposedApi: true,
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#58a6ff',
        selectionBackground: '#1f6feb44',
      }
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    if (typeof WebLinksAddon !== 'undefined' && WebLinksAddon.WebLinksAddon) {
      term.loadAddon(new WebLinksAddon.WebLinksAddon());
    }
    let unicode11Instance = null;
    if (typeof Unicode11Addon !== 'undefined' && Unicode11Addon.Unicode11Addon) {
      unicode11Instance = new Unicode11Addon.Unicode11Addon();
      term.loadAddon(unicode11Instance);
      term.unicode.activeVersion = '11';
    }

    // Register comprehensive modern Unicode provider matching Python Rich / Textual (Unicode 15+)
    const modernUnicodeProvider = {
      version: 'unicode-modern',
      wcwidth: function(codepoint) {
        // Zero-width characters (ZWJ, variation selectors, combining marks)
        if (codepoint === 0x200D || (codepoint >= 0xFE00 && codepoint <= 0xFE0F) || (codepoint >= 0xE0100 && codepoint <= 0xE01EF)) {
          return 0;
        }
        // Regional Indicator Symbols (U+1F1E6 to U+1F1FF: Country Flags like 🇮🇹, 🇩🇰)
        // Each indicator is width 1 so a pair of indicators forms a 2-cell flag
        if (codepoint >= 0x1F1E6 && codepoint <= 0x1F1FF) {
          return 1;
        }
        // Enclosed Alphanumeric, Squared Latin, and Alchemical/Geometric symbols (width 1)
        if ((codepoint >= 0x1F100 && codepoint <= 0x1F16F) || (codepoint >= 0x1F190 && codepoint <= 0x1F1AC) || (codepoint >= 0x1F700 && codepoint <= 0x1F8FF) || (codepoint >= 0x1F000 && codepoint <= 0x1F09F)) {
          return 1;
        }
        // Primary Emoji Blocks (U+1F300..U+1F6FF, U+1F900..U+1FAFF, U+1F200..U+1F251, U+1F0A0..U+1F0FF)
        if ((codepoint >= 0x1F300 && codepoint <= 0x1F6FF) || (codepoint >= 0x1F900 && codepoint <= 0x1FAFF) || (codepoint >= 0x1F200 && codepoint <= 0x1F251) || (codepoint >= 0x1F0A0 && codepoint <= 0x1F0FF)) {
          return 2;
        }
        // Remaining Supplementary Multilingual Plane
        if (codepoint >= 0x1F000 && codepoint <= 0x1FFFF) {
          return 2;
        }
        // BMP Symbols and Dingbats with emoji presentation (U+2600..U+27BF, stars U+2B50..U+2B55, symbols)
        if ((codepoint >= 0x2600 && codepoint <= 0x27BF) || (codepoint >= 0x2B50 && codepoint <= 0x2B55) || codepoint === 0x231A || codepoint === 0x231B || (codepoint >= 0x23E9 && codepoint <= 0x23F3) || (codepoint >= 0x23F8 && codepoint <= 0x23FA) || (codepoint >= 0x25AA && codepoint <= 0x25AB) || (codepoint >= 0x25FB && codepoint <= 0x25FE)) {
          return 2;
        }
        // Standard CJK and Fullwidth ranges
        if (codepoint >= 0x1100 && (
          codepoint <= 0x115F ||
          codepoint === 0x2329 || codepoint === 0x232A ||
          (codepoint >= 0x2E80 && codepoint <= 0xA4CF && codepoint !== 0x303F) ||
          (codepoint >= 0xAC00 && codepoint <= 0xD7A3) ||
          (codepoint >= 0xF900 && codepoint <= 0xFAFF) ||
          (codepoint >= 0xFE10 && codepoint <= 0xFE19) ||
          (codepoint >= 0xFE30 && codepoint <= 0xFE6F) ||
          (codepoint >= 0xFF00 && codepoint <= 0xFF60) ||
          (codepoint >= 0xFFE0 && codepoint <= 0xFFE6) ||
          (codepoint >= 0x20000 && codepoint <= 0x2FFFD) ||
          (codepoint >= 0x30000 && codepoint <= 0x3FFFD)
        )) {
          return 2;
        }
        if (unicode11Instance && typeof unicode11Instance.wcwidth === 'function') {
          return unicode11Instance.wcwidth(codepoint);
        }
        return 1;
      }
    };
    try {
      term.unicode.register(modernUnicodeProvider);
      term.unicode.activeVersion = 'unicode-modern';
    } catch (e) {
      console.warn('Could not register modern unicode provider:', e);
    }

    const container = document.getElementById('terminal-container');
    term.open(container);

    fitAddon.fit();

    let ws = null;
    let resizeTimeout = null;
    const statusMsg = document.getElementById('status-msg');
    const statusBar = document.getElementById('status-bar');

    function notifyResize() {
      if (ws && ws.readyState === WebSocket.OPEN) {
        fitAddon.fit();
        ws.send(JSON.stringify({
          type: 'resize',
          cols: term.cols,
          rows: term.rows
        }));
      }
    }

    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        fitAddon.fit();
        notifyResize();
      }, 150);
    });

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      
      statusMsg.textContent = 'Connecting...';
      statusBar.classList.remove('show');

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        statusBar.classList.remove('show');
        fitAddon.fit();
        notifyResize();
        term.focus();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'output') {
            term.write(msg.data);
          }
        } catch (e) {
          term.write(event.data);
        }
      };

      ws.onclose = () => {
        statusMsg.textContent = 'Disconnected from Mastui session';
        statusBar.classList.add('show');
      };

      ws.onerror = () => {
        statusMsg.textContent = 'Connection error';
        statusBar.classList.add('show');
      };
    }

    term.onData((data) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'input', data: data }));
      }
    });

    // Touch support & autofocus
    container.addEventListener('click', () => term.focus());
    connect();
  </script>
</body>
</html>
"""


class WebSocketConnection:
    """Minimal RFC 6455 WebSocket connection handler."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.closed = False

    async def send_text(self, text: str) -> None:
        if self.closed:
            return
        payload = text.encode("utf-8")
        length = len(payload)
        header = bytearray([0x81])  # FIN + Text frame
        if length <= 125:
            header.append(length)
        elif length <= 65535:
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))
        try:
            self.writer.write(header + payload)
            await self.writer.drain()
        except Exception:
            self.closed = True

    async def read_frame(self) -> Optional[str]:
        if self.closed:
            return None
        try:
            head = await self.reader.readexactly(2)
            b1, b2 = head[0], head[1]
            opcode = b1 & 0x0F
            is_masked = bool(b2 & 0x80)
            payload_len = b2 & 0x7F

            if opcode == 0x8:  # Close frame
                self.closed = True
                return None

            if payload_len == 126:
                ext = await self.reader.readexactly(2)
                payload_len = struct.unpack("!H", ext)[0]
            elif payload_len == 127:
                ext = await self.reader.readexactly(8)
                payload_len = struct.unpack("!Q", ext)[0]

            mask = await self.reader.readexactly(4) if is_masked else None
            data = await self.reader.readexactly(payload_len)

            if mask:
                unmasked = bytearray(len(data))
                for i in range(len(data)):
                    unmasked[i] = data[i] ^ mask[i % 4]
                data = bytes(unmasked)

            return data.decode("utf-8", errors="replace")
        except Exception:
            self.closed = True
            return None


class PipeDriver(Driver):
    """Custom Driver for running Textual over pipes or in worker threads without signal.signal or termios requirements."""

    in_fd: int = 0
    out_fd: int = 1

    def __init__(
        self,
        app: App,
        *,
        debug: bool = False,
        mouse: bool = True,
        size: tuple[int, int] | None = None,
    ) -> None:
        super().__init__(app, debug=debug, mouse=mouse, size=size)
        self.exit_event = threading.Event()
        self._key_thread: Optional[threading.Thread] = None

    def start_application_mode(self) -> None:
        cols = int(os.environ.get("COLUMNS", self._size[0] if self._size else 120))
        rows = int(os.environ.get("LINES", self._size[1] if self._size else 35))
        sz = Size(cols, rows)
        ev = events.Resize(sz, sz)
        self.send_message(ev)

        # Enter alternate screen buffer & hide cursor
        self.write("\x1b[?1049h\x1b[?25l")
        if self._mouse:
            # Enable standard & SGR mouse tracking
            self.write("\x1b[?1000h\x1b[?1002h\x1b[?1006h")
        self.flush()

        in_fileno = self.in_fd

        def _run_input() -> None:
            parser = XTermParser(self._debug)
            decoder = codecs.getincrementaldecoder("utf-8")().decode
            sel = selectors.SelectSelector()
            sel.register(in_fileno, selectors.EVENT_READ)
            try:
                while not self.exit_event.is_set():
                    for key, mask in sel.select(0.05):
                        if mask & selectors.EVENT_READ:
                            chunk = os.read(in_fileno, 4096)
                            if not chunk:
                                return
                            u_data = decoder(chunk)
                            for event in parser.feed(u_data):
                                self.process_message(event)
                    for event in parser.tick():
                        self.process_message(event)
            except Exception:
                pass
            finally:
                try:
                    sel.close()
                except Exception:
                    pass

        self._key_thread = threading.Thread(target=_run_input, name="pipe-input", daemon=True)
        self._key_thread.start()

    def stop_application_mode(self) -> None:
        self.close()

    def disable_input(self) -> None:
        pass

    def write(self, data: str) -> None:
        try:
            os.write(self.out_fd, data.encode("utf-8"))
        except Exception:
            pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.exit_event.set()
        if self._mouse:
            self.write("\x1b[?1000l\x1b[?1002l\x1b[?1006l")
        self.write("\x1b[?25h\x1b[?1049l")
        self.flush()


class MastuiWebBridge:
    """Manages pseudo-terminal session running Mastui and bridges to WebSockets."""

    def __init__(self, cols: int = 120, rows: int = 35, args: list[str] | None = None):
        self.cols = cols
        self.rows = rows
        self.cli_args = args or []
        self.master_fd: Optional[int] = None
        self.in_pipe_w: Optional[int] = None
        self.out_pipe_r: Optional[int] = None
        self.pid: Optional[int] = None
        self.clients: Set[WebSocketConnection] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.app_instance = None
        self._running = False
        self.history_buffer: list[str] = []
        self._history_lock = threading.Lock()
        self._max_history_chars = 500000

    def start_pty(self) -> None:
        """Spawn mastui inside a pseudo-terminal (fork, in-process PTY, or pipe fallback)."""
        use_pipes = False
        slave_fd: Optional[int] = None
        in_r: Optional[int] = None
        out_w: Optional[int] = None

        try:
            self.master_fd, slave_fd = pty.openpty()
        except Exception as e:
            log.warning(f"pty.openpty unavailable ({e}), using pipe fallback for terminal I/O")
            use_pipes = True
            in_r, in_w = os.pipe()
            out_r, out_w = os.pipe()
            self.in_pipe_w = in_w
            self.out_pipe_r = out_r

        self.resize_pty(self.cols, self.rows)

        is_android = hasattr(sys, "getandroidapilevel") or "ANDROID_DATA" in os.environ or "ANDROID_ROOT" in os.environ

        if not is_android and not use_pipes and hasattr(os, "fork") and self.master_fd is not None and slave_fd is not None:
            try:
                pid = os.fork()
                if pid == 0:  # Child process
                    os.close(self.master_fd)
                    os.setsid()
                    os.dup2(slave_fd, 0)
                    os.dup2(slave_fd, 1)
                    os.dup2(slave_fd, 2)
                    if slave_fd > 2:
                        os.close(slave_fd)

                    env = os.environ.copy()
                    env["TERM"] = "xterm-256color"
                    env["COLORTERM"] = "truecolor"

                    cmd = [sys.executable, "-m", "mastui.app"] + self.cli_args
                    try:
                        os.execvpe(cmd[0], cmd, env)
                    except Exception as e:
                        print(f"Failed to execute mastui: {e}", file=sys.stderr)
                        os._exit(1)

                # Parent process
                os.close(slave_fd)
                self.pid = pid
                self._running = True
                self._start_child_reaper()
                return
            except Exception as e:
                log.warning(f"os.fork failed ({e}), falling back to in-process execution")

    def _start_child_reaper(self) -> None:
        """Start a daemon thread to reap the child process when it terminates."""
        if self.pid is None:
            return

        def _reap() -> None:
            try:
                if self.pid is not None:
                    os.waitpid(self.pid, 0)
            except (ChildProcessError, OSError):
                pass
            finally:
                self._running = False

        reaper_thread = threading.Thread(target=_reap, daemon=True, name="pty-child-reaper")
        reaper_thread.start()

    def stop(self) -> None:
        """Clean up pseudo-terminal descriptors and gracefully terminate child processes."""
        self._running = False
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None
        if self.in_pipe_w is not None:
            try:
                os.close(self.in_pipe_w)
            except Exception:
                pass
            self.in_pipe_w = None
        if self.out_pipe_r is not None:
            try:
                os.close(self.out_pipe_r)
            except Exception:
                pass
            self.out_pipe_r = None
        if self.pid is not None:
            try:
                os.kill(self.pid, 15)  # SIGTERM
                for _ in range(10):
                    reaped_pid, _ = os.waitpid(self.pid, os.WNOHANG)
                    if reaped_pid != 0:
                        break
                    time.sleep(0.05)
                else:
                    os.kill(self.pid, 9)  # SIGKILL
                    os.waitpid(self.pid, 0)
            except (ProcessLookupError, ChildProcessError, OSError):
                pass
            self.pid = None

        # In-process runner for Android / embedded / pipe fallback environments
        def run_in_process() -> None:
            orig_stdin = os.dup(0)
            orig_stdout = os.dup(1)
            orig_stderr = os.dup(2)
            try:
                if not use_pipes and slave_fd is not None:
                    os.dup2(slave_fd, 0)
                    os.dup2(slave_fd, 1)
                    os.dup2(slave_fd, 2)
                elif in_r is not None and out_w is not None:
                    os.dup2(in_r, 0)
                    os.dup2(out_w, 1)
                    os.dup2(out_w, 2)

                os.environ["TERM"] = "xterm-256color"
                os.environ["COLORTERM"] = "truecolor"
                os.environ["COLUMNS"] = str(self.cols)
                os.environ["LINES"] = str(self.rows)

                from mastui.app import Mastui, setup_logging

                debug = "--debug" in self.cli_args
                ssl_verify = "--no-ssl-verify" not in self.cli_args
                add_account = "--add-account" in self.cli_args
                action = "add_account" if add_account else None

                if use_pipes or is_android:
                    PipeDriver.in_fd = in_r if in_r is not None else 0
                    PipeDriver.out_fd = out_w if out_w is not None else 1
                    os.environ["MASTUI_WEB"] = "1"
                    os.environ["TEXTUAL_DRIVER"] = "mastui.web:PipeDriver"

                log_file_path = setup_logging(debug=debug)
                app = Mastui(action=action, ssl_verify=ssl_verify, debug=debug)
                app.log_file_path = log_file_path
                self.app_instance = app
                app.run(size=(self.cols, self.rows))
            except Exception as ex:
                print(f"Error in in-process Mastui execution: {ex}", file=sys.stderr)
            finally:
                try:
                    os.dup2(orig_stdin, 0)
                    os.dup2(orig_stdout, 1)
                    os.dup2(orig_stderr, 2)
                    os.close(orig_stdin)
                    os.close(orig_stdout)
                    os.close(orig_stderr)
                    if not use_pipes and slave_fd is not None:
                        os.close(slave_fd)
                    elif use_pipes:
                        if in_r is not None:
                            os.close(in_r)
                        if out_w is not None:
                            os.close(out_w)
                except Exception:
                    pass

        thread = threading.Thread(target=run_in_process, name="MastuiInProcess", daemon=True)
        thread.start()
        self._running = True

    def resize_pty(self, cols: int, rows: int) -> None:
        self.cols = max(20, cols)
        self.rows = max(10, rows)
        os.environ["COLUMNS"] = str(self.cols)
        os.environ["LINES"] = str(self.rows)
        if self.master_fd is not None:
            try:
                winsize = struct.pack("HHHH", self.rows, self.cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            except Exception as e:
                log.debug(f"Could not resize PTY: {e}")
        if self.app_instance is not None:
            try:
                sz = Size(self.cols, self.rows)
                self.app_instance.post_message(events.Resize(sz, sz))
            except Exception as e:
                log.debug(f"Could not post Resize event to app: {e}")

    def write_input(self, data: str) -> None:
        raw = data.encode("utf-8")
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, raw)
            except Exception as e:
                log.debug(f"Error writing to master PTY: {e}")
        elif self.in_pipe_w is not None:
            try:
                os.write(self.in_pipe_w, raw)
            except Exception as e:
                log.debug(f"Error writing to input pipe: {e}")

    def start_reader_thread(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        thread = threading.Thread(target=self._read_loop, daemon=True)
        thread.start()

    def _read_loop(self) -> None:
        """Continuously read output from master PTY or output pipe and broadcast to connected clients."""
        read_fd = self.master_fd if self.master_fd is not None else self.out_pipe_r
        while self._running and read_fd is not None:
            try:
                r, _, _ = select.select([read_fd], [], [], 0.05)
                if r:
                    chunk = os.read(read_fd, 4096)
                    if not chunk:
                        break
                    text = chunk.decode("utf-8", errors="replace")
                    with self._history_lock:
                        self.history_buffer.append(text)
                        # Keep history buffer bounded
                        total = sum(len(c) for c in self.history_buffer)
                        while total > self._max_history_chars and len(self.history_buffer) > 1:
                            removed = self.history_buffer.pop(0)
                            total -= len(removed)

                    msg = json.dumps({"type": "output", "data": text})
                    if self.loop and self.clients:
                        asyncio.run_coroutine_threadsafe(self._broadcast(msg), self.loop)
            except (OSError, ValueError):
                break
        self._running = False

    async def _broadcast(self, msg: str) -> None:
        dead = []
        for client in self.clients:
            if client.closed:
                dead.append(client)
            else:
                await client.send_text(msg)
        for client in dead:
            self.clients.discard(client)


async def handle_http_and_ws(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    bridge: MastuiWebBridge,
) -> None:
    """Handle incoming HTTP requests and WebSocket handshakes."""
    try:
        request_line = await reader.readline()
        if not request_line:
            writer.close()
            return
        
        parts = request_line.decode("utf-8").strip().split()
        if len(parts) < 2:
            writer.close()
            return
        
        method, path = parts[0], parts[1]
        headers = {}
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n" or line == b"\n":
                break
            header_str = line.decode("utf-8").strip()
            if ":" in header_str:
                k, v = header_str.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        # Handle WebSocket Upgrade
        if headers.get("upgrade", "").lower() == "websocket" and "sec-websocket-key" in headers:
            key = headers["sec-websocket-key"]
            guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept = base64.b64encode(hashlib.sha1((key + guid).encode()).digest()).decode()

            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            )
            writer.write(response.encode())
            await writer.drain()

            ws = WebSocketConnection(reader, writer)
            bridge.clients.add(ws)

            # Replay history buffer to the newly connected browser / webview
            with bridge._history_lock:
                if bridge.history_buffer:
                    replay_text = "".join(bridge.history_buffer)
                    await ws.send_text(json.dumps({"type": "output", "data": replay_text}))

            # Trigger a full redraw from Textual if running
            if bridge.app_instance is not None:
                try:
                    sz = Size(bridge.cols, bridge.rows)
                    bridge.app_instance.post_message(events.Resize(sz, sz))
                except Exception:
                    pass

            # Process incoming messages
            while not ws.closed:
                msg_text = await ws.read_frame()
                if msg_text is None:
                    break
                try:
                    msg = json.loads(msg_text)
                    m_type = msg.get("type")
                    if m_type == "input":
                        bridge.write_input(msg.get("data", ""))
                    elif m_type == "resize":
                        bridge.resize_pty(msg.get("cols", 120), msg.get("rows", 35))
                except json.JSONDecodeError:
                    bridge.write_input(msg_text)

            bridge.clients.discard(ws)
            writer.close()
            return

        # Serve Web UI
        body = WEB_HTML.encode("utf-8")
        resp = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode() + body
        writer.write(resp)
        await writer.drain()
        writer.close()
    except Exception as e:
        log.debug(f"HTTP/WS connection error: {e}")
        try:
            writer.close()
        except Exception:
            pass


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = True,
    cli_args: list[str] | None = None,
) -> None:
    """Run the Mastui web bridge server."""
    bridge = MastuiWebBridge(args=cli_args)
    bridge.start_pty()

    async def main_async() -> None:
        loop = asyncio.get_running_loop()
        bridge.start_reader_thread(loop)

        server = await asyncio.start_server(
            lambda r, w: handle_http_and_ws(r, w, bridge),
            host,
            port,
        )

        url = f"http://{host}:{port}"
        print(f"\n=======================================================")
        print(f"  Mastui Web Interface running at: {url}")
        print(f"  Press Ctrl+C to stop the server.")
        print(f"=======================================================\n")

        if open_browser:
            try:
                webbrowser.open(url)
            except Exception as e:
                log.debug(f"Could not open browser automatically: {e}")

        async with server:
            await server.serve_forever()

    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping Mastui web server...")
    finally:
        bridge.stop()
