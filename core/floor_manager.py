from dataclasses import replace
from models.floor import Floor

PALETTE = ((.35,.83,.69), (.40,.64,.98), (.98,.70,.35), (.78,.55,.94), (.96,.48,.62), (.45,.85,.91))


class FloorManager:
    def __init__(self):
        self.floors: dict[str, Floor] = {}

    def validate(self, floor):
        floor.validate()
        for other in self.floors.values():
            if other.key == floor.key:
                continue
            for name in ('floor_id', 'map_id', 'map_name'):
                if getattr(other, name) == getattr(floor, name):
                    raise ValueError(f'{name} 已被楼层 {other.floor_id} 使用。')

    def put(self, floor):
        self.validate(floor)
        self.floors[floor.key] = floor

    def create(self):
        number = 1
        while any(f.map_id == number or f.floor_id == f'floor_{number}' or f.map_name == f'floor_{number}'
                  for f in self.floors.values()):
            number += 1
        floor = Floor(f'floor_{number}', number, f'floor_{number}', color=PALETTE[len(self.floors) % len(PALETTE)])
        self.put(floor)
        return floor

    def set_visible(self, key, visible):
        self.floors[key] = replace(self.floors[key], visible=visible)

    def delete(self, key):
        del self.floors[key]
