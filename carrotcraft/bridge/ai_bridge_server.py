"""Headless AI bridge.

The headless client (client/headless_client.js) dials in to
ws://127.0.0.1:8765. From there this server drives the loop:

    observe -> update the planner's world snapshot -> pick the next objective
    -> send the client the actions that objective needs

Message shapes are documented in bridge/protocol.md.
"""

import asyncio
import json

from ai.executor import ActionExecutor
from bridge.ws_server import start_server

STATE_TIMEOUT = 5.0


class BridgeServer:
    def __init__(self, ai, host="127.0.0.1", port=8765, tick=0.4, executor=None):
        self.ai = ai
        self.host = host
        self.port = port
        self.tick = tick
        self.executor = executor or ActionExecutor(tick_seconds=tick)
        self.states = asyncio.Queue()
        self.goal_reported = False

    async def _send(self, socket, message):
        await socket.send_text(json.dumps(message))

    async def _read_messages(self, socket):
        while True:
            raw = await socket.receive_text()
            if raw is None:
                return
            try:
                message = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(message, dict):
                continue

            kind = message.get("type")
            if kind == "state":
                await self.states.put(message)
            elif kind == "hello":
                print("bridge: client connected:", message.get("client"), "v", message.get("version"))
            elif kind == "result":
                if not message.get("ok"):
                    print("bridge: client reported:", message.get("action"), message.get("error"))

    async def _control(self, socket):
        await self._send(socket, {
            "type": "config",
            "server_url": self.ai.server_url,
            "client_version": self.ai.client_version,
            "tick": self.tick,
        })

        while True:
            await self._send(socket, {"type": "observe"})
            try:
                state = await asyncio.wait_for(self.states.get(), STATE_TIMEOUT)
            except asyncio.TimeoutError:
                print("bridge: no state from the client - is the adapter loaded?")
                continue

            self.ai.update_from_state(state)
            objective = self.ai.select_next_objective()

            if objective is None:
                if not self.goal_reported:
                    print("bridge: goal complete:", self.ai.goal)
                    self.goal_reported = True
                await self._send(socket, {"type": "goal_complete", "goal": self.ai.goal})
                await asyncio.sleep(2.0)
                continue

            print(f"bridge: {objective.text} -> {objective.action}")
            for command in self.executor.commands(objective, self.ai.world):
                await self._send(socket, {"type": "action", **command})
            await asyncio.sleep(self.tick)

    async def _handle_client(self, socket):
        print("bridge: headless client attached, target", self.ai.server_url)
        reader = asyncio.create_task(self._read_messages(socket))
        try:
            await self._control(socket)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print("bridge: client connection ended:", exc)
        finally:
            reader.cancel()

    async def serve(self):
        server = await start_server(self._handle_client, self.host, self.port)
        print(f"bridge: listening on ws://{self.host}:{self.port}")
        print(f"bridge: driving {self.ai.goal!r} on {self.ai.server_url}")
        async with server:
            await server.serve_forever()


def run_bridge(ai, host="127.0.0.1", port=8765, tick=0.4):
    server = BridgeServer(ai, host, port, tick)
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("\nbridge: stopped")