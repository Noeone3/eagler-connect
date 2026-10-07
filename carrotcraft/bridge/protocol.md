# Headless client ↔ Python bridge

`client/headless_client.js` keeps its own WebSocket to the Minecraft server
(`wss://eagler.carrot-craft.org`) and *additionally* connects to
`ws://127.0.0.1:8765` for AI control. The second socket carries JSON; it never
touches the Minecraft protocol.

## Python → client

```json
{"type":"observe"}
{"type":"config","server_url":"wss://eagler.carrot-craft.org","client_version":"1.8.8","tick":0.4}
{"type":"action","action":"move","forward":true,"back":false,"left":false,"right":false,"jump":false,"sprint":false}
{"type":"action","action":"look","yaw":90,"pitch":-10}
{"type":"action","action":"mine","x":123,"y":63,"z":-40}
{"type":"action","action":"place","x":123,"y":64,"z":-40,"face":"top"}
{"type":"action","action":"attack"}
{"type":"action","action":"use"}
{"type":"action","action":"chat","message":"/register password password"}
{"type":"action","action":"respawn"}
{"type":"action","action":"craft","recipe":"iron_pickaxe"}
{"type":"goal_complete","goal":"get full netherite"}
```

`config` arrives once when the AI connects: if the client is not in a game yet
it joins `server_url`. `observe` asks for exactly one `state`.

## Client → Python

```json
{"type":"hello","version":3,"client":"eagler-headless","server_url":"wss://eagler.carrot-craft.org"}
{"type":"state","player":{},"inventory":{},"blocks":[],"entities":[],"chat":[]}
{"type":"result","ok":true,"action":"mine"}
{"type":"result","ok":false,"action":"craft","error":"crafting is not implemented by the headless client"}
```

`state.player` carries `x, y, z, yaw, pitch, health, food, dimension,
game_mode, on_ground, entity_id, status, server`; `blocks` is the nearest 96
blocks (ores, logs, and everything else nearby) as `{type, x, y, z}`;
`inventory` is item name → count.

Every action is answered with a `result`, so the Python side always learns
whether the client could act.

## Crafting

`craft` is answered `ok:false` on purpose: real crafting needs window
transactions (open window, place ingredients, click the output slot), which the
headless client does not implement yet. Everything else it claims, it does.