"""描画で繰り返し使われる共通処理をまとめたヘルパー群。"""

import math
import pygame


def make_alpha_surface(size: tuple[int, int], fill: tuple[int, int, int, int] | None = None) -> pygame.Surface:
    """フルスクリーン等の透過(SRCALPHA)サーフェスを生成する。"""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    if fill is not None:
        surf.fill(fill)
    return surf


def draw_rotated_rect(
    surface: pygame.Surface,
    size: tuple[int, int],
    color: tuple[int, int, int],
    angle_rad: float,
    center: tuple[float, float],
) -> None:
    """指定サイズ・色の矩形を角度に合わせて回転させ、中心座標に描画する。"""
    rect_surf = make_alpha_surface(size, fill=color)
    rotated_surf = pygame.transform.rotate(rect_surf, -math.degrees(angle_rad))
    dest_rect = rotated_surf.get_rect(center=center)
    surface.blit(rotated_surf, dest_rect.topleft)
