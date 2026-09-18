"""武器画像(images/配下)の読み込みと、向きに合わせた回転描画。"""

import math

import pygame

from backend.weapons import WEAPONS
from constants import WEAPON_SPRITE_MAX_SIZE
from resources import IMAGES_DIR


def _load_scaled(filename: str) -> pygame.Surface:
    image = pygame.image.load(str(IMAGES_DIR / filename)).convert_alpha()
    max_w, max_h = WEAPON_SPRITE_MAX_SIZE
    scale = min(max_w / image.get_width(), max_h / image.get_height())
    size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
    scaled = pygame.transform.smoothscale(image, size)
    # 元画像は銃口が左向きに描かれているが、回転処理は角度0=右向きを前提にしているため
    # 左右反転して銃口を右に揃えておく(そうしないと常に180度反対を向いてしまう)。
    return pygame.transform.flip(scaled, True, False)


def load_weapon_sprites() -> dict[str, pygame.Surface]:
    """全武器の画像をゲーム開始時に一度だけ読み込み、表示用サイズに縮小しておく。"""
    return {weapon.name: _load_scaled(weapon.image_filename) for weapon in WEAPONS}


def draw_weapon_sprite(
    surface: pygame.Surface, sprite: pygame.Surface, angle_rad: float, center: tuple[float, float]
) -> None:
    rotated = pygame.transform.rotate(sprite, -math.degrees(angle_rad))
    dest_rect = rotated.get_rect(center=center)
    surface.blit(rotated, dest_rect.topleft)
