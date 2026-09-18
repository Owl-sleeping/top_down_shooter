"""ゲームの状態保持とメインループのオーケストレーションを担うモジュール。"""

import math
import sys
import pygame

from frontend.render_utils import make_alpha_surface, draw_rotated_rect
from frontend.vision import Vision, is_point_visible
from backend.entities import Bullet, Grenade, Explosion
from backend.player import Player
from backend.maps import GameMap, MAPS
from frontend.hud import create_item_textures, draw_hud
from backend.network import Connection
from constants import (
    WIDTH, HEIGHT, FPS,
    COLOR_BG, COLOR_WALL, COLOR_PLAYER, COLOR_ENEMY_PLAYER, COLOR_GUN, COLOR_EXPLOSION,
    COLOR_GAME_OVER_TEXT, GAME_OVER_FONT_SIZE,
    EXPLOSION_DURATION, EXPLOSION_DAMAGE, EXPLOSION_RING_WIDTH,
    BULLET_DESPAWN_MARGIN, BULLET_DAMAGE,
    PLAYER_FOV_DEGREES,
    VISION_DARKNESS_ALPHA, VISION_LIGHT_ALPHA,
    GUN_LENGTH, GUN_WIDTH,
)


class Game:
    def __init__(
        self,
        screen: pygame.Surface,
        clock: pygame.time.Clock,
        font: pygame.font.Font,
        mode: str = "solo",
        connection: Connection | None = None,
        local_id: int = 0,
        game_map: GameMap | None = None,
    ) -> None:
        self.screen = screen
        self.clock = clock
        self.font = font
        self.game_over_font = pygame.font.SysFont("arial", GAME_OVER_FONT_SIZE, bold=True)

        self.mode = mode  # "solo" | "host" | "client"
        self.connection = connection
        self.local_id = local_id
        self.remote_input = {"move": (0.0, 0.0), "cursor": (0, 0), "fire": False}

        self.item_textures = create_item_textures()

        self.game_map = game_map or MAPS[0]
        self.walls = self.game_map.build_wall_rects()

        self.vision = Vision(self.walls)

        self.fov = math.radians(PLAYER_FOV_DEGREES)
        self.tris = []
        self.disconnected = False

        self._reset_round_state()

    def _reset_round_state(self) -> None:
        """1試合分の状態(プレイヤー・弾・グレネード・爆発・勝敗)を初期化する。
        壁配置やネットワーク接続など、試合をまたいで保持すべきものには触れない。"""
        self.players: dict[int, Player] = {0: Player(self.game_map.spawn_positions[0])}
        if self.mode != "solo":
            self.players[1] = Player(self.game_map.spawn_positions[1])

        self.bullets: list[Bullet] = []
        self.grenades: list[Grenade] = []
        self.explosions: list[Explosion] = []

        self.game_over = False
        self.winner_id = None

    def restart(self) -> None:
        """リマッチ。ソロ/ホストはその場で試合状態をリセットする
        (ホストならこの直後に送られるスナップショットでクライアントにも反映される)。"""
        self._reset_round_state()

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()

            if self.connection is not None and not self.connection.connected:
                self.disconnected = True

            if self.disconnected:
                self.draw()
                continue

            self._poll_network()

            if self.mode == "client":
                self.handle_input(dt)
            else:
                if not self.game_over:
                    self.handle_input(dt)
                    self.update(dt)
                    self.handle_collisions()
                    if any(p.is_dead for p in self.players.values()):
                        self.game_over = True
                        self._determine_winner()
                if self.mode == "host":
                    self.connection.send(self.build_snapshot())

            self.draw()

    def _quit(self) -> None:
        if self.connection is not None:
            self.connection.close()
        pygame.quit()
        sys.exit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            elif event.type == pygame.KEYDOWN:
                # ESCキーで終了
                if event.key == pygame.K_ESCAPE:
                    self._quit()

                # グレネード：１（一時的に無効化）
                # if event.key == pygame.K_1:
                #     self._trigger_action("grenade")

                # 回復：２
                if event.key == pygame.K_2:
                    self._trigger_action("medkit")

                # リマッチ：R（ゲーム終了後のみ）
                if event.key == pygame.K_r and self.game_over and not self.disconnected:
                    self._trigger_rematch()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # リロード：マウス右
                if event.button == 3:
                    self._trigger_action("reload")

    def _trigger_action(self, action: str) -> None:
        """グレネード投擲・回復・リロードのような単発アクション。
        クライアントはホストへ送信するだけで、実際の適用はホスト側でのみ行う。"""
        if self.mode == "client":
            self.connection.send({"type": "action", "action": action})
        else:
            cursor = pygame.mouse.get_pos()
            self._apply_action(self.local_id, self.players[self.local_id], action, cursor)

    def _trigger_rematch(self) -> None:
        """リマッチ要求。ホスト権威なので、クライアントは要求を送るだけでホストが実際にリセットする。"""
        if self.mode == "client":
            self.connection.send({"type": "action", "action": "rematch"})
        else:
            self.restart()

    def _apply_action(self, pid: int, player: Player, action: str, cursor: tuple[int, int]) -> None:
        if action == "grenade":
            thrown = player.try_throw_grenade(cursor)
            if thrown is not None:
                center, direction = thrown
                self.grenades.append(Grenade(center, direction, owner_id=pid))
        elif action == "medkit":
            player.use_medkit()
        elif action == "reload":
            player.start_reload()

    def _poll_network(self) -> None:
        if self.connection is None:
            return
        for msg in self.connection.poll():
            msg_type = msg.get("type")
            if self.mode == "host":
                if msg_type == "input":
                    self.remote_input["move"] = tuple(msg["move"])
                    self.remote_input["cursor"] = tuple(msg["cursor"])
                    self.remote_input["fire"] = bool(msg["fire"])
                elif msg_type == "action":
                    if msg["action"] == "rematch":
                        if self.game_over:
                            self.restart()
                    else:
                        cursor = tuple(self.remote_input["cursor"])
                        self._apply_action(1, self.players[1], msg["action"], cursor)
            elif self.mode == "client":
                if msg_type == "snapshot":
                    self.apply_snapshot(msg)

    def _read_local_input(self) -> tuple[list[float], tuple[int, int], bool]:
        keys = pygame.key.get_pressed()
        move = [0.0, 0.0]
        if keys[pygame.K_w]: move[1] -= 1
        if keys[pygame.K_s]: move[1] += 1
        if keys[pygame.K_a]: move[0] -= 1
        if keys[pygame.K_d]: move[0] += 1
        cursor = pygame.mouse.get_pos()
        fire_held = pygame.mouse.get_pressed()[0]
        return move, cursor, fire_held

    def handle_input(self, dt: float) -> None:
        if self.mode == "client":
            move, cursor, fire_held = self._read_local_input()
            self.connection.send({
                "type": "input",
                "move": list(move),
                "cursor": list(cursor),
                "fire": bool(fire_held),
            })
            return

        move, cursor, fire_held = self._read_local_input()
        self._apply_continuous_input(self.local_id, self.players[self.local_id], move, cursor, fire_held, dt)

        if self.mode == "host":
            remote = self.players[1]
            self._apply_continuous_input(
                1, remote, self.remote_input["move"], self.remote_input["cursor"], self.remote_input["fire"], dt
            )

    def _apply_continuous_input(
        self, pid: int, player: Player, move: tuple[float, float], cursor: tuple[int, int], fire_held: bool, dt: float
    ) -> None:
        player.move(move, self.walls, dt)
        player.update_aim(cursor)
        player.update_cooldowns(dt)

        if fire_held:
            fired = player.try_fire()
            if fired is not None:
                muzzle, direction = fired
                self.bullets.append(Bullet(muzzle, direction, owner_id=pid))

    def update(self, dt: float) -> None:
        # グレネード更新
        for g in self.grenades:
            g.update(dt)
            if g.exploded:
                self.explosions.append(Explosion(g.explosion_circle(), owner_id=g.owner_id))
        self.grenades = [g for g in self.grenades if not g.exploded]

        # 爆発タイマー更新
        for e in self.explosions:
            e.timer -= dt

        # 弾丸移動
        for b in self.bullets:
            b.update(dt)

    def build_snapshot(self) -> dict:
        """ホストが毎フレーム構築し、クライアントへ送る状態のスナップショット。"""
        return {
            "type": "snapshot",
            "players": {
                str(pid): {
                    "pos": list(p.rect.center),
                    "hp": p.hp,
                    "max_hp": p.max_hp,
                    "ammo": p.ammo,
                    "reload": p.reload,
                    "reload_time": p.reload_time,
                    "grenade_count": p.grenade_count,
                    "medkit_count": p.medkit_count,
                    "direction": p.direction,
                    "gun_pos": list(p.gun_pos),
                    "muzzle": list(p.muzzle),
                }
                for pid, p in self.players.items()
            },
            "bullets": [
                {"pos": [b.pos.x, b.pos.y], "angle": b.angle, "owner": b.owner_id}
                for b in self.bullets
            ],
            "grenades": [
                {"pos": [g.pos.x, g.pos.y], "exploded": g.exploded, "owner": g.owner_id}
                for g in self.grenades
            ],
            "explosions": [
                {"x": e.x, "y": e.y, "radius": e.radius, "timer": e.timer, "owner": e.owner_id}
                for e in self.explosions
            ],
            "game_over": self.game_over,
            "winner": self.winner_id,
        }

    def apply_snapshot(self, msg: dict) -> None:
        """クライアントが受信したスナップショットで自分の状態を上書きする。
        物理は一切実行せず、既存のPlayer/Bullet/Grenade/Explosionを描画用の器として再利用する。"""
        for pid_str, pdata in msg["players"].items():
            pid = int(pid_str)
            fallback_pos = self.game_map.spawn_positions.get(pid, (0, 0))
            player = self.players.setdefault(pid, Player(fallback_pos))
            player.rect.center = pdata["pos"]
            player.hp = pdata["hp"]
            player.max_hp = pdata["max_hp"]
            player.ammo = pdata["ammo"]
            player.reload = pdata["reload"]
            player.reload_time = pdata["reload_time"]
            player.grenade_count = pdata["grenade_count"]
            player.medkit_count = pdata["medkit_count"]
            player.direction = pdata["direction"]
            player.gun_pos = tuple(pdata["gun_pos"])
            player.muzzle = tuple(pdata["muzzle"])

        self.bullets = [Bullet(b["pos"], b["angle"], b["owner"]) for b in msg["bullets"]]

        grenades = []
        for g in msg["grenades"]:
            grenade = Grenade(g["pos"], 0.0, g["owner"])
            grenade.exploded = g["exploded"]
            grenades.append(grenade)
        self.grenades = grenades

        explosions = []
        for e in msg["explosions"]:
            explosion = Explosion((e["x"], e["y"], e["radius"]), e["owner"])
            explosion.timer = e["timer"]
            explosions.append(explosion)
        self.explosions = explosions

        self.game_over = msg["game_over"]
        self.winner_id = msg["winner"]

    def handle_collisions(self) -> None:
        # 爆発 vs 全プレイヤー
        for e in self.explosions:
            for pid, p in self.players.items():
                if pid not in e.damaged_ids and e.intersects_rect(p.rect):
                    p.take_damage(EXPLOSION_DAMAGE)
                    e.damaged_ids.add(pid)
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
            if not b.alive:
                continue
            # 弾 vs 敵プレイヤー（発射者自身には当たらない）
            for pid, p in self.players.items():
                if pid == b.owner_id:
                    continue
                if b_rect.colliderect(p.rect):
                    p.take_damage(BULLET_DAMAGE)
                    b.alive = False
                    break
        self.bullets = [b for b in self.bullets if b.alive]

    def draw(self) -> None:
        screen = self.screen
        local_player = self.players[self.local_id]
        center = local_player.rect.center
        direction = local_player.direction

        screen.fill(COLOR_BG)

        # 壁描画
        for w in self.walls:
            pygame.draw.rect(screen, COLOR_WALL, w)

        # 暗闇用オーバーレイ
        dark_overlay = make_alpha_surface((WIDTH, HEIGHT), fill=(0, 0, 0, VISION_DARKNESS_ALPHA))

        # 視界ポリゴンの作成（自分視点のみ）
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

        # 自分は常に描画
        pygame.draw.rect(screen, COLOR_PLAYER, local_player.rect)
        draw_rotated_rect(screen, (GUN_LENGTH, GUN_WIDTH), COLOR_GUN, local_player.direction, local_player.gun_pos)

        # 敵は自分の視界(FOV三角形)内にいる時だけ描画する
        enemy = next((p for pid, p in self.players.items() if pid != self.local_id), None)
        enemy_visible = enemy is not None and is_point_visible(enemy.rect.center, self.tris)
        if enemy_visible:
            pygame.draw.rect(screen, COLOR_ENEMY_PLAYER, enemy.rect)
            draw_rotated_rect(screen, (GUN_LENGTH, GUN_WIDTH), COLOR_GUN, enemy.direction, enemy.gun_pos)

        draw_hud(screen, self.font, local_player, self.item_textures, enemy=enemy if enemy_visible else None)

        if self.disconnected:
            self._draw_disconnected()
        elif self.game_over:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_disconnected(self) -> None:
        txt = self.game_over_font.render("CONNECTION LOST", True, COLOR_GAME_OVER_TEXT)
        self.screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    def _determine_winner(self) -> None:
        if len(self.players) < 2:
            return
        survivors = [pid for pid, p in self.players.items() if not p.is_dead]
        self.winner_id = survivors[0] if len(survivors) == 1 else None

    def _draw_game_over(self) -> None:
        if len(self.players) < 2:
            text = "GAME OVER"
        elif self.winner_id is None:
            text = "DRAW"
        elif self.winner_id == self.local_id:
            text = "YOU WIN"
        else:
            text = "YOU LOSE"

        txt = self.game_over_font.render(text, True, COLOR_GAME_OVER_TEXT)
        self.screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        hint = self.font.render("Press R to rematch", True, COLOR_PLAYER)
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + GAME_OVER_FONT_SIZE)))
