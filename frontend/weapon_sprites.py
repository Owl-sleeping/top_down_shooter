"""武器画像(images/配下)の読み込みと、向きに合わせた回転描画。

- held sprite(真上から見た画像, `_up.png`): プレイヤーが構えている武器として
  マウス方向に合わせて回転描画する(ゲーム中の見た目)。
- portrait(横から見た画像): 向きを回転させず、HUDやメニューでの
  「今持っている武器」の静止アイコン表示に使う。
"""

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
    # 元画像は銃口が左向きに描かれているが、回転処理は角度0=右向きを前提にしているため
    # 左右反転して銃口を右に揃えておく(そうしないと常に180度反対を向いてしまう)。
    return pygame.transform.flip(scaled, True, False)


def load_weapon_sprites() -> dict[str, pygame.Surface]:
    """プレイヤーが構えている武器(真上視点)の画像。ゲーム開始時に一度だけ読み込む。"""
    return {weapon.name: _load_held_sprite(weapon.held_image_filename) for weapon in WEAPONS}


def load_weapon_portraits() -> dict[str, pygame.Surface]:
    """HUD/メニューで使う、回転させない静止アイコン用の武器画像(横から見た画像)。"""
    return {weapon.name: _scale_to_fit(_load_image(weapon.image_filename), WEAPON_PORTRAIT_SIZE) for weapon in WEAPONS}


def draw_weapon_sprite(
    surface: pygame.Surface, sprite: pygame.Surface, angle_rad: float, center: tuple[float, float]
) -> None:
    rotated = pygame.transform.rotate(sprite, -math.degrees(angle_rad))
    dest_rect = rotated.get_rect(center=center)
    surface.blit(rotated, dest_rect.topleft)
