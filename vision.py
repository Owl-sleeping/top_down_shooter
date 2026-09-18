"""プレイヤーの視界(FOV)をレイキャストで計算するモジュール。"""

import math

import pygame

from constants import VISION_RAY_COUNT, VISION_RAY_MAX_LENGTH

Point = tuple[float, float]


class Vision:
    def __init__(self, walls: list[pygame.Rect]) -> None:
        self.walls = walls

    def ray(self, p: Point, angle: float) -> Point:
        ray_end = (
            p[0] + math.cos(angle) * VISION_RAY_MAX_LENGTH,
            p[1] + math.sin(angle) * VISION_RAY_MAX_LENGTH,
        )
        closest_hit = ray_end
        min_dist_sq = VISION_RAY_MAX_LENGTH ** 2

        for w in self.walls:
            # 矩形の4辺の取り出す
            lines = [
                ((w.left, w.top), (w.right, w.top)),
                ((w.right, w.top), (w.right, w.bottom)),
                ((w.right, w.bottom), (w.left, w.bottom)),
                ((w.left, w.bottom), (w.left, w.top))
            ]
            for seg_start, seg_end in lines:
                hit = self.line_intersection((p, ray_end), (seg_start, seg_end))
                if hit:
                    dist_sq = (hit[0] - p[0])**2 + (hit[1] - p[1])**2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        closest_hit = hit
        return closest_hit

    @staticmethod
    def line_intersection(line1: tuple[Point, Point], line2: tuple[Point, Point]) -> Point | None:
        (x1, y1), (x2, y2) = line1
        (x3, y3), (x4, y4) = line2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return None

    def get_triangles(self, p: Point, direction: float, fov: float) -> list[list[Point]]:
        pts = []
        n = VISION_RAY_COUNT
        half_fov = fov / 2.0
        start_angle = direction - half_fov

        for i in range(n):
            angle = start_angle + (fov * i / (n - 1))
            pts.append(self.ray(p, angle))

        triangles = []
        for i in range(n - 1):
            triangles.append([p, pts[i], pts[i + 1]])
        return triangles
