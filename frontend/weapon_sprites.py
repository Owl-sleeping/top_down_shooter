"""武器画像の読み込みと、向きに合わせた回転描画。"""

import math

import pygame

from backend.weapons import WEAPONS
from constants import WEAPON_SPRITE_MAX_SIZE, WEAPON_PORTRAIT_SIZE
from resources import IMAGES_DIR


def _load_image(filename: str) -> pygame.Surface:
    return pygame.image.load(str(IMAGES_DIR / filename)).convert_alpha()


def _scale_to_fit(image: pygame.Surface, max_size: tuple[int, int]) -> pygame.Surface:
    max_w, max_h = max_size
    scale = min(max_w / image.get_width(), max_h / image.get_height())
    size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
    return pygame.transform.smoothscale(image, size)


def _load_held_sprite(filename: str) -> pygame.Surface:
    scaled = _scale_to_fit(_load_image(filename), WEAPON_SPRITE_MAX_SIZE)
    return pygame.transform.flip(scaled, True, False)


def load_weapon_sprites() -> dict[str, pygame.Surface]:
    return {weapon.name: _load_held_sprite(weapon.held_image_filename) for weapon in WEAPONS}


def load_weapon_portraits() -> dict[str, pygame.Surface]:
    return {weapon.name: _scale_to_fit(_load_image(weapon.image_filename), WEAPON_PORTRAIT_SIZE) for weapon in WEAPONS}


def draw_weapon_sprite(
    surface: pygame.Surface, sprite: pygame.Surface, angle_rad: float, center: tuple[float, float]
) -> None:
    rotated = pygame.transform.rotate(sprite, -math.degrees(angle_rad))
    dest_rect = rotated.get_rect(center=center)
    surface.blit(rotated, dest_rect.topleft)
