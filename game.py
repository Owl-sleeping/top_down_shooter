"""ゲームの状態保持とメインループのオーケストレーションを担うモジュール。"""

import math
import sys
import pygame

from render_utils import make_alpha_surface, draw_rotated_rect
from vision import Vision
from entities import Bullet, Grenade, Explosion
from player import Player
from hud import create_item_textures, draw_hud
from constants import (
    WIDTH, HEIGHT, FPS,
    COLOR_BG, COLOR_WALL, COLOR_PLAYER, COLOR_GUN, COLOR_EXPLOSION,
    COLOR_GAME_OVER_TEXT, GAME_OVER_FONT_SIZE,
    PLAYER_START_POS,
    EXPLOSION_DURATION, EXPLOSION_DAMAGE, EXPLOSION_RING_WIDTH,
    BULLET_DESPAWN_MARGIN,
    PLAYER_FOV_DEGREES,
    VISION_DARKNESS_ALPHA, VISION_LIGHT_ALPHA,
    GUN_LENGTH, GUN_WIDTH,
)


class Game:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> None:
        self.screen = screen
        self.clock = clock
        self.font = font
        self.game_over_font = pygame.font.SysFont("arial", GAME_OVER_FONT_SIZE, bold=True)

        self.item_textures = create_item_textures()

        self.walls = [
            pygame.Rect(600, 200, 60, 300),
            pygame.Rect(300, 100, 120, 50),
            pygame.Rect(850, 450, 200, 80)
        ]

        self.vision = Vision(self.walls)
        self.player = Player(PLAYER_START_POS)

        self.bullets = []
        self.grenades = []
        self.explosions = []

        self.fov = math.radians(PLAYER_FOV_DEGREES)
        self.tris = []
        self.game_over = False

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if not self.game_over:
                self.handle_input(dt)
                self.update(dt)
                self.handle_collisions()
                if self.player.is_dead:
                    self.game_over = True
            self.draw()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                # ESCキーで終了
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                # グレネード：１
                if event.key == pygame.K_1:
                    cursor = pygame.mouse.get_pos()
                    thrown = self.player.try_throw_grenade(cursor)
                    if thrown is not None:
                        center, direction = thrown
                        self.grenades.append(Grenade(center, direction))

                # 回復：２
                if event.key == pygame.K_2:
                    self.player.use_medkit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # リロード：マウス右
                if event.button == 3:
                    self.player.start_reload()

    def handle_input(self, dt: float) -> None:
        # キー入力による移動
        keys = pygame.key.get_pressed()
        move = [0.0, 0.0]
        if keys[pygame.K_w]: move[1] -= 1
        if keys[pygame.K_s]: move[1] += 1
        if keys[pygame.K_a]: move[0] -= 1
        if keys[pygame.K_d]: move[0] += 1
        self.player.move(move, self.walls, dt)

        # プレイヤーの向きと銃の位置設定
        cursor_pos = pygame.mouse.get_pos()
        self.player.update_aim(cursor_pos)

        self.player.update_cooldowns(dt)

        # 発射
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            fired = self.player.try_fire()
            if fired is not None:
                muzzle, direction = fired
                self.bullets.append(Bullet(muzzle, direction))

    def update(self, dt: float) -> None:
        # グレネード更新
        for g in self.grenades:
            g.update(dt)
            if g.exploded:
                self.explosions.append(Explosion(g.explosion_circle()))
        self.grenades = [g for g in self.grenades if not g.exploded]

        # 爆発タイマー更新
        for e in self.explosions:
            e.timer -= dt

        # 弾丸移動
        for b in self.bullets:
            b.update(dt)

    def handle_collisions(self) -> None:
        # 爆発 vs プレイヤー
        for e in self.explosions:
            if not e.damaged and e.intersects_rect(self.player.rect):
                self.player.take_damage(EXPLOSION_DAMAGE)
                e.damaged = True
        self.explosions = [e for e in self.explosions if e.timer > 0]

        # 弾丸 vs 壁、および画面外への消滅判定
        despawn_bounds = pygame.Rect(
            -BULLET_DESPAWN_MARGIN, -BULLET_DESPAWN_MARGIN,
            WIDTH + BULLET_DESPAWN_MARGIN * 2, HEIGHT + BULLET_DESPAWN_MARGIN * 2
        )
        for b in self.bullets:
            b_rect = b.get_rect()
            if not despawn_bounds.collidepoint(b.pos):
                b.alive = False
                continue
            for w in self.walls:
                if w.colliderect(b_rect):
                    b.alive = False
        self.bullets = [b for b in self.bullets if b.alive]

    def draw(self) -> None:
        screen = self.screen
        player = self.player
        center = player.rect.center
        direction = player.direction

        screen.fill(COLOR_BG)

        # 壁描画
        for w in self.walls:
            pygame.draw.rect(screen, COLOR_WALL, w)

        # 暗闇用オーバーレイ
        dark_overlay = make_alpha_surface((WIDTH, HEIGHT), fill=(0, 0, 0, VISION_DARKNESS_ALPHA))

        # 視界ポリゴンの作成
        self.tris = self.vision.get_triangles(center, direction, self.fov)
        vision_surf = make_alpha_surface((WIDTH, HEIGHT))
        for t in self.tris:
            pygame.draw.polygon(vision_surf, (255, 255, 255, VISION_LIGHT_ALPHA), t)

        screen.blit(dark_overlay, (0, 0))
        screen.blit(vision_surf, (0, 0))

        # 視界内にある弾丸を描画
        for b in self.bullets:
            if b.visible_to(self.tris):
                b.draw(screen)

        # グレネード描画
        for g in self.grenades:
            g.draw(screen)

        # 爆発エフェクト描画
        for e in self.explosions:
            alpha = max(0, int(255 * (e.timer / EXPLOSION_DURATION)))
            exp_surf = make_alpha_surface((WIDTH, HEIGHT))
            pygame.draw.circle(exp_surf, (*COLOR_EXPLOSION, alpha), (int(e.x), int(e.y)), int(e.radius), EXPLOSION_RING_WIDTH)
            screen.blit(exp_surf, (0, 0))

        # プレイヤー描画
        pygame.draw.rect(screen, COLOR_PLAYER, player.rect)

        # 銃描画
        draw_rotated_rect(screen, (GUN_LENGTH, GUN_WIDTH), COLOR_GUN, direction, player.gun_pos)

        draw_hud(screen, self.font, player, self.item_textures)

        if self.game_over:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_game_over(self) -> None:
        txt = self.game_over_font.render("GAME OVER", True, COLOR_GAME_OVER_TEXT)
        self.screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
