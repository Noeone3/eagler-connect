# CarrotCraft Headless AI

A headless Minecraft 1.8 client that joins `wss://eagler.carrot-craft.org` by
itself, the Python AI that drives it, and the YouTube research that feeds it
strategies.

The client speaks the EaglercraftX 1.8 handshake and the Minecraft 1.8 packets
over a plain WebSocket, so **no client build has to be patched** and nothing
from the browser is required.

## Requirements

- Python 3.10+ (the bridge and planner use the standard library only)
- Node 18+ (the headless client; it uses the built-in `WebSocket`)
- `pytubefix` only if you use the YouTube research: `python -m pip install --user pytubefix`

## 1. Test the planner (no connection)

```bash
python main.py --goal "get full netherite" --dry-run
```

## 2. Start the AI (terminal 1)

```bash
python main.py --goal "get full netherite" --serve
```

It prints the objective plan and listens on `ws://127.0.0.1:8765`.

## 3. Start the client (terminal 2)

```bash
node client/headless_client.js --username AI_Bot
```

The client joins the server, then the bridge drives it: `observe` → state →
`action` → `result`.

| Option | Meaning |
| --- | --- |
| `--username <name>` | player name (default `AI_Bot`) |
| `--server <url>` | another server socket (default `wss://eagler.carrot-craft.org`) |
| `--bridge <url>` | another AI socket (default `ws://127.0.0.1:8765`) |
| `--no-bridge` | just join the server, no AI |
| `--register <password>` | send `/register <password> <password>` once in game |
| `--login <password>` | send `/login <password>` once in game |
| `--quiet` | fewer logs |

You can also move servers from the Python side:
`python main.py --serve --server-url wss://eagler.carrot-craft.org`

## Server accounts

`eagler.carrot-craft.org` runs a login plugin: a name nobody has registered
lands in limbo (spectator, empty world) and the server answers `/register`.
Use `--register <password>` the first time and `--login <password>` afterwards.
The password is only ever sent to the game server.

## Browser

Open `client/index.html` and press **Connect** to run the same client in a
browser. Chunk parsing needs Node's `zlib`, so in the browser the client only
sees blocks it is told about through block updates.

## What the client can do

`move`, `look`, `mine`, `place`, `attack`, `use`, `chat`, `respawn`, plus
always: join, keep-alives, position, chat, inventory, entities and blocks
(chunks, single and multi block changes).

`craft` is **not** implemented yet - it needs window/transaction handling, and
the client answers `{"result": false, "error": "crafting is not implemented..."}`
so the planner can see it plainly.

## Tests

```bash
python -m unittest discover -s tests -t . -v
node --check client/headless_client.js
```

## YouTube research

```bash
$env:YOUTUBE_API_KEY="YOUR_KEY"           # PowerShell
python main.py --goal "get full netherite" --research-objectives --objective-limit 2 --video-limit 2
python main.py --goal "get full netherite" --research-objectives --study-videos --objective-limit 2 --video-limit 2
```

Searches are per objective and the strategies/studies are stored with their
`objective_id`. Set `--study-videos` to pull captions into the knowledge base.

## Note on versions

The planner plans against `--server-version` (default `1.21.1`) while the client
speaks 1.8.8. Netherite is post-1.16, so `get full netherite` only makes sense
if the server really runs something a 1.8.8 client can join. With
`--server-version 1.8.8` the planner says netherite is unavailable instead of
inventing steps for it.

## Layout

```
main.py                     CLI: plan, research, serve the bridge
ai/                         planner, executor, world model, optimizer
bridge/ai_bridge_server.py  the ws://127.0.0.1:8765 control loop
bridge/ws_server.py         dependency-free WebSocket server
bridge/protocol.md          the JSON protocol between Python and the client
client/headless_client.js   the client: Eaglercraft handshake + game packets
client/index.html           browser host for the same client
research/, training/        YouTube research and knowledge base
tests/                      bridge tests
``