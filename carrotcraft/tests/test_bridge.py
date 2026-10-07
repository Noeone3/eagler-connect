"""End-to-end tests for the headless bridge.

Run from the project root:

    python -m unittest discover -s tests -t . -v

They start the AI bridge on a spare local port and talk to it with a real
WebSocket client, so a failure here means the client would fail too.
"""

import asyncio
import base64
import json
import os
import struct
import unittest

from ai.agent import DEFAULT_SERVER_URL, MinecraftAI
from ai.executor import ActionExecutor
from ai.objective_planner import Objective, ObjectivePlanner, ObjectivePlanningError, WorldSnapshot
from bridge.ai_bridge_server import BridgeServer
from bridge.ws_server import start_server

PORT = 8799


def build_frame(text):
    payload = text.encode("utf-8")
    mask = os.urandom(4)
    header = bytearray([0x81])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", length)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", length)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return bytes(header) + mask + masked


async def read_message(reader):
    head = await reader.readexactly(2)
    length = head[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", await reader.readexactly(8))[0]
    payload = await reader.readexactly(length) if length else b""
    return json.loads(payload.decode("utf-8"))


class PlannerTest(unittest.TestCase):
    def test_ai_starts_and_plans(self):
        ai = MinecraftAI()
        self.assertEqual(ai.server_url, DEFAULT_SERVER_URL)
        objectives = ai.prepare("get full netherite")
        self.assertEqual(len(objectives), 21)
        self.assertEqual(objectives[0].id, "wood")

    def test_old_keyword_still_rejected_for_1_8_8(self):
        with self.assertRaises(ObjectivePlanningError):
            ObjectivePlanner(mc_version="1.8.8").plan("get full netherite")


class ExecutorTest(unittest.TestCase):
    def test_mine_target_comes_from_reported_blocks(self):
        world = WorldSnapshot(
            player={"x": 0, "y": 64, "z": 0},
            blocks=[{"type": "stone", "x": 1, "y": 63, "z": 0},
                    {"type": "iron_ore", "x": 5, "y": 60, "z": 2}],
        )
        objective = Objective("iron", "Mine iron", "mine", params={"block": "iron_ore", "amount": 31})
        commands = ActionExecutor().commands(objective, world)
        self.assertEqual(commands, [{"action": "mine", "x": 5.0, "y": 60.0, "z": 2.0}])

    def test_scan_when_block_not_reported(self):
        world = WorldSnapshot(player={"yaw": 0})
        objective = Objective("gold", "Mine gold", "mine_nether", params={"block": "gold_ore"})
        commands = ActionExecutor().commands(objective, world)
        self.assertEqual([c["action"] for c in commands], ["look", "move"])


class BridgeTest(unittest.TestCase):
    def test_bridge_drives_the_client(self):
        asyncio.run(asyncio.wait_for(self._scenario(), 40))

    async def _scenario(self):
        ai = MinecraftAI()
        ai.prepare("get full netherite")
        bridge = BridgeServer(ai, "127.0.0.1", PORT, tick=0.05)
        server = await start_server(bridge._handle_client, "127.0.0.1", PORT)

        reader, writer = await asyncio.open_connection("127.0.0.1", PORT)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        writer.write((
            "GET / HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{PORT}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("ascii"))
        await writer.drain()

        handshake = await reader.readuntil(b"\r\n\r\n")
        self.assertIn(b"101 Switching Protocols", handshake)

        writer.write(build_frame(json.dumps({
            "type": "hello", "version": 2, "client": "eagler-headless",
            "server_url": DEFAULT_SERVER_URL,
        })))
        await writer.drain()

        config = await asyncio.wait_for(read_message(reader), 10)
        self.assertEqual(config["type"], "config")
        self.assertEqual(config["server_url"], DEFAULT_SERVER_URL)

        ask = await asyncio.wait_for(read_message(reader), 10)
        self.assertEqual(ask, {"type": "observe"})

        # first objective is "Get wood": the reported oak_log must be mined
        writer.write(build_frame(json.dumps({
            "type": "state",
            "player": {"x": 0, "y": 64, "z": 0, "yaw": 0, "pitch": 0},
            "inventory": {},
            "blocks": [{"type": "oak_log", "x": 2, "y": 64, "z": 0}],
            "entities": [],
        })))
        await writer.drain()

        mine = None
        for _ in range(4):
            message = await asyncio.wait_for(read_message(reader), 10)
            if message.get("action") == "mine":
                mine = message
                break
        self.assertEqual((mine or {}).get("x"), 2.0)
        self.assertEqual((mine or {}).get("z"), 0.0)

        # wood in the inventory -> the planner moves on to crafting planks
        self.assertEqual((await asyncio.wait_for(read_message(reader), 10)), {"type": "observe"})
        writer.write(build_frame(json.dumps({
            "type": "state", "player": {"x": 0, "y": 64, "z": 0},
            "inventory": {"oak_log": 4}, "blocks": [], "entities": [],
        })))
        await writer.drain()

        seen = []
        craft = None
        for _ in range(6):
            message = await asyncio.wait_for(read_message(reader), 10)
            seen.append(message)
            if message.get("action") == "craft":
                craft = message
                break
        self.assertEqual((craft or {}).get("recipe"), "oak_planks", f"messages after state 2: {seen}")

        writer.close()
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    unittest.main()