"""Action Executor.

Turns an objective from the planner into the concrete messages the headless
client understands (see bridge/protocol.md). It only uses the world snapshot
the client reported - it never invents coordinates or blocks.
"""

BLOCK_NAME_KEYS = ("type", "name", "block", "id")


def _block_name(block):
    for key in BLOCK_NAME_KEYS:
        value = block.get(key)
        if isinstance(value, str):
            return value
    return None


def _block_position(block):
    try:
        return float(block["x"]), float(block["y"]), float(block["z"])
    except (KeyError, TypeError, ValueError):
        return None


def _player_position(player):
    try:
        return float(player.get("x", 0)), float(player.get("y", 0)), float(player.get("z", 0))
    except (TypeError, ValueError):
        return 0.0, 0.0, 0.0


class ActionExecutor:
    def __init__(self, tick_seconds=0.4, reach=6.0):
        self.tick_seconds = tick_seconds
        self.reach = reach
        self.scan_yaw = 0.0

    def commands(self, objective, world):
        """Protocol messages that move `objective` one step forward."""
        params = objective.params or {}
        player = world.player if isinstance(world.player, dict) else {}

        if objective.action in ("mine", "mine_nether", "gather"):
            wanted = params.get("block") or params.get("item")
            target = self._nearest_block(world, wanted, player)
            if target:
                return [{"action": "mine", "x": target[0], "y": target[1], "z": target[2]}]
            return self._scan(player)

        if objective.action in ("craft", "smelt_and_craft"):
            recipe = params.get("item") or params.get("target")
            return [{"action": "craft", "recipe": recipe}]

        if objective.action in ("build_portal", "upgrade_netherite"):
            return [{"action": "use"}]

        # research, explore_nether, loot_structure and anything else:
        # keep scanning the area until the client reports something useful.
        return self._scan(player)

    def _nearest_block(self, world, wanted, player):
        origin = _player_position(player)
        best = None
        best_distance = None

        for block in world.blocks:
            if not isinstance(block, dict):
                continue
            if wanted and _block_name(block) != wanted:
                continue
            position = _block_position(block)
            if position is None:
                continue
            distance = sum((position[i] - origin[i]) ** 2 for i in range(3))
            if best_distance is None or distance < best_distance:
                best, best_distance = position, distance

        return best

    def _scan(self, player):
        self.scan_yaw = (self.scan_yaw + 30.0) % 360.0
        return [
            {"action": "look", "yaw": self.scan_yaw, "pitch": -5},
            {"action": "move", "forward": True, "back": False, "left": False,
             "right": False, "jump": False, "sprint": True},
        ]