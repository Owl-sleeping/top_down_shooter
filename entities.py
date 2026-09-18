"""弾丸・グレネード・爆発エフェクトを表すエンティティ群。"""

import math
import pygame

from render_utils import draw_rotated_rect
from constants import (
    COLOR_BULLET, COLOR_GRENADE,
    BULLET_SPEED, BULLET_WIDTH, BULLET_HEIGHT,
    GRENADE_THROW_SPEED, GRENADE_FRICTION, GRENADE_FUSE_TIME,
    GRENADE_EXPLOSION_RADIUS, GRENADE_VISUAL_RADIUS,
    EXPLOSION_DURATION,
)

Point = tuple[float, float]


class Bullet:
    def __init__(self, p: Point, angle: float, owner_id: int = 0) -> None:
        self.pos = pygame.Vector2(p)
        self.angle = angle
        self.speed = BULLET_SPEED
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * self.speed
        self.alive = True
        self.width, self.height = BULLET_WIDTH, BULLET_HEIGHT
        self.owner_id = owner_id

    def update(self, dt: float) -> None:
        self.pos += self.vel * dt

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(self.pos.x - self.width / 2, self.pos.y - self.height / 2, self.width, self.height)

    def draw(self, surface: pygame.Surface) -> None:
        # 回転した矩形の描画
        draw_rotated_rect(surface, (self.width, self.height), COLOR_BULLET, self.angle, self.pos)

    def visible_to(self, triangles: list[list[Point]]) -> bool:
        # 弾のが視界内にあるか
        px, py = self.pos.x, self.pos.y
        for tri in triangles:
            if self.point_in_triangle((px, py), tri[0], tri[1], tri[2]):
                return True
        return False

    @staticmethod
    def point_in_triangle(pt: Point, v1: Point, v2: Point, v3: Point) -> bool:
        def sign(p1: Point, p2: Point, p3: Point) -> float:
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign(pt, v1, v2)
        d2 = sign(pt, v2, v3)
        d3 = sign(pt, v3, v1)

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)


class Grenade:
    def __init__(self, p: Point, angle: float, owner_id: int = 0) -> None:
        self.pos = pygame.Vector2(p)
        self.speed = GRENADE_THROW_SPEED
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * self.speed
        self.timer = GRENADE_FUSE_TIME
        self.exploded = False
        self.explosion_radius = GRENADE_EXPLOSION_RADIUS
        self.owner_id = owner_id

    def update(self, dt: float) -> None:
        if self.exploded:
            return
        self.pos += self.vel * dt
        self.vel *= GRENADE_FRICTION

        self.timer -= dt
        if self.timer <= 0:
            self.exploded = True

    def draw(self, surface: pygame.Surface) -> None:
        if not self.exploded:
            pygame.draw.circle(surface, COLOR_GRENADE, (int(self.pos.x), int(self.pos.y)), GRENADE_VISUAL_RADIUS)

    def explosion_circle(self) -> tuple[float, float, float]:
        return (self.pos.x, self.pos.y, self.explosion_radius)


class Explosion:
    def __init__(self, circle_data: tuple[float, float, float], owner_id: int = 0) -> None:
        self.x, self.y, self.radius = circle_data
        self.timer = EXPLOSION_DURATION
        self.owner_id = owner_id
        self.damaged_ids: set[int] = set()

    def intersects_rect(self, rect: pygame.Rect) -> bool:
        # 円と矩形の当たり判定
        closest_x = max(rect.left, min(self.x, rect.right))
        closest_y = max(rect.top, min(self.y, rect.bottom))
        dist_x = self.x - closest_x
        dist_y = self.y - closest_y
        return (dist_x**2 + dist_y**2) < (self.radius**2)
