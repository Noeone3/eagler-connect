"""Small RFC6455 WebSocket server on the Python standard library.

The headless bridge only needs text frames in both directions, so this keeps
the transport dependency-free (no `websockets` package to install).
"""

import asyncio
import base64
import hashlib
import struct

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_FRAME = 8 * 1024 * 1024


class WebSocketClosed(Exception):
    """Raised when a frame cannot be read safely."""


class WebSocket:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.closed = False

    # --------------------------------------------------
    # HANDSHAKE
    # --------------------------------------------------

    @classmethod
    async def accept(cls, reader, writer):
        try:
            raw = await reader.readuntil(b"\r\n\r\n")
        except (asyncio.IncompleteReadError, ConnectionResetError):
            writer.close()
            return None

        headers = {}
        for line in raw.decode("latin-1").split("\r\n")[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()

        key = headers.get("sec-websocket-key")
        if not key:
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            writer.close()
            return None

        accept = base64.b64encode(
            hashlib.sha1((key + GUID).encode("ascii")).digest()
        ).decode("ascii")

        writer.write(
            (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Accept: " + accept + "\r\n"
                "\r\n"
            ).encode("latin-1")
        )
        await writer.drain()
        return cls(reader, writer)

    # --------------------------------------------------
    # FRAMES
    # --------------------------------------------------

    async def _read_frame(self):
        head = await self.reader.readexactly(2)
        opcode = head[0] & 0x0F
        fin = bool(head[0] & 0x80)
        masked = bool(head[1] & 0x80)
        length = head[1] & 0x7F

        if length == 126:
            length = struct.unpack(">H", await self.reader.readexactly(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", await self.reader.readexactly(8))[0]

        if length > MAX_FRAME:
            raise WebSocketClosed("frame too large")

        mask = await self.reader.readexactly(4) if masked else b""
        payload = await self.reader.readexactly(length) if length else b""

        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

        return opcode, fin, payload

    def _write_frame(self, opcode, payload):
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.append(126)
            header += struct.pack(">H", length)
        else:
            header.append(127)
            header += struct.pack(">Q", length)
        self.writer.write(bytes(header) + payload)

    async def _send_frame(self, opcode, payload):
        if self.closed:
            return
        self._write_frame(opcode, payload)
        await self.writer.drain()

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    async def send_text(self, text):
        await self._send_frame(0x1, text.encode("utf-8"))

    async def receive_text(self):
        """Return the next text message, or None once the peer closes."""
        buffer = b""
        while True:
            try:
                opcode, fin, payload = await self._read_frame()
            except (asyncio.IncompleteReadError, ConnectionResetError, WebSocketClosed):
                self.closed = True
                return None

            if opcode == 0x8:
                await self.close()
                return None
            if opcode == 0x9:
                await self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue

            buffer = buffer + payload if opcode == 0x0 else payload
            if fin:
                return buffer.decode("utf-8", "replace")

    async def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self._write_frame(0x8, b"\x03\xe8")
            await self.writer.drain()
        except (ConnectionResetError, OSError):
            pass
        self.writer.close()


async def start_server(handler, host, port):
    """Start an asyncio server whose handler receives a WebSocket."""

    async def on_client(reader, writer):
        socket = await WebSocket.accept(reader, writer)
        if socket is None:
            return
        try:
            await handler(socket)
        finally:
            await socket.close()

    return await asyncio.start_server(on_client, host, port)