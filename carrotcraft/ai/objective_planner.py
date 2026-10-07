from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re


@dataclass
class WorldSnapshot:
    player: dict = field(default_factory=dict)
    inventory: Dict[str, int] = field(default_factory=dict)
    blocks: List[dict] = field(default_factory=list)
    entities: List[dict] = field(default_factory=list)

    def has(self, item: str, amount: int = 1) -> bool:
        return int(self.inventory.get(item, 0)) >= amount


@dataclass
class Objective:
    id: str
    text: str
    action: str
    prerequisites: List[str] = field(default_factory=list)
    status: str = "pending"
    params: dict = field(default_factory=dict)


class ObjectivePlanningError(ValueError):
    pass


class ObjectivePlanner:
    """Version-aware Minecraft objective planner.

    The planner intentionally does not invent mechanics that are unavailable in
    the selected Minecraft version. Server plugins/mods can be represented later
    through a capabilities object once the headless client observes them.
    """

    def __init__(self, mc_version: str = "1.8.8"):
        self.mc_version = mc_version
        self.version_tuple = self._parse_version(mc_version)

    @staticmethod
    def _parse_version(version: str):
        m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version)
        if not m:
            raise ObjectivePlanningError(f"Invalid Minecraft version: {version!r}")
        return tuple(int(x or 0) for x in m.groups())

    def _at_least(self, major: int, minor: int, patch: int = 0) -> bool:
        return self.version_tuple >= (major, minor, patch)

    def plan(self, goal: str) -> List[Objective]:
        s = re.sub(r"[^a-z0-9 ]+", " ", goal.lower()).strip()

        if "full netherite" in s or "netherite armor" in s:
            if not self._at_least(1, 16):
                raise ObjectivePlanningError(
                    f"The selected Minecraft version is {self.mc_version}. "
                    "Vanilla Netherite was introduced in Minecraft 1.16, so "
                    "the planner will not invent ancient debris/netherite steps "
                    "for a 1.8.8 server. If CarrotCraft has custom netherite, "
                    "add it as a server capability/custom recipe."
                )
            return self._toposort(self.full_netherite())

        if "diamond" in s and ("full" in s or "armor" in s):
            return self._toposort(self.full_diamond())
        if "diamond" in s:
            return self._toposort(self.diamonds())

        return [Objective(
            "research",
            f"Research how to accomplish: {goal}",
            "research",
            params={"goal": goal},
        )]

    def full_netherite(self):
        # Netherite exists from 1.16 onward. For 1.20+, upgrading also needs a
        # Netherite Upgrade Smithing Template found in bastion remnants.
        objectives = [
            Objective("wood", "Get wood", "gather", params={"item": "oak_log", "amount": 4}),
            Objective("planks", "Craft wooden planks", "craft", ["wood"], {"item": "oak_planks", "amount": 8}),
            Objective("table", "Craft a crafting table", "craft", ["planks"], {"item": "crafting_table", "amount": 1}),
            Objective("sticks", "Craft sticks", "craft", ["planks"], {"item": "stick", "amount": 8}),
            Objective("wood_pick", "Craft a wooden pickaxe", "craft", ["table", "sticks"], {"item": "wooden_pickaxe", "amount": 1}),
            Objective("stone", "Mine stone", "mine", ["wood_pick"], {"block": "stone", "amount": 20}),
            Objective("stone_pick", "Craft a stone pickaxe", "craft", ["stone", "table", "sticks"], {"item": "stone_pickaxe", "amount": 1}),
            Objective("iron", "Mine iron", "mine", ["stone_pick"], {"block": "iron_ore", "amount": 31}),
            Objective("iron_pick", "Craft an iron pickaxe", "craft", ["iron", "table", "sticks"], {"item": "iron_pickaxe", "amount": 1}),
            Objective("diamonds", "Mine diamonds", "mine", ["iron_pick"], {"block": "diamond_ore", "amount": 35}),
            Objective("diamond_gear", "Craft diamond armor and diamond tools", "craft", ["diamonds", "table"], {"target": "diamond_gear"}),
            Objective("diamond_pick", "Craft a diamond pickaxe", "craft", ["diamonds", "table", "sticks"], {"item": "diamond_pickaxe", "amount": 1}),
            Objective("obsidian", "Obtain obsidian", "mine", ["diamond_pick"], {"block": "obsidian", "amount": 10}),
            Objective("portal", "Build and enter a Nether portal", "build_portal", ["obsidian"], {}),
            Objective("debris", "Mine ancient debris", "mine_nether", ["portal"], {"block": "ancient_debris", "amount": 36}),
            Objective("gold", "Mine gold", "mine_nether", ["portal"], {"block": "gold_ore", "amount": 36}),
            Objective("netherite", "Craft netherite ingots", "smelt_and_craft", ["debris", "gold"], {"item": "netherite_ingot", "amount": 9}),
        ]

        if self._at_least(1, 20):
            objectives.extend([
                Objective("bastion", "Find a Nether bastion", "explore_nether", ["portal"], {}),
                Objective("upgrade_template", "Obtain a Netherite Upgrade Smithing Template", "loot_structure", ["bastion"], {"item": "netherite_upgrade_smithing_template", "amount": 1}),
                Objective("smithing_table", "Craft a smithing table", "craft", ["iron", "planks"], {"item": "smithing_table", "amount": 1}),
                Objective("upgrade", "Upgrade diamond armor and tools to netherite", "upgrade_netherite", ["netherite", "diamond_gear", "upgrade_template", "smithing_table"], {"target": "full_netherite"}),
            ])
        else:
            objectives.append(
                Objective("smithing_table", "Craft a smithing table", "craft", ["iron", "planks"], {"item": "smithing_table", "amount": 1})
            )
            objectives.append(
                Objective("upgrade", "Upgrade diamond armor and tools to netherite", "upgrade_netherite", ["netherite", "diamond_gear", "smithing_table"], {"target": "full_netherite"})
            )

        return objectives

    def diamonds(self):
        return [
            Objective("wood", "Get wood", "gather", params={"item": "oak_log", "amount": 4}),
            Objective("table", "Craft a crafting table", "craft", ["wood"], {"item": "crafting_table", "amount": 1}),
            Objective("sticks", "Craft sticks", "craft", ["wood"], {"item": "stick", "amount": 8}),
            Objective("stone", "Mine stone", "mine", ["sticks"], {"block": "stone", "amount": 3}),
            Objective("stone_pick", "Craft a stone pickaxe", "craft", ["stone", "table", "sticks"], {"item": "stone_pickaxe", "amount": 1}),
            Objective("iron", "Mine iron", "mine", ["stone_pick"], {"block": "iron_ore", "amount": 3}),
            Objective("iron_pick", "Craft an iron pickaxe", "craft", ["iron", "table", "sticks"], {"item": "iron_pickaxe", "amount": 1}),
            Objective("diamonds", "Mine diamonds", "mine", ["iron_pick"], {"block": "diamond_ore", "amount": 35}),
        ]

    def full_diamond(self):
        x = self.diamonds()
        x.append(Objective("gear", "Craft full diamond armor and tools", "craft", ["diamonds"], {"target": "diamond_gear"}))
        return x

    def _toposort(self, objs):
        by_id = {o.id: o for o in objs}
        out = []
        seen = set()

        def visit(k):
            if k in seen:
                return
            if k not in by_id:
                raise ObjectivePlanningError(f"Unknown prerequisite {k!r}")
            seen.add(k)
            for d in by_id[k].prerequisites:
                visit(d)
            out.append(by_id[k])

        for o in objs:
            visit(o.id)
        return out

    def next_objective(self, objectives, world: WorldSnapshot) -> Optional[Objective]:
        by_id = {o.id: o for o in objectives}
        for o in objectives:
            if o.status == "done":
                continue
            if any(by_id[d].status != "done" for d in o.prerequisites):
                continue
            item = o.params.get("item")
            amount = int(o.params.get("amount", 1))
            if item and world.has(item, amount):
                o.status = "done"
                continue
            o.status = "active"
            return o
        return None
