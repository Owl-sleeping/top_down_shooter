"""武器画像(images/配下)の読み込みと、向きに合わせた回転描画。"""

import math
from pathlib import Path

import pygame

from backend.weapons import WEAPONS
from constants import WEAPON_SPRITE_MAX_SIZE

IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"


def _load_scaled(filename: str) -> pygame.Surface:
    image = pygame.image.load(str(IMAGES_DIR / filename)).convert_alpha()
    max_w, max_h = WEAPON_SPRITE_MAX_SIZE
    scale = min(max_w / image.get_width(), max_h / image.get_height())
    size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
    return pygame.transform.smoothscale(image, size)


def load_weapon_sprites() -> dict[str, pygame.Surface]:
    """全武器の画像をゲーム開始時に一度だけ読み込み、表示用サイズに縮小しておく。"""
    return {weapon.name: _load_scaled(weapon.image_filename) for weapon in WEAPONS}


def draw_weapon_sprite(
    surface: pygame.Surface, sprite: pygame.Surface, angle_rad: float, center: tuple[float, float]
) -> None:
    rotated = pygame.transform.rotate(sprite, -math.degrees(angle_rad))
    dest_rect = rotated.get_rect(center=center)
    surface.blit(rotated, dest_rect.topleft)
