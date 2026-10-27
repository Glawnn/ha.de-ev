"""Fake Dé Pow charger speaking the local Tuya protocol 3.3.

It keeps the charger state in memory and exposes a tiny HTTP control API so
end-to-end tests can inspect it and inject failures.
"""

from __future__ import annotations

import json
import os
import socket
import socketserver
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from tinytuya.core.command_types import CONTROL, DP_QUERY, DP_QUERY_NEW, HEART_BEAT
from tinytuya.core.crypto_helper import AESCipher
from tinytuya.core.header import PREFIX_55AA_VALUE, PROTOCOL_33_HEADER
from tinytuya.core.message_helper import (
    TuyaMessage,
    pack_message,
    parse_header,
    unpack_message,
)

TUYA_PORT = int(os.environ.get("FAKE_TUYA_PORT", "6668"))
CONTROL_PORT = int(os.environ.get("FAKE_CONTROL_PORT", "8080"))
DEFAULT_KEY = os.environ.get("FAKE_LOCAL_KEY", "0123456789abcdef")
HEADER_FRAME = 16


class Charger:
    """In-memory charger state shared by the Tuya and control servers."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.connections: set[socket.socket] = set()
        self.server: socketserver.ThreadingTCPServer | None = None
        self.reset()

    def reset(self) -> None:
        """Restore the initial state: charging at 10 A, default key."""
        with self.lock:
            self.local_key = DEFAULT_KEY
            self.charging = True
            self.target = 10
            self.writes: list[list[Any]] = []
        self.drop_connections()

    def dps(self) -> dict[str, Any]:
        """Return the data points derived from the internal state."""
        current = self.target * 10 if self.charging else 0
        metrics = {"L1": [2300, current, 23], "t": 250, "d": 600, "e": 12}
        return {
            "102": json.dumps(metrics, separators=(",", ":")),
            "109": "WORKING" if self.charging else "IDLEINS",
            "140": self.charging,
            "150": self.target,
            "152": 16,
        }

    def apply(self, changes: dict[str, Any]) -> None:
        """Apply a Tuya CONTROL request."""
        with self.lock:
            for dp, value in changes.items():
                self.writes.append([dp, value])
                if dp == "140":
                    self.charging = bool(value)
                elif dp == "150":
                    self.target = int(value)

    def drop_connections(self) -> int:
        """Close every open Tuya connection."""
        with self.lock:
            sockets = list(self.connections)
            self.connections.clear()
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        return len(sockets)

    def start(self) -> None:
        """Start listening on the Tuya port."""
        with self.lock:
            if self.server is not None:
                return
            server = _TuyaServer(("0.0.0.0", TUYA_PORT), _TuyaHandler)
            server.charger = self
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.server = server

    def stop(self) -> None:
        """Stop listening so the port refuses connections."""
        with self.lock:
            server, self.server = self.server, None
        if server is not None:
            server.shutdown()
            server.server_close()
        self.drop_connections()


class _TuyaServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    charger: Charger


class _TuyaHandler(socketserver.BaseRequestHandler):
    server: _TuyaServer

    def handle(self) -> None:
        charger = self.server.charger
        with charger.lock:
            charger.connections.add(self.request)
        try:
            while self._serve_one(charger):
                pass
        except OSError:
            pass
        finally:
            with charger.lock:
                charger.connections.discard(self.request)
            self.request.close()

    def _read(self, size: int) -> bytes | None:
        data = b""
        while len(data) < size:
            chunk = self.request.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _serve_one(self, charger: Charger) -> bool:
        head = self._read(HEADER_FRAME)
        if head is None:
            return False
        header = parse_header(head)
        rest = self._read(header.total_length - HEADER_FRAME)
        if rest is None:
            return False
        msg = unpack_message(head + rest, no_retcode=True)
        if not msg.crc_good:
            return False

        cipher = AESCipher(charger.local_key.encode())
        payload = msg.payload
        if payload.startswith(PROTOCOL_33_HEADER[:3]):
            payload = payload[len(PROTOCOL_33_HEADER) :]
        try:
            raw = cipher.decrypt(payload, use_base64=False, decode_text=False)
            request = json.loads(raw)
        except Exception:
            return False

        if msg.cmd in (DP_QUERY, DP_QUERY_NEW):
            self._reply(cipher, msg, {"dps": charger.dps()})
        elif msg.cmd == CONTROL:
            charger.apply(request.get("dps", {}))
            self._reply(cipher, msg, None)
        elif msg.cmd == HEART_BEAT:
            self._reply(cipher, msg, None)
        return True

    def _reply(
        self, cipher: AESCipher, request: TuyaMessage, body: dict[str, Any] | None
    ) -> None:
        payload = struct.pack(">I", 0)
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode()
            payload += cipher.encrypt(data, use_base64=False)
        reply = TuyaMessage(
            request.seqno, request.cmd, 0, payload, 0, True, PREFIX_55AA_VALUE, None
        )
        self.request.sendall(pack_message(reply))


CHARGER = Charger()


class _ControlHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict[str, Any]) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"ok": True})
        elif self.path == "/state":
            with CHARGER.lock:
                self._send(
                    200,
                    {
                        "dps": CHARGER.dps(),
                        "writes": CHARGER.writes,
                        "local_key": CHARGER.local_key,
                        "listening": CHARGER.server is not None,
                        "connections": len(CHARGER.connections),
                    },
                )
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path == "/reset":
            CHARGER.reset()
            CHARGER.start()
        elif self.path == "/stop":
            CHARGER.stop()
        elif self.path == "/start":
            CHARGER.start()
        elif self.path == "/local_key":
            CHARGER.local_key = str(self._json()["local_key"])
            CHARGER.drop_connections()
        else:
            self._send(404, {"error": "not found"})
            return
        self._send(200, {"ok": True})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    """Run the fake charger until interrupted."""
    CHARGER.start()
    ThreadingHTTPServer(("0.0.0.0", CONTROL_PORT), _ControlHandler).serve_forever()


if __name__ == "__main__":
    main()
