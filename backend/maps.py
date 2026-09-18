"""対戦マップの定義（壁配置とスポーン地点）。"""

import pygame

Point = tuple[int, int]
WallSpec = tuple[int, int, int, int]


class GameMap:
    def __init__(self, name: str, walls: list[WallSpec], spawn_positions: dict[int, Point]) -> None:
        self.name = name
        self.walls = walls
        self.spawn_positions = spawn_positions

    def build_wall_rects(self) -> list[pygame.Rect]:
        return [pygame.Rect(*w) for w in self.walls]


MAPS: list[GameMap] = [
    GameMap(
        name="Classic",
        walls=[
            (600, 200, 60, 300),
            (300, 100, 120, 50),
            (850, 450, 200, 80),
        ],
        spawn_positions={0: (200, 360), 1: (1000, 360)},
    ),
    GameMap(
        name="Crossfire",
        walls=[
            (0, 340, 560, 40),    # 左側の横壁
            (720, 340, 560, 40),  # 右側の横壁（中央にレーンが空く）
            (600, 0, 40, 300),    # 中央上の縦壁
            (600, 420, 40, 300),  # 中央下の縦壁
        ],
        spawn_positions={0: (100, 80), 1: (1180, 640)},
    ),
    GameMap(
        name="Open Arena",
        walls=[
            (590, 335, 100, 50),  # 中央の小さな遮蔽物のみ
        ],
        spawn_positions={0: (150, 360), 1: (1130, 360)},
    ),
]


def get_map_by_name(name: str) -> GameMap:
    return next((m for m in MAPS if m.name == name), MAPS[0])
