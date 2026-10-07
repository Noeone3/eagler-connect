/* CarrotCraft headless client - independent, no dependencies, no client patch.
 *
 * It speaks the EaglercraftX 1.8 handshake and vanilla Minecraft 1.8 packets
 * over a plain WebSocket, so it joins wss://eagler.carrot-craft.org by itself:
 *
 *     node client/headless_client.js --username AI_Bot
 *
 * It also dials the Python AI on ws://127.0.0.1:8765 and answers its
 * observe/action messages (see bridge/protocol.md).
 *
 * Runs on Node 18+ (global WebSocket) and in a browser. Chunk parsing needs
 * zlib, so it is Node-only; in a browser blocks are tracked from block
 * updates instead.
 */
(function (global) {
  "use strict";

  const VERSION = 3;
  const DEFAULT_SERVER = "wss://eagler.carrot-craft.org";
  const DEFAULT_BRIDGE = "ws://127.0.0.1:8765";
  const MC_PROTOCOL = 47;          // Minecraft 1.8.8
  const EAGLER_PROTOCOLS = [5, 4]; // handshake versions we can speak

  /* ------------------------------------------------------------------ ids */

  const LOG_META = ["oak_log", "spruce_log", "birch_log", "jungle_log"];
  const PLANK_META = ["oak_planks", "spruce_planks", "birch_planks", "jungle_planks", "acacia_planks", "dark_oak_planks"];

  const NAMES = {
    1: "stone", 2: "grass", 3: "dirt", 4: "cobblestone", 5: "oak_planks", 7: "bedrock",
    8: "water", 9: "water", 10: "lava", 11: "lava", 12: "sand", 13: "gravel",
    14: "gold_ore", 15: "iron_ore", 16: "coal_ore", 17: "oak_log", 18: "leaves",
    19: "sponge", 20: "glass", 21: "lapis_ore", 22: "lapis_block", 23: "dispenser",
    24: "sandstone", 25: "noteblock", 29: "piston", 31: "tallgrass", 33: "piston_head",
    35: "wool", 41: "gold_block", 42: "iron_block", 43: "double_stone_slab", 44: "stone_slab",
    45: "brick_block", 46: "tnt", 47: "bookshelf", 48: "mossy_cobblestone", 49: "obsidian",
    50: "torch", 52: "mob_spawner", 53: "oak_stairs", 54: "chest", 56: "diamond_ore",
    57: "diamond_block", 58: "crafting_table", 59: "wheat", 60: "farmland", 61: "furnace",
    62: "lit_furnace", 64: "wooden_door", 65: "ladder", 66: "rail", 67: "stone_stairs",
    73: "redstone_ore", 74: "lit_redstone_ore", 78: "snow_layer", 79: "ice", 80: "snow",
    81: "cactus", 82: "clay", 83: "reeds", 85: "oak_fence", 86: "pumpkin",
    87: "netherrack", 88: "soul_sand", 89: "glowstone", 90: "portal", 95: "stained_glass",
    98: "stonebrick", 101: "iron_bars", 102: "glass_pane", 103: "melon_block",
    110: "mycelium", 112: "nether_brick", 116: "enchanting_table", 120: "end_portal_frame",
    121: "end_stone", 129: "emerald_ore", 133: "emerald_block", 137: "command_block",
    145: "anvil", 152: "redstone_block", 153: "quartz_ore", 155: "quartz_block",
    159: "stained_hardened_clay", 161: "stained_glass_pane", 162: "dark_oak_log",
    168: "prismarine", 173: "coal_block", 174: "packed_ice", 179: "red_sandstone",
    // items
    256: "iron_shovel", 257: "iron_pickaxe", 258: "iron_axe", 259: "flint_and_steel",
    260: "apple", 261: "bow", 262: "arrow", 263: "coal", 264: "diamond", 265: "iron_ingot",
    266: "gold_ingot", 267: "iron_sword", 268: "wooden_sword", 269: "wooden_shovel",
    270: "wooden_pickaxe", 271: "wooden_axe", 272: "stone_sword", 273: "stone_shovel",
    274: "stone_pickaxe", 275: "stone_axe", 276: "diamond_sword", 277: "diamond_shovel",
    278: "diamond_pickaxe", 279: "diamond_axe", 280: "stick", 281: "bowl", 282: "mushroom_stew",
    283: "golden_sword", 284: "golden_shovel", 285: "golden_pickaxe", 286: "golden_axe",
    287: "string", 288: "feather", 289: "gunpowder", 290: "wooden_hoe", 291: "stone_hoe",
    292: "iron_hoe", 293: "diamond_hoe", 294: "golden_hoe", 296: "wheat_seeds",
    297: "bread", 298: "leather_helmet", 300: "leather_leggings", 301: "leather_boots",
    306: "iron_helmet", 307: "iron_chestplate", 308: "iron_leggings", 309: "iron_boots",
    310: "diamond_helmet", 311: "diamond_chestplate", 312: "diamond_leggings",
    313: "diamond_boots", 314: "golden_helmet", 315: "golden_chestplate",
    316: "golden_leggings", 317: "golden_boots", 319: "porkchop", 320: "cooked_porkchop",
    321: "painting", 322: "golden_apple", 325: "bucket", 326: "water_bucket",
    327: "lava_bucket", 331: "redstone", 332: "snowball", 334: "leather", 337: "clay_ball",
    338: "reeds", 340: "book", 344: "egg", 345: "compass", 347: "clock", 348: "glowstone_dust",
    349: "fish", 350: "cooked_fish", 352: "bone", 353: "sugar", 355: "bed", 357: "cookie",
    359: "shears", 360: "melon", 361: "pumpkin_seeds", 362: "melon_seeds", 363: "beef",
    364: "cooked_beef", 365: "chicken", 366: "cooked_chicken", 367: "rotten_flesh",
    368: "ender_pearl", 369: "blaze_rod", 370: "ghast_tear", 371: "gold_nugget",
    374: "glass_bottle", 377: "blaze_powder", 378: "magma_cream", 381: "ender_eye",
    388: "emerald", 390: "flower_pot", 391: "carrot", 392: "potato", 393: "baked_potato",
    400: "pumpkin_pie", 405: "netherbrick", 406: "quartz", 407: "tnt"
  };
  const INTERESTING = /ore|log|planks|ingot|diamond|emerald|coal|stick|crafting_table|furnace|chest|obsidian|torch|pickaxe|sword|axe|shovel|hoe|bucket|apple|bread|cobblestone|stone|dirt|sand|gravel|wool|glowstone|netherrack|soul_sand/;

  function nameOf(id, meta) {
    if (id === 0) return null;
    if (id === 17) return LOG_META[meta & 3] || "oak_log";
    if (id === 5) return PLANK_META[meta & 7] || "oak_planks";
    if (id === 162) return (meta & 1) ? "dark_oak_log" : "acacia_log";
    return NAMES[id] || null;
  }

  /* -------------------------------------------------------------- binary io */

  const utf8 = new TextDecoder("utf-8");
  let zlib = null;
  try { if (typeof require === "function") zlib = require("zlib"); } catch (e) { zlib = null; }

  class Reader {
    constructor(bytes, offset) {
      this.b = bytes;
      this.o = offset || 0;
      this.dv = new DataView(bytes.buffer, bytes.byteOffset || 0, bytes.byteLength);
    }
    u8() { return this.b[this.o++]; }
    i8() { const v = this.b[this.o++]; return v > 127 ? v - 256 : v; }
    u16() { const v = this.dv.getUint16(this.o); this.o += 2; return v; }
    i32() { const v = this.dv.getInt32(this.o); this.o += 4; return v; }
    f32() { const v = this.dv.getFloat32(this.o); this.o += 4; return v; }
    f64() { const v = this.dv.getFloat64(this.o); this.o += 8; return v; }
    vi() { let n = 0, s = 0, b; do { b = this.b[this.o++]; n |= (b & 0x7f) << s; s += 7; } while (b & 0x80); return n >>> 0; }
    str() { const n = this.vi(); const s = utf8.decode(this.b.subarray(this.o, this.o + n)); this.o += n; return s; }
    skip(n) { this.o += n; return this; }
    left() { return this.b.length - this.o; }
  }

  function packPos(x, y, z) {
    return (BigInt(x & 0x3ffffff) << 38n) | (BigInt(y & 0xfff) << 26n) | BigInt(z & 0x3ffffff);
  }
  function unpackPos(v) {
    let x = Number(v >> 38n), y = Number((v >> 26n) & 0xfffn), z = Number(v & 0x3ffffffn);
    if (x >= 0x2000000) x -= 0x4000000;
    if (y >= 0x800) y -= 0x1000;
    if (z >= 0x2000000) z -= 0x4000000;
    return { x: x, y: y, z: z };
  }

  class Writer {
    constructor() { this.a = []; }
    u8(v) { this.a.push(v & 0xff); return this; }
    bool(v) { return this.u8(v ? 1 : 0); }
    u16(v) { this.a.push((v >> 8) & 0xff, v & 0xff); return this; }
    i32(v) { this.a.push((v >> 24) & 0xff, (v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff); return this; }
    vi(v) { v = v >>> 0; for (;;) { if ((v & ~0x7f) === 0) { this.a.push(v); break; } this.a.push((v & 0x7f) | 0x80); v >>>= 7; } return this; }
    f32(v) { const d = new DataView(new ArrayBuffer(4)); d.setFloat32(0, v, false); for (let i = 0; i < 4; i++) this.a.push(d.getUint8(i)); return this; }
    f64(v) { const d = new DataView(new ArrayBuffer(8)); d.setFloat64(0, v, false); for (let i = 0; i < 8; i++) this.a.push(d.getUint8(i)); return this; }
    pos(x, y, z) { const v = packPos(x, y, z); for (let s = 56n; s >= 0n; s -= 8n) this.a.push(Number((v >> s) & 0xffn)); return this; }
    str(s) { const d = new TextEncoder().encode(String(s)); this.vi(d.length); for (let i = 0; i < d.length; i++) this.a.push(d[i]); return this; }
    bytes() { return new Uint8Array(this.a); }
  }

  const FACES = { down: 0, up: 1, north: 2, south: 3, west: 4, east: 5, top: 1, bottom: 0, side: 3 };
  const FACE_NORMAL = [[0, -1, 0], [0, 1, 0], [0, 0, -1], [0, 0, 1], [-1, 0, 0], [1, 0, 0]];

  /* ----------------------------------------------------------------- client */

  class HeadlessClient {
    constructor(opts) {
      opts = opts || {};
      this.serverUrl = opts.serverUrl || DEFAULT_SERVER;
      this.bridgeUrl = opts.bridgeUrl === null ? null : (opts.bridgeUrl || DEFAULT_BRIDGE);
      this.username = opts.username || "AI_Bot";
      this.brand = opts.brand || "EaglercraftX";
      this.clientVersion = opts.clientVersion || "1.8.8";
      this.registerPassword = opts.registerPassword || null;
      this.loginPassword = opts.loginPassword || null;
      this.verbose = opts.verbose !== false;
      this.autoRespawn = opts.autoRespawn !== false;

      this.status = "idle";
      this.player = { x: 0, y: 64, z: 0, yaw: 0, pitch: 0, health: 20, food: 20, dimension: 0, gameMode: 0, onGround: true, entityId: null, flying: false };
      this.inventory = {};
      this.slots = {};
      this.chat = [];
      this.entities = new Map();
      this.blocks = new Map();
      this.stats = { keepAlives: 0, chat: 0, blockChanges: 0, chunks: 0, actions: 0, errors: 0 };
      this.moveInput = { forward: false, back: false, left: false, right: false, jump: false, sprint: false };
      this.vy = 0;
      this.heldSlot = 0;
      this.authMethod = 0;
      this.awaitingAuth = false;
      this.game = null;
      this.aiSocket = null;
      this.lastError = null;
      this._moveTimer = null;
      this._lastStep = 0;
    }

    log() {
      if (!this.verbose) return;
      const parts = Array.prototype.slice.call(arguments);
      console.log("[headless] " + parts.join(" "));
    }

    fail(message) {
      this.status = "error";
      this.lastError = message;
      if (typeof console !== "undefined") console.error("[headless] " + message);
    }

    /* --- game socket ---------------------------------------------------- */

    connect() {
      const WS = global.WebSocket;
      if (!WS) { this.fail("no WebSocket implementation available"); return this; }
      this.status = "connecting";
      let socket;
      try { socket = new WS(this.serverUrl); } catch (err) { this.fail("cannot open " + this.serverUrl + ": " + err.message); return this; }
      this.game = socket;
      socket.binaryType = "arraybuffer";
      socket.onopen = () => {
        this.status = "handshake";
        socket.send(this._versionPacket());
        this.log("joined " + this.serverUrl + " as " + this.username);
      };
      socket.onmessage = (event) => {
        const bytes = toBytes(event.data);
        if (!bytes) return;
        try { this._gameFrame(bytes); } catch (err) { this.stats.errors++; this.log("packet error:", err.message); }
      };
      socket.onclose = (event) => {
        this.status = "closed";
        this._stopMoving();
        this.log("disconnected from " + this.serverUrl + (event && event.code ? " (" + event.code + ")" : ""));
      };
      socket.onerror = () => { this.stats.errors++; this.lastError = "socket error"; };
      return this;
    }

    _versionPacket() {
      const w = new Writer();
      w.u8(0x01).u8(0x02);                              // EaglercraftX 1.8, handshake v2+
      w.u16(EAGLER_PROTOCOLS.length);
      EAGLER_PROTOCOLS.forEach((p) => w.u16(p));
      w.u16(1).u16(MC_PROTOCOL);
      w.str(this.brand).str(this.clientVersion);
      w.bool(false);                                    // no account session
      w.str(this.username);                             // auth username == player name
      return w.bytes();
    }

    _gameFrame(bytes) {
      const id = bytes[0];
      if (this.status === "handshake") return this._handshakePacket(id, bytes);
      switch (id) {
        case 0x00: return this._keepAlive(bytes);
        case 0x01: return this._joinGame(bytes);
        case 0x02: return this._chat(bytes);
        case 0x06: return this._health(bytes);
        case 0x07: return this._respawn(bytes);
        case 0x08: return this._positionAndLook(bytes);
        case 0x09: this.heldSlot = bytes[1]; return;
        case 0x0c: return this._spawn(bytes, 1);
        case 0x0e: return this._spawn(bytes, 2);
        case 0x0f: return this._spawn(bytes, 3);
        case 0x13: return this._destroyEntities(bytes);
        case 0x15: case 0x16: case 0x17: return this._entityMove(id, bytes);
        case 0x18: return this._entityTeleport(bytes);
        case 0x21: return this._chunkData(bytes);
        case 0x22: return this._multiBlockChange(bytes);
        case 0x23: return this._blockChange(bytes);
        case 0x2f: return this._setSlot(bytes);
        case 0x30: return this._windowItems(bytes);
        case 0x39: return this._abilities(bytes);
        case 0x40: return this._disconnect(bytes);
        case 0x46: this.compression = true; this.log("server asked for compressed packets"); return;
        default: return;
      }
    }

    _handshakePacket(id, bytes) {
      const r = new Reader(bytes);
      switch (id) {
        case 0x02: {                                      // server version
          r.skip(1);
          const eaglerProtocol = r.u16(), mcProtocol = r.u16();
          const serverBrand = r.str(), serverVersion = r.str();
          this.authMethod = r.u8();
          this.log("server " + serverBrand + " " + serverVersion + " (handshake v" + eaglerProtocol + ", mc " + mcProtocol + ")");
          return void this._send(this._loginPacket());
        }
        case 0x03: {                                      // version mismatch
          r.skip(1);
          const count = r.u16();
          for (let i = 0; i < count; i++) r.u16();
          const mcCount = r.u16();
          for (let i = 0; i < mcCount; i++) r.u16();
          return this.fail("server rejected this client version (" + r.str() + ")");
        }
        case 0x05: {                                      // login allowed
          r.skip(1);
          this.player.username = r.str();
          this.player.uuid = hex(r.b.subarray(r.o, r.o + 16));
          r.skip(16);
          return void this._send(this._finishLoginPacket());
        }
        case 0x06: return this.fail("login denied by the server");
        case 0x09:                                        // handshake complete
          this.status = "playing";
          this.log("logged in");
          this._startMoving();
          return;
        case 0x0a: r.skip(1); return this.fail("server redirected the connection to " + r.str());
        case 0xff: r.skip(1); const code = r.u8(); return this.fail("server error " + code + ": " + r.str());
        default: return;
      }
    }

    _loginPacket() {
      const w = new Writer();
      w.u8(0x04).str(this.player.username || this.username).str(this.serverUrl);
      w.vi(0);                                          // no auth password
      w.bool(false);                                    // no cookie
      w.u8(0);                                          // empty cookie
      w.vi(0);                                          // no capabilities
      w.u8(0);                                          // no extended capabilities
      return w.bytes();
    }

    _finishLoginPacket() { return new Uint8Array([0x08]); }

    /* --- play packets --------------------------------------------------- */

    _keepAlive(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const id = r.vi();
      this.stats.keepAlives++;
      this._send(new Writer().u8(0x00).vi(id).bytes());
    }

    _joinGame(bytes) {
      const r = new Reader(bytes); r.skip(1);
      this.player.entityId = r.i32();
      this.player.gameMode = r.u8();
      this.player.dimension = r.i8();
      this.player.difficulty = r.u8();
      this.player.maxPlayers = r.u8();
      this.levelType = r.str();
      this.player.reducedDebug = r.u8() !== 0;
      this.status = "playing";
      this._send(this._clientSettingsPacket());
      this._send(this._brandPacket());
      this._startMoving();
      this.log("in game: entity " + this.player.entityId + ", mode " + this.player.gameMode + ", dimension " + this.player.dimension);
      if (this.registerPassword) setTimeout(() => this.say("/register " + this.registerPassword + " " + this.registerPassword), 1500);
      else if (this.loginPassword) setTimeout(() => this.say("/login " + this.loginPassword), 1500);
    }

    _clientSettingsPacket() {
      return new Writer().u8(0x15).str("en_US").u8(8).u8(0).bool(true).u8(0x7f).bytes();
    }

    _brandPacket() {
      return new Writer().u8(0x17).str("MC|Brand").str("CarrotCraft-Headless").bytes();
    }

    _chat(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const raw = r.str();
      const position = r.u8();
      let text = raw;
      try { text = flattenChat(JSON.parse(raw)); } catch (err) { /* keep raw */ }
      this.chat.push(text);
      if (this.chat.length > 40) this.chat.shift();
      this.stats.chat++;
      this.log("chat:", text);
      if (position === 2 && /register|login/i.test(text)) this.awaitingAuth = true;
    }

    _health(bytes) {
      const r = new Reader(bytes); r.skip(1);
      this.player.health = r.f32();
      this.player.food = r.vi();
      this.player.saturation = r.f32();
      this.player.dead = this.player.health <= 0;
      if (this.player.dead && this.autoRespawn) setTimeout(() => this._send(new Writer().u8(0x16).vi(0).bytes()), 900);
    }

    _respawn(bytes) {
      const r = new Reader(bytes); r.skip(1);
      this.player.dimension = r.i32();
      this.player.difficulty = r.u8();
      this.player.gameMode = r.u8();
      this.levelType = r.str();
      this.blocks.clear();
      this.entities.clear();
      this.vy = 0;
      this.log("respawned in dimension " + this.player.dimension);
    }

    _positionAndLook(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const x = r.f64(), y = r.f64(), z = r.f64(), yaw = r.f32(), pitch = r.f32(), flags = r.u8();
      const p = this.player;
      p.x = (flags & 0x01) ? p.x + x : x;
      p.y = (flags & 0x02) ? p.y + y : y;
      p.z = (flags & 0x04) ? p.z + z : z;
      p.yaw = (flags & 0x08) ? p.yaw + yaw : yaw;
      p.pitch = (flags & 0x10) ? p.pitch + pitch : pitch;
      p.onGround = true;
      this.vy = 0;
      this._sendPosition();
    }

    _spawn(bytes, kind) {
      const r = new Reader(bytes); r.skip(1);
      const id = r.vi();
      let type = "entity";
      if (kind === 1) { type = "player"; r.skip(16); r.skip(2); }
      if (kind === 2) type = "object:" + r.u8();
      if (kind === 3) type = "mob:" + r.u8();
      const x = r.i32() / 32, y = r.i32() / 32, z = r.i32() / 32;
      this.entities.set(id, { id: id, type: type, x: x, y: y, z: z });
    }

    _destroyEntities(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const count = r.vi();
      for (let i = 0; i < count; i++) this.entities.delete(r.vi());
    }

    _entityMove(id, bytes) {
      const r = new Reader(bytes); r.skip(1);
      const entity = this.entities.get(r.vi());
      if (!entity) return;
      if (id === 0x15 || id === 0x17) { entity.x += r.i8() / 32; entity.y += r.i8() / 32; entity.z += r.i8() / 32; }
      if (id === 0x16 || id === 0x17) { entity.yaw = r.u8(); entity.pitch = r.u8(); }
    }

    _entityTeleport(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const entity = this.entities.get(r.vi());
      if (!entity) return;
      entity.x = r.i32() / 32; entity.y = r.i32() / 32; entity.z = r.i32() / 32;
    }

    _chunkData(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const cx = r.i32(), cz = r.i32();
      r.u8();                                           // groundUp
      const mask = r.u16();
      const size = r.vi();
      const raw = bytes.subarray(r.o, r.o + size);
      if (!zlib) return;                                // browser: block updates only
      let data;
      try { data = new Uint8Array(zlib.inflateSync(Buffer.from(raw))); } catch (err) { return; }
      const cr = new Reader(data);
      const skyLight = this.player.dimension !== -1;
      for (let section = 0; section < 16; section++) {
        if (!(mask & (1 << section))) continue;
        for (let i = 0; i < 4096; i++) {
          const value = cr.b[cr.o] | (cr.b[cr.o + 1] << 8); cr.o += 2;
          const blockId = value >> 4, meta = value & 0x0f;
          if (!blockId) continue;
          const name = nameOf(blockId, meta);
          if (!name) continue;
          const y = section * 16 + (i >> 8);
          const z = cz * 16 + ((i >> 4) & 15);
          const x = cx * 16 + (i & 15);
          this.blocks.set(x + "," + y + "," + z, name);
        }
        cr.skip(2048);                                  // block light
        if (skyLight) cr.skip(2048);                    // sky light
      }
      this.stats.chunks++;
      if (this.stats.chunks % 20 === 0) this.log("chunks parsed:", this.stats.chunks, "blocks:", this.blocks.size);
    }

    _multiBlockChange(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const cx = r.i32(), cz = r.i32();
      const count = r.vi();
      for (let i = 0; i < count; i++) {
        const value = r.u16();
        const state = r.vi();
        const x = cx * 16 + (value >> 12);
        const z = cz * 16 + ((value >> 8) & 15);
        const y = value & 0xff;
        this._applyBlock(x, y, z, state);
      }
    }

    _blockChange(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const pos = unpackPos(r.dv.getBigInt64(r.o)); r.o += 8;
      this._applyBlock(pos.x, pos.y, pos.z, r.vi());
    }

    _applyBlock(x, y, z, state) {
      const name = nameOf(state >> 4, state & 0x0f);
      const key = x + "," + y + "," + z;
      if (name) this.blocks.set(key, name); else this.blocks.delete(key);
      this.stats.blockChanges++;
    }

    _readSlot(r) {
      const id = r.u16();
      if (id === 0xffff || id === -1) return null;
      const count = r.u8();
      const damage = r.u16();
      if (r.u8() !== 0) skipNbt(r);
      return { id: id, count: count, damage: damage, name: nameOf(id, damage) || ("item_" + id) };
    }

    _setSlot(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const windowId = r.u8();
      const slot = r.u16();
      const item = this._readSlot(r);
      if (windowId !== 0) return;
      this.slots[slot] = item;
      this._recount();
    }

    _windowItems(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const windowId = r.u8();
      const count = r.u16();
      for (let i = 0; i < count; i++) this.slots[i] = this._readSlot(r);
      if (windowId !== 0) return;
      this._recount();
    }

    _recount() {
      const counts = {};
      Object.keys(this.slots).forEach((slot) => {
        const item = this.slots[slot];
        if (item) counts[item.name] = (counts[item.name] || 0) + item.count;
      });
      this.inventory = counts;
    }

    _abilities(bytes) {
      const r = new Reader(bytes); r.skip(1);
      const flags = r.u8();
      this.player.flying = !!(flags & 0x02);
      this.player.invulnerable = !!(flags & 0x01);
    }

    _disconnect(bytes) {
      const r = new Reader(bytes); r.skip(1);
      let text = r.str();
      try { text = flattenChat(JSON.parse(text)); } catch (err) { /* raw */ }
      this.status = "kicked";
      this.lastError = text;
      this.log("kicked:", text);
    }

    /* --- outgoing ------------------------------------------------------- */

    _send(payload) {
      const socket = this.game;
      if (!socket || socket.readyState !== 1) return false;
      try { socket.send(payload); return true; } catch (err) { this.stats.errors++; return false; }
    }

    say(message) {
      const ok = this._send(new Writer().u8(0x01).str(message).bytes());
      this.log("say:", message);
      return ok;
    }

    _sendLook() {
      const p = this.player;
      return this._send(new Writer().u8(0x05).f32(p.yaw).f32(p.pitch).bool(true).bytes());
    }

    _sendPosition() {
      const p = this.player;
      return this._send(new Writer().u8(0x06).f64(p.x).f64(p.y).f64(p.z).f32(p.yaw).f32(p.pitch).bool(p.onGround).bytes());
    }

    _startMoving() {
      if (this._moveTimer || typeof setInterval !== "function") return;
      this._lastStep = Date.now();
      this._moveTimer = setInterval(() => this._step(), 50);
      if (this._moveTimer && typeof this._moveTimer.unref === "function") this._moveTimer.unref();
    }

    _stopMoving() {
      if (this._moveTimer) { clearInterval(this._moveTimer); this._moveTimer = null; }
    }

    _step() {
      const now = Date.now();
      const dt = Math.min((now - this._lastStep) / 1000, 0.5);
      this._lastStep = now;
      const p = this.player;
      const input = this.moveInput;
      const forward = (input.forward ? 1 : 0) - (input.back ? 1 : 0);
      const strafe = (input.right ? 1 : 0) - (input.left ? 1 : 0);
      let moved = false;

      if (forward || strafe) {
        const rad = Math.PI * p.yaw / 180;
        const dx = -Math.sin(rad) * forward - Math.cos(rad) * strafe;
        const dz = Math.cos(rad) * forward - Math.sin(rad) * strafe;
        const len = Math.hypot(dx, dz) || 1;
        const speed = (input.sprint ? 5.6 : 4.32) * dt;
        p.x += (dx / len) * speed;
        p.z += (dz / len) * speed;
        moved = true;
      }

      if (input.jump && p.onGround) { this.vy = 0.42; p.onGround = false; }
      if (!p.onGround || this.vy !== 0) {
        this.vy = (this.vy - 0.08) * 0.98;
        p.y += this.vy;
        const ground = this.groundY(Math.floor(p.x), Math.floor(p.z));
        if (ground !== null && p.y <= ground + 1) { p.y = ground + 1; this.vy = 0; p.onGround = true; }
        moved = true;
      }

      if (moved) this._sendPosition();
    }

    groundY(bx, bz) {
      const base = Math.floor(this.player.y);
      for (let y = base + 2; y >= base - 6; y--) {
        const name = this.blocks.get(bx + "," + y + "," + bz);
        if (name && name !== "torch") return y;
      }
      return null;
    }

    /* --- actions -------------------------------------------------------- */

    doAction(message) {
      const action = message && message.action;
      this.stats.actions++;
      try {
        switch (action) {
          case "move":
            this.moveInput = {
              forward: !!message.forward, back: !!message.back, left: !!message.left,
              right: !!message.right, jump: !!message.jump, sprint: !!message.sprint
            };
            return this.result(action, true);
          case "look":
            this.player.yaw = number(message.yaw, this.player.yaw);
            this.player.pitch = number(message.pitch, this.player.pitch);
            this._sendLook();
            return this.result(action, true);
          case "mine": return this._mine(message);
          case "place": return this._place(message);
          case "attack": return this._attack(message);
          case "use": return this._use();
          case "chat":
            return this.say(String(message.message || message.text || ""))
              ? this.result(action, true)
              : this.result(action, false, "not connected");
          case "respawn":
            this._send(new Writer().u8(0x16).vi(0).bytes());
            return this.result(action, true);
          case "craft":
            return this.result(action, false, "crafting is not implemented by the headless client");
          case "join":
            return this.result(action, this.status === "playing", this.status);
          default: return this.result(action, false, "unknown action: " + action);
        }
      } catch (err) {
        this.stats.errors++;
        return this.result(action, false, err.message);
      }
    }

    _mine(message) {
      const x = Math.floor(number(message.x, 0));
      const y = Math.floor(number(message.y, 0));
      const z = Math.floor(number(message.z, 0));
      const face = Math.floor(number(message.face, 1));
      if (!this._send(new Writer().u8(0x07).u8(0).pos(x, y, z).u8(face).bytes())) {
        return this.result("mine", false, "not connected");
      }
      setTimeout(() => this._send(new Writer().u8(0x07).u8(2).pos(x, y, z).u8(face).bytes()), 700);
      this._send(new Writer().u8(0x0a).bytes());        // swing arm
      return this.result("mine", true);
    }

    _place(message) {
      const key = String(message.face || "top").toLowerCase();
      const face = FACES[key] === undefined ? 1 : FACES[key];
      const normal = FACE_NORMAL[face];
      const target = {
        x: Math.floor(number(message.x, 0)), y: Math.floor(number(message.y, 0)), z: Math.floor(number(message.z, 0))
      };
      const ref = { x: target.x - normal[0], y: target.y - normal[1], z: target.z - normal[2] };
      const w = new Writer();
      w.u8(0x08).pos(ref.x, ref.y, ref.z).u8(face).u16(this.heldSlot);
      w.u8(8).u8(8).u8(8);                             // cursor in the middle of the face
      const ok = this._send(w.bytes());
      this._send(new Writer().u8(0x0a).bytes());
      return this.result("place", ok, ok ? undefined : "not connected");
    }

    _attack(message) {
      let target = message.id !== undefined ? this.entities.get(message.id) : null;
      if (!target) {
        let best = null, bestDistance = 6;
        this.entities.forEach((entity) => {
          const d = Math.hypot(entity.x - this.player.x, entity.y - this.player.y, entity.z - this.player.z);
          if (d < bestDistance) { bestDistance = d; best = entity; }
        });
        target = best;
      }
      this._send(new Writer().u8(0x0a).bytes());        // always swing
      if (!target) return this.result("attack", false, "no entity within reach");
      return this.result("attack", this._send(new Writer().u8(0x02).vi(target.id).vi(1).bytes()));
    }

    _use() {
      const p = this.player;
      const rad = Math.PI * p.yaw / 180;
      const dx = -Math.sin(rad), dz = Math.cos(rad);
      for (let step = 1; step <= 4; step++) {
        const bx = Math.floor(p.x + dx * step);
        const bz = Math.floor(p.z + dz * step);
        const by = Math.floor(p.y);
        if (this.blocks.get(bx + "," + by + "," + bz)) {
          const w = new Writer();
          w.u8(0x08).pos(bx, by, bz).u8(1).u16(this.heldSlot).u8(8).u8(8).u8(8);
          const ok = this._send(w.bytes());
          this._send(new Writer().u8(0x0a).bytes());
          return this.result("use", ok);
        }
      }
      this._send(new Writer().u8(0x0a).bytes());
      return this.result("use", false, "no block in reach");
    }

    result(action, ok, error) {
      const message = { type: "result", ok: !!ok, action: action };
      if (error) message.error = error;
      this.sendToBridge(message);
      return message;
    }

    /* --- state ---------------------------------------------------------- */

    nearbyBlocks(radius, limit) {
      radius = radius || 16;
      limit = limit || 96;
      const p = this.player;
      const interesting = [], rest = [];
      this.blocks.forEach((name, key) => {
        const parts = key.split(",");
        const x = +parts[0], y = +parts[1], z = +parts[2];
        if (Math.abs(x - p.x) > radius || Math.abs(z - p.z) > radius || Math.abs(y - p.y) > radius) return;
        const distance = Math.hypot(x - p.x, y - p.y, z - p.z);
        const entry = { type: name, x: x, y: y, z: z, distance: distance };
        if (INTERESTING.test(name)) interesting.push(entry); else rest.push(entry);
      });
      interesting.sort(byDistance);
      rest.sort(byDistance);
      return interesting.concat(rest).slice(0, limit)
        .map((entry) => ({ type: entry.type, x: entry.x, y: entry.y, z: entry.z }));
    }

    snapshot() {
      const p = this.player;
      return {
        player: {
          x: round(p.x), y: round(p.y), z: round(p.z), yaw: round(p.yaw), pitch: round(p.pitch),
          health: p.health, food: p.food, dimension: p.dimension, game_mode: p.gameMode,
          on_ground: p.onGround, entity_id: p.entityId, status: this.status, server: this.serverUrl
        },
        inventory: this.inventory,
        blocks: this.nearbyBlocks(),
        entities: Array.from(this.entities.values()).slice(0, 32)
          .map((e) => ({ id: e.id, type: e.type, x: round(e.x), y: round(e.y), z: round(e.z) })),
        chat: this.chat.slice(-6)
      };
    }

    /* --- AI bridge ------------------------------------------------------ */

    connectBridge() {
      if (!this.bridgeUrl) return this;
      const WS = global.WebSocket;
      if (!WS) return this;
      const make = () => {
        let socket;
        try { socket = new WS(this.bridgeUrl); } catch (err) { return; }
        this.aiSocket = socket;
        socket.onopen = () => {
          this.sendToBridge({ type: "hello", version: VERSION, client: "eagler-headless", server_url: this.serverUrl });
          this.log("AI bridge connected on " + this.bridgeUrl);
        };
        socket.onmessage = (event) => {
          let message;
          try { message = JSON.parse(typeof event.data === "string" ? event.data : String(event.data)); } catch (err) { return; }
          this.onBridgeMessage(message);
        };
        socket.onclose = () => { this.aiSocket = null; setTimeout(make, 1500); };
        socket.onerror = () => { };
      };
      make();
      return this;
    }

    onBridgeMessage(message) {
      if (!message || typeof message !== "object") return;
      if (message.type === "observe") {
        this.sendToBridge(Object.assign({ type: "state" }, this.snapshot()));
        return;
      }
      if (message.type === "config") {
        if (message.server_url && this.status !== "playing" && this.status !== "handshake" && this.status !== "connecting") {
          this.serverUrl = message.server_url;
          this.connect();
        }
        return;
      }
      if (message.type === "action") this.doAction(message);
    }

    sendToBridge(message) {
      const socket = this.aiSocket;
      if (socket && socket.readyState === 1) {
        try { socket.send(JSON.stringify(message)); } catch (err) { /* dropped */ }
      }
    }
  }

  /* ---------------------------------------------------------------- helpers */

  function number(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
  function round(value) { return Math.round(value * 100) / 100; }
  function byDistance(a, b) { return a.distance - b.distance; }

  function toBytes(data) {
    if (!data) return null;
    if (data instanceof Uint8Array) return data;
    if (typeof ArrayBuffer !== "undefined" && data instanceof ArrayBuffer) return new Uint8Array(data);
    if (data.buffer) return new Uint8Array(data.buffer, data.byteOffset || 0, data.byteLength);
    return null;
  }

  function hex(bytes) {
    let out = "";
    for (let i = 0; i < bytes.length; i++) out += (bytes[i] < 16 ? "0" : "") + bytes[i].toString(16);
    return out;
  }

  function flattenChat(node) {
    if (node === null || node === undefined) return "";
    if (typeof node === "string") return node;
    if (Array.isArray(node)) return node.map(flattenChat).join("");
    if (node.translate) return node.translate + (node.with ? " " + flattenChat(node.with) : "");
    return (node.text || "") + (node.extra ? flattenChat(node.extra) : "");
  }

  function skipNbt(r) {
    readTag(r, r.u8(), false);
  }
  function readTag(r, type, named) {
    if (type === 0) return;
    if (named) { const n = r.u16(); r.skip(n); }
    switch (type) {
      case 1: r.skip(1); break;                       // byte
      case 2: r.skip(2); break;                       // short
      case 3: r.skip(4); break;                       // int
      case 4: r.skip(8); break;                       // long
      case 5: r.skip(4); break;                       // float
      case 6: r.skip(8); break;                       // double
      case 7: r.skip(r.i32()); break;                 // byte array
      case 8: r.skip(r.u16()); break;                 // string
      case 9: {                                       // list
        const itemType = r.u8();
        const n = r.i32();
        for (let i = 0; i < n; i++) readTag(r, itemType, false);
        break;
      }
      case 10: {                                      // compound
        for (;;) {
          const childType = r.u8();
          if (childType === 0) break;
          readTag(r, childType, true);
        }
        break;
      }
      case 11: r.skip(r.i32() * 4); break;            // int array
      case 12: r.skip(r.i32() * 8); break;            // long array
      default: break;
    }
  }

  /* -------------------------------------------------------------- CLI entry */

  function parseArgs(argv) {
    const opts = {};
    for (let i = 0; i < argv.length; i++) {
      const arg = argv[i];
      if (arg === "--server") opts.serverUrl = argv[++i];
      else if (arg === "--bridge") opts.bridgeUrl = argv[++i];
      else if (arg === "--no-bridge") opts.bridgeUrl = null;
      else if (arg === "--username") opts.username = argv[++i];
      else if (arg === "--register") opts.registerPassword = argv[++i];
      else if (arg === "--login") opts.loginPassword = argv[++i];
      else if (arg === "--quiet") opts.verbose = false;
      else if (arg === "--help" || arg === "-h") opts.help = true;
    }
    return opts;
  }

  function main() {
    const opts = parseArgs(process.argv.slice(2));
    if (opts.help) {
      console.log([
        "CarrotCraft headless client",
        "",
        "  --username <name>     player name (default AI_Bot)",
        "  --server <url>        server socket (default " + DEFAULT_SERVER + ")",
        "  --bridge <url>        AI socket (default " + DEFAULT_BRIDGE + ")",
        "  --no-bridge           run without the Python AI",
        "  --register <password> send /register once in game (auth plugins)",
        "  --login <password>    send /login once in game",
        "  --quiet               less logging"
      ].join("\n"));
      return;
    }
    const client = new HeadlessClient(opts);
    client.connect();
    if (opts.bridgeUrl !== null) client.connectBridge();
    const shutdown = () => { client._stopMoving(); process.exit(0); };
    if (typeof process.on === "function") { process.on("SIGINT", shutdown); process.on("SIGTERM", shutdown); }
  }

  const api = { HeadlessClient: HeadlessClient, VERSION: VERSION, parseArgs: parseArgs, main: main, nameOf: nameOf };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  global.CarrotCraftHeadless = api;
  if (typeof require !== "undefined" && typeof module !== "undefined" && typeof process !== "undefined"
      && require.main === module && /headless_client\.js$/.test(process.argv[1] || "")) {
    main();
  }
})(typeof globalThis !== "undefined" ? globalThis : this);