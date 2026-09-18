import math
import sys
import pygame

from render_utils import make_alpha_surface, draw_rotated_rect
from vision import Vision
from entities import Bullet, Grenade, Explosion
from player import Player
from constants import (
    WIDTH, HEIGHT, FPS, WINDOW_TITLE,
    COLOR_BG, COLOR_WALL, COLOR_PLAYER, COLOR_GUN,
    COLOR_EXPLOSION, COLOR_HP_BG, COLOR_HP_FG, COLOR_AMMO_FULL, COLOR_AMMO_EMPTY,
    COLOR_RELOAD_BG, COLOR_RELOAD_FG, COLOR_RELOAD_TEXT,
    COLOR_SLOT_BG, COLOR_SLOT_BORDER, COLOR_SLOT_NUMBER, COLOR_COUNT_TEXT, COLOR_COUNT_BG,
    COLOR_GRENADE_BAR, COLOR_MEDKIT_BAR,
    COLOR_GRENADE_ICON, COLOR_MEDKIT_ICON_BODY, COLOR_MEDKIT_ICON_CROSS,
    PLAYER_START_POS,
    MAX_AMMO, RELOAD_TIME,
    EXPLOSION_DURATION, EXPLOSION_DAMAGE, EXPLOSION_RING_WIDTH,
    PLAYER_FOV_DEGREES,
    VISION_DARKNESS_ALPHA, VISION_LIGHT_ALPHA,
    GUN_LENGTH, GUN_WIDTH,
    MAX_GRENADES, MAX_MEDKITS,
    HP_BAR_POS, HP_BAR_SIZE, AMMO_BOX_ORIGIN, AMMO_BOX_SIZE, AMMO_BOX_GAP,
    RELOAD_GAUGE_POS, RELOAD_GAUGE_SIZE, RELOAD_TEXT_POS,
    INVENTORY_SLOT_COUNT, INVENTORY_SLOT_SIZE, INVENTORY_SLOT_GAP, INVENTORY_ORIGIN,
    INVENTORY_ICON_SIZE,
)


# 初期化、定数

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(WINDOW_TITLE)
clock = pygame.time.Clock()

font = pygame.font.SysFont("arial", 20, bold=True)


# メイン処理

def main():
    grenade_tex = pygame.Surface(INVENTORY_ICON_SIZE, pygame.SRCALPHA)
    pygame.draw.circle(grenade_tex, COLOR_GRENADE_ICON, (24, 24), 20)

    medkit_tex = pygame.Surface(INVENTORY_ICON_SIZE, pygame.SRCALPHA)
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_BODY, (8, 8, 32, 32))
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_CROSS, (20, 12, 8, 24))
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_CROSS, (12, 20, 24, 8))

    walls = [
        pygame.Rect(600, 200, 60, 300),
        pygame.Rect(300, 100, 120, 50),
        pygame.Rect(850, 450, 200, 80)
    ]

    vision = Vision(walls)
    player = Player(PLAYER_START_POS)

    bullets = []
    grenades = []
    explosions = []

    fov = math.radians(PLAYER_FOV_DEGREES)

    while True:
        dt = clock.tick(FPS) / 1000.0

        # イベント処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                # グレネード：１
                if event.key == pygame.K_1:
                    cursor = pygame.mouse.get_pos()
                    thrown = player.try_throw_grenade(cursor)
                    if thrown is not None:
                        center, direction = thrown
                        grenades.append(Grenade(center, direction))

                # 回復：２
                if event.key == pygame.K_2:
                    player.use_medkit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # リロード：マウス右
                if event.button == 3:
                    player.start_reload()

        # キー入力による移動
        keys = pygame.key.get_pressed()
        move = [0.0, 0.0]
        if keys[pygame.K_w]: move[1] -= 1
        if keys[pygame.K_s]: move[1] += 1
        if keys[pygame.K_a]: move[0] -= 1
        if keys[pygame.K_d]: move[0] += 1
        player.move(move, walls, dt)

        # プレイヤーの向きと銃の位置設定
        cursor_pos = pygame.mouse.get_pos()
        player.update_aim(cursor_pos)
        center = player.rect.center
        direction = player.direction

        player.update_cooldowns(dt)

        # 発射
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            fired = player.try_fire()
            if fired is not None:
                muzzle, fire_direction = fired
                bullets.append(Bullet(muzzle, fire_direction))

        # グレネード更新
        for g in grenades:
            g.update(dt)
            if g.exploded:
                explosions.append(Explosion(g.explosion_circle()))
        grenades = [g for g in grenades if not g.exploded]

        # 爆発処理
        for e in explosions:
            if not e.damaged and e.intersects_rect(player.rect):
                player.take_damage(EXPLOSION_DAMAGE)
                e.damaged = True
            e.timer -= dt
        explosions = [e for e in explosions if e.timer > 0]

        # 弾丸更新、壁判定
        for b in bullets:
            b.update(dt)
            b_rect = b.get_rect()
            for w in walls:
                if w.colliderect(b_rect):
                    b.alive = False
        bullets = [b for b in bullets if b.alive]

        # 描画処理
        screen.fill(COLOR_BG)

        # 壁描画
        for w in walls:
            pygame.draw.rect(screen, COLOR_WALL, w)

        # 暗闇用オーバーレイ
        dark_overlay = make_alpha_surface((WIDTH, HEIGHT), fill=(0, 0, 0, VISION_DARKNESS_ALPHA))

        # 視界ポリゴンの作成
        tris = vision.get_triangles(center, direction, fov)
        vision_surf = make_alpha_surface((WIDTH, HEIGHT))
        for t in tris:
            pygame.draw.polygon(vision_surf, (255, 255, 255, VISION_LIGHT_ALPHA), t)

        screen.blit(dark_overlay, (0, 0))
        screen.blit(vision_surf, (0, 0))

        # 視界内にある弾丸を描画
        for b in bullets:
            if b.visible_to(tris):
                b.draw(screen)

        # グレネード描画
        for g in grenades:
            g.draw(screen)

        # 爆発エフェクト描画
        for e in explosions:
            alpha = max(0, int(255 * (e.timer / EXPLOSION_DURATION)))
            exp_surf = make_alpha_surface((WIDTH, HEIGHT))
            pygame.draw.circle(exp_surf, (*COLOR_EXPLOSION, alpha), (int(e.x), int(e.y)), int(e.radius), EXPLOSION_RING_WIDTH)
            screen.blit(exp_surf, (0, 0))

        # プレイヤー描画
        pygame.draw.rect(screen, COLOR_PLAYER, player.rect)

        # 銃描画
        draw_rotated_rect(screen, (GUN_LENGTH, GUN_WIDTH), COLOR_GUN, direction, player.gun_pos)

        # HPバー
        pygame.draw.rect(screen, COLOR_HP_BG, (*HP_BAR_POS, *HP_BAR_SIZE))
        pygame.draw.rect(screen, COLOR_HP_FG, (HP_BAR_POS[0], HP_BAR_POS[1], HP_BAR_SIZE[0] * (player.hp / player.max_hp), HP_BAR_SIZE[1]))

        # マガジン
        for i in range(MAX_AMMO):
            box = pygame.Rect(AMMO_BOX_ORIGIN[0] + i * AMMO_BOX_GAP, AMMO_BOX_ORIGIN[1], *AMMO_BOX_SIZE)
            if i < player.ammo:
                pygame.draw.rect(screen, COLOR_AMMO_FULL, box)
            else:
                pygame.draw.rect(screen, COLOR_AMMO_EMPTY, box, 2)

        # リロードゲージ
        if player.reload:
            rate = max(0.0, min(1.0, 1.0 - (player.reload_time / RELOAD_TIME)))
            pygame.draw.rect(screen, COLOR_RELOAD_BG, (*RELOAD_GAUGE_POS, *RELOAD_GAUGE_SIZE))
            pygame.draw.rect(screen, COLOR_RELOAD_FG, (RELOAD_GAUGE_POS[0], RELOAD_GAUGE_POS[1], RELOAD_GAUGE_SIZE[0] * rate, RELOAD_GAUGE_SIZE[1]))
            txt = font.render("RELOAD", True, COLOR_RELOAD_TEXT)
            screen.blit(txt, RELOAD_TEXT_POS)

        # インベントリ
        for i in range(INVENTORY_SLOT_COUNT):
            slot = pygame.Rect(INVENTORY_ORIGIN[0] + i * INVENTORY_SLOT_GAP, INVENTORY_ORIGIN[1], *INVENTORY_SLOT_SIZE)
            pygame.draw.rect(screen, COLOR_SLOT_BG, slot)
            pygame.draw.rect(screen, COLOR_SLOT_BORDER, slot, 3)

            # アイテム表示
            if i == 0:
                screen.blit(grenade_tex, grenade_tex.get_rect(center=slot.center))
                txt = font.render(str(player.grenade_count), True, COLOR_COUNT_TEXT)
                screen.blit(txt, txt.get_rect(center=(slot.centerx + 18, slot.centery + 18)))

                count_box = pygame.Rect(slot.x + 10, slot.y + 55, 50, 12)
                pygame.draw.rect(screen, COLOR_COUNT_BG, count_box)
                pygame.draw.rect(screen, COLOR_GRENADE_BAR, (count_box.x, count_box.y, 50.0 * player.grenade_count / MAX_GRENADES, 12))

            elif i == 1:
                screen.blit(medkit_tex, medkit_tex.get_rect(center=slot.center))
                txt = font.render(str(player.medkit_count), True, COLOR_COUNT_TEXT)
                screen.blit(txt, txt.get_rect(center=(slot.centerx + 18, slot.centery + 18)))

                count_box = pygame.Rect(slot.x + 10, slot.y + 55, 50, 12)
                pygame.draw.rect(screen, COLOR_COUNT_BG, count_box)
                pygame.draw.rect(screen, COLOR_MEDKIT_BAR, (count_box.x, count_box.y, 50.0 * player.medkit_count / MAX_MEDKITS, 12))

            # スロット番号
            num_txt = font.render(str(i + 1), True, COLOR_SLOT_NUMBER)
            screen.blit(num_txt, (slot.x + 5, slot.y + 5))

        pygame.display.flip()

if __name__ == "__main__":
    main()
