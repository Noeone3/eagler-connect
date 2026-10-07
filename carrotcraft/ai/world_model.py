from dataclasses import dataclass, field

@dataclass
class WorldModel:
    player: dict = field(default_factory=dict)
    inventory: dict = field(default_factory=dict)
    blocks: dict = field(default_factory=dict)
    entities: dict = field(default_factory=dict)

    def apply(self, state):
        self.player = state.get("player", self.player)
        self.inventory = state.get("inventory", self.inventory)
        for b in state.get("blocks", []):
            self.blocks[f"{b.get('x')},{b.get('y')},{b.get('z')}"] = b
        for e in state.get("entities", []):
            self.entities[str(e.get("id"))] = e
