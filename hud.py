"""HUD(HPバー・弾薬・リロードゲージ・インベントリ)の描画。"""

import pygame

from player import Player
from constants import (
    COLOR_HP_BG, COLOR_HP_FG, COLOR_AMMO_FULL, COLOR_AMMO_EMPTY,
    COLOR_RELOAD_BG, COLOR_RELOAD_FG, COLOR_RELOAD_TEXT,
    COLOR_SLOT_BG, COLOR_SLOT_BORDER, COLOR_SLOT_NUMBER, COLOR_COUNT_TEXT, COLOR_COUNT_BG,
    COLOR_GRENADE_BAR, COLOR_MEDKIT_BAR, COLOR_ENEMY_PLAYER,
    COLOR_GRENADE_ICON, COLOR_MEDKIT_ICON_BODY, COLOR_MEDKIT_ICON_CROSS,
    MAX_AMMO, RELOAD_TIME,
    MAX_GRENADES, MAX_MEDKITS,
    HP_BAR_POS, HP_BAR_SIZE, AMMO_BOX_ORIGIN, AMMO_BOX_SIZE, AMMO_BOX_GAP,
    RELOAD_GAUGE_POS, RELOAD_GAUGE_SIZE, RELOAD_TEXT_POS,
    ENEMY_HP_BAR_POS, ENEMY_HP_BAR_SIZE, ENEMY_HP_LABEL_OFFSET_Y,
    INVENTORY_SLOT_COUNT, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_GAP, INVENTORY_ORIGIN,
    INVENTORY_ICON_SIZE,
)

# スロット番号(表示順)に対応する所持品の定義。ここに1件足すだけで
# インベントリスロットに新しいアイテムを割り当てられる。要素が無い
# スロットは枠だけが描画される。
INVENTORY_ITEMS = [
    {"key": "grenade_count", "texture": "grenade", "max": MAX_GRENADES, "bar_color": COLOR_GRENADE_BAR},
    {"key": "medkit_count", "texture": "medkit", "max": MAX_MEDKITS, "bar_color": COLOR_MEDKIT_BAR},
]


def create_item_textures() -> dict[str, pygame.Surface]:
    """インベントリに表示するアイコンをゲーム開始時に一度だけ生成する。"""
    grenade_tex = pygame.Surface(INVENTORY_ICON_SIZE, pygame.SRCALPHA)
    pygame.draw.circle(grenade_tex, COLOR_GRENADE_ICON, (24, 24), 20)

    medkit_tex = pygame.Surface(INVENTORY_ICON_SIZE, pygame.SRCALPHA)
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_BODY, (8, 8, 32, 32))
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_CROSS, (20, 12, 8, 24))
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_CROSS, (12, 20, 24, 8))

    return {"grenade": grenade_tex, "medkit": medkit_tex}


def draw_hud(
    screen: pygame.Surface,
    font: pygame.font.Font,
    player: Player,
    item_textures: dict[str, pygame.Surface],
    enemy: Player | None = None,
) -> None:
    _draw_hp_bar(screen, player)
    _draw_ammo_boxes(screen, player)
    _draw_reload_gauge(screen, font, player)
    _draw_inventory(screen, font, player, item_textures)
    if enemy is not None:
        _draw_enemy_hp_bar(screen, font, enemy)


def _draw_hp_bar(screen: pygame.Surface, player: Player) -> None:
    pygame.draw.rect(screen, COLOR_HP_BG, (*HP_BAR_POS, *HP_BAR_SIZE))
    pygame.draw.rect(screen, COLOR_HP_FG, (
        HP_BAR_POS[0], HP_BAR_POS[1], HP_BAR_SIZE[0] * (player.hp / player.max_hp), HP_BAR_SIZE[1]
    ))


def _draw_enemy_hp_bar(screen: pygame.Surface, font: pygame.font.Font, enemy: Player) -> None:
    label = font.render("ENEMY", True, COLOR_ENEMY_PLAYER)
    screen.blit(label, (ENEMY_HP_BAR_POS[0], ENEMY_HP_BAR_POS[1] - ENEMY_HP_LABEL_OFFSET_Y))
    pygame.draw.rect(screen, COLOR_HP_BG, (*ENEMY_HP_BAR_POS, *ENEMY_HP_BAR_SIZE))
    pygame.draw.rect(screen, COLOR_ENEMY_PLAYER, (
        ENEMY_HP_BAR_POS[0], ENEMY_HP_BAR_POS[1], ENEMY_HP_BAR_SIZE[0] * (enemy.hp / enemy.max_hp), ENEMY_HP_BAR_SIZE[1]
    ))


def _draw_ammo_boxes(screen: pygame.Surface, player: Player) -> None:
    for i in range(MAX_AMMO):
        box = pygame.Rect(AMMO_BOX_ORIGIN[0] + i * AMMO_BOX_GAP, AMMO_BOX_ORIGIN[1], *AMMO_BOX_SIZE)
        if i < player.ammo:
            pygame.draw.rect(screen, COLOR_AMMO_FULL, box)
        else:
            pygame.draw.rect(screen, COLOR_AMMO_EMPTY, box, 2)


def _draw_reload_gauge(screen: pygame.Surface, font: pygame.font.Font, player: Player) -> None:
    if not player.reload:
        return
    rate = max(0.0, min(1.0, 1.0 - (player.reload_time / RELOAD_TIME)))
    pygame.draw.rect(screen, COLOR_RELOAD_BG, (*RELOAD_GAUGE_POS, *RELOAD_GAUGE_SIZE))
    pygame.draw.rect(screen, COLOR_RELOAD_FG, (
        RELOAD_GAUGE_POS[0], RELOAD_GAUGE_POS[1], RELOAD_GAUGE_SIZE[0] * rate, RELOAD_GAUGE_SIZE[1]
    ))
    txt = font.render("RELOAD", True, COLOR_RELOAD_TEXT)
    screen.blit(txt, RELOAD_TEXT_POS)


def _draw_inventory(
    screen: pygame.Surface,
    font: pygame.font.Font,
    player: Player,
    item_textures: dict[str, pygame.Surface],
) -> None:
    for i in range(INVENTORY_SLOT_COUNT):
        slot = pygame.Rect(INVENTORY_ORIGIN[0] + i * INVENTORY_SLOT_GAP, INVENTORY_ORIGIN[1], *INVENTORY_SLOT_SIZE)
        pygame.draw.rect(screen, COLOR_SLOT_BG, slot)
        pygame.draw.rect(screen, COLOR_SLOT_BORDER, slot, 3)

        if i < len(INVENTORY_ITEMS):
            item = INVENTORY_ITEMS[i]
            count = getattr(player, item["key"])
            texture = item_textures[item["texture"]]

            screen.blit(texture, texture.get_rect(center=slot.center))
            txt = font.render(str(count), True, COLOR_COUNT_TEXT)
            screen.blit(txt, txt.get_rect(center=(slot.centerx + 18, slot.centery + 18)))

            count_box = pygame.Rect(slot.x + 10, slot.y + 55, 50, 12)
            pygame.draw.rect(screen, COLOR_COUNT_BG, count_box)
            pygame.draw.rect(screen, item["bar_color"], (
                count_box.x, count_box.y, 50.0 * count / item["max"], 12
            ))

        # スロット番号
        num_txt = font.render(str(i + 1), True, COLOR_SLOT_NUMBER)
        screen.blit(num_txt, (slot.x + 5, slot.y + 5))
