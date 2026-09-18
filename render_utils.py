"""描画で繰り返し使われる共通処理をまとめたヘルパー群。"""

import math
import pygame


def make_alpha_surface(size, fill=None):
    """フルスクリーン等の透過(SRCALPHA)サーフェスを生成する。"""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    if fill is not None:
        surf.fill(fill)
    return surf


def draw_rotated_rect(surface, size, color, angle_rad, center):
    """指定サイズ・色の矩形を角度に合わせて回転させ、中心座標に描画する。"""
    rect_surf = make_alpha_surface(size, fill=color)
    rotated_surf = pygame.transform.rotate(rect_surf, -math.degrees(angle_rad))
    dest_rect = rotated_surf.get_rect(center=center)
    surface.blit(rotated_surf, dest_rect.topleft)
