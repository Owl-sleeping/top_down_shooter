import math
import sys
import pygame

from render_utils import make_alpha_surface, draw_rotated_rect
from constants import (
    WIDTH, HEIGHT, FPS, WINDOW_TITLE,
    COLOR_BG, COLOR_WALL, COLOR_PLAYER, COLOR_BULLET, COLOR_GRENADE, COLOR_GUN,
    COLOR_EXPLOSION, COLOR_HP_BG, COLOR_HP_FG, COLOR_AMMO_FULL, COLOR_AMMO_EMPTY,
    COLOR_RELOAD_BG, COLOR_RELOAD_FG, COLOR_RELOAD_TEXT,
    COLOR_SLOT_BG, COLOR_SLOT_BORDER, COLOR_SLOT_NUMBER, COLOR_COUNT_TEXT, COLOR_COUNT_BG,
    COLOR_GRENADE_BAR, COLOR_MEDKIT_BAR,
    COLOR_GRENADE_ICON, COLOR_MEDKIT_ICON_BODY, COLOR_MEDKIT_ICON_CROSS,
    PLAYER_SIZE, PLAYER_SPEED, PLAYER_MAX_HP, MEDKIT_HEAL_AMOUNT, PLAYER_START_POS,
    MAX_AMMO, BULLET_SPEED, BULLET_WIDTH, BULLET_HEIGHT, FIRE_RATE, RELOAD_TIME,
    GRENADE_THROW_SPEED, GRENADE_FRICTION, GRENADE_FUSE_TIME,
    GRENADE_EXPLOSION_RADIUS, GRENADE_VISUAL_RADIUS,
    EXPLOSION_DURATION, EXPLOSION_DAMAGE, EXPLOSION_RING_WIDTH,
    PLAYER_FOV_DEGREES, VISION_RAY_COUNT, VISION_RAY_MAX_LENGTH,
    VISION_DARKNESS_ALPHA, VISION_LIGHT_ALPHA,
    GUN_LENGTH, GUN_WIDTH, GUN_FORWARD_OFFSET, GUN_SIDE_OFFSET, GUN_MUZZLE_OFFSET,
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


# クラス定義

class Vision:
    def __init__(self, walls):
        self.walls = walls

    def ray(self, p, angle):
        ray_end = (
            p[0] + math.cos(angle) * VISION_RAY_MAX_LENGTH,
            p[1] + math.sin(angle) * VISION_RAY_MAX_LENGTH,
        )
        closest_hit = ray_end
        min_dist_sq = VISION_RAY_MAX_LENGTH ** 2

        for w in self.walls:
            # 矩形の4辺の取り出す
            lines = [
                ((w.left, w.top), (w.right, w.top)),
                ((w.right, w.top), (w.right, w.bottom)),
                ((w.right, w.bottom), (w.left, w.bottom)),
                ((w.left, w.bottom), (w.left, w.top))
            ]
            for l_start, l_end in lines:
                hit = self.line_intersection((p, ray_end), (l_start, l_end))
                if hit:
                    dist_sq = (hit[0] - p[0])**2 + (hit[1] - p[1])**2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        closest_hit = hit
        return closest_hit

    @staticmethod
    def line_intersection(line1, line2):
        (x1, y1), (x2, y2) = line1
        (x3, y3), (x4, y4) = line2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return None

    def get_triangles(self, p, direction, fov):
        pts = []
        n = VISION_RAY_COUNT
        half_fov = fov / 2.0
        start_angle = direction - half_fov

        for i in range(n):
            angle = start_angle + (fov * i / (n - 1))
            pts.append(self.ray(p, angle))

        triangles = []
        for i in range(n - 1):
            triangles.append([p, pts[i], pts[i + 1]])
        return triangles


class Bullet:
    def __init__(self, p, angle):
        self.pos = list(p)
        self.angle = angle
        self.speed = BULLET_SPEED
        self.vel = [math.cos(angle) * self.speed, math.sin(angle) * self.speed]
        self.alive = True
        self.width, self.height = BULLET_WIDTH, BULLET_HEIGHT

    def update(self, dt):
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

    def get_rect(self):
        return pygame.Rect(self.pos[0] - 12, self.pos[1] - 3, self.width, self.height)

    def draw(self, surface):
        # 回転した矩形の描画
        draw_rotated_rect(surface, (self.width, self.height), COLOR_BULLET, self.angle, (self.pos[0], self.pos[1]))

    def visible_to(self, triangles):
        # 弾のが視界内にあるか
        px, py = self.pos[0], self.pos[1]
        for tri in triangles:
            if self.point_in_triangle((px, py), tri[0], tri[1], tri[2]):
                return True
        return False

    @staticmethod
    def point_in_triangle(pt, v1, v2, v3):
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign(pt, v1, v2)
        d2 = sign(pt, v2, v3)
        d3 = sign(pt, v3, v1)

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)


class Grenade:
    def __init__(self, p, angle):
        self.pos = list(p)
        self.speed = GRENADE_THROW_SPEED
        self.vel = [math.cos(angle) * self.speed, math.sin(angle) * self.speed]
        self.timer = GRENADE_FUSE_TIME
        self.exploded = False
        self.radius = 150

    def update(self, dt):
        if self.exploded:
            return
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.vel[0] *= GRENADE_FRICTION
        self.vel[1] *= GRENADE_FRICTION

        self.timer -= dt
        if self.timer <= 0:
            self.exploded = True

    def draw(self, surface):
        if not self.exploded:
            pygame.draw.circle(surface, COLOR_GRENADE, (int(self.pos[0]), int(self.pos[1])), GRENADE_VISUAL_RADIUS)

    def explosion_circle(self):
        return (self.pos[0], self.pos[1], self.radius * (2.0 / 3.0))


class Explosion:
    def __init__(self, circle_data):
        self.x, self.y, self.radius = circle_data
        self.timer = EXPLOSION_DURATION
        self.damaged = False

    def intersects_rect(self, rect):
        # 円と矩形の当たり判定
        closest_x = max(rect.left, min(self.x, rect.right))
        closest_y = max(rect.top, min(self.y, rect.bottom))
        dist_x = self.x - closest_x
        dist_y = self.y - closest_y
        return (dist_x**2 + dist_y**2) < (self.radius**2)


# メイン処理

def main():
    grenade_tex = pygame.Surface(INVENTORY_ICON_SIZE, pygame.SRCALPHA)
    pygame.draw.circle(grenade_tex, COLOR_GRENADE_ICON, (24, 24), 20)

    medkit_tex = pygame.Surface(INVENTORY_ICON_SIZE, pygame.SRCALPHA)
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_BODY, (8, 8, 32, 32))
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_CROSS, (20, 12, 8, 24))
    pygame.draw.rect(medkit_tex, COLOR_MEDKIT_ICON_CROSS, (12, 20, 24, 8))

    grenade_count = MAX_GRENADES
    medkit_count = MAX_MEDKITS

    walls = [
        pygame.Rect(600, 200, 60, 300),
        pygame.Rect(300, 100, 120, 50),
        pygame.Rect(850, 450, 200, 80)
    ]

    vision = Vision(walls)
    player_rect = pygame.Rect(PLAYER_START_POS[0], PLAYER_START_POS[1], PLAYER_SIZE, PLAYER_SIZE)

    bullets = []
    grenades = []
    explosions = []

    hp = PLAYER_MAX_HP
    max_hp = PLAYER_MAX_HP
    ammo = MAX_AMMO
    timer = 0.0
    reload = False
    reload_time = 0.0
    reload_max = RELOAD_TIME

    speed = PLAYER_SPEED
    fov = math.radians(PLAYER_FOV_DEGREES)
    fire_rate = FIRE_RATE

    while True:
        dt = clock.tick(FPS) / 1000.0

        # イベント処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                # グレネード：１
                if event.key == pygame.K_1 and grenade_count > 0:
                    grenade_count -= 1
                    center = player_rect.center
                    cursor = pygame.mouse.get_pos()
                    direction = math.atan2(cursor[1] - center[1], cursor[0] - center[0])
                    grenades.append(Grenade(center, direction))

                # 回復：２
                if event.key == pygame.K_2 and medkit_count > 0:
                    medkit_count -= 1
                    hp = min(hp + MEDKIT_HEAL_AMOUNT, max_hp)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # リロード：マウス右
                if event.button == 3 and ammo < MAX_AMMO and not reload:
                    reload = True
                    reload_time = reload_max

        # キー入力による移動
        keys = pygame.key.get_pressed()
        move = [0.0, 0.0]
        if keys[pygame.K_w]: move[1] -= 1
        if keys[pygame.K_s]: move[1] += 1
        if keys[pygame.K_a]: move[0] -= 1
        if keys[pygame.K_d]: move[0] += 1

        if move[0] != 0 or move[1] != 0:
            length = math.hypot(move[0], move[1])
            move[0] = (move[0] / length) * speed * dt
            move[1] = (move[1] / length) * speed * dt

            next_rect = player_rect.move(move[0], move[1])
            hit = any(w.colliderect(next_rect) for w in walls)
            if not hit:
                player_rect = next_rect

        # プレイヤーの向きと銃の位置設定
        center = player_rect.center
        cursor_pos = pygame.mouse.get_pos()
        direction = math.atan2(cursor_pos[1] - center[1], cursor_pos[0] - center[0])

        side = (math.cos(direction + math.radians(90)), math.sin(direction + math.radians(90)))
        gun_pos = (
            center[0] + math.cos(direction) * GUN_FORWARD_OFFSET + side[0] * GUN_SIDE_OFFSET,
            center[1] + math.sin(direction) * GUN_FORWARD_OFFSET + side[1] * GUN_SIDE_OFFSET
        )
        muzzle = (
            gun_pos[0] + math.cos(direction) * GUN_MUZZLE_OFFSET,
            gun_pos[1] + math.sin(direction) * GUN_MUZZLE_OFFSET
        )

        timer -= dt

        # 発射
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0] and timer <= 0 and ammo > 0 and not reload:
            bullets.append(Bullet(muzzle, direction))
            ammo -= 1
            timer = fire_rate

        # グレネード更新
        for g in grenades:
            g.update(dt)
            if g.exploded:
                explosions.append(Explosion(g.explosion_circle()))
        grenades = [g for g in grenades if not g.exploded]

        # 爆発処理
        for e in explosions:
            if not e.damaged and e.intersects_rect(player_rect):
                hp = max(0, hp - EXPLOSION_DAMAGE)
                e.damaged = True
            e.timer -= dt
        explosions = [e for e in explosions if e.timer > 0]

        # リロード処理
        if reload:
            reload_time -= dt
            if reload_time <= 0:
                ammo = MAX_AMMO
                reload = False

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
        pygame.draw.rect(screen, COLOR_PLAYER, player_rect)

        # 銃描画
        draw_rotated_rect(screen, (GUN_LENGTH, GUN_WIDTH), COLOR_GUN, direction, gun_pos)

        # HPバー
        pygame.draw.rect(screen, COLOR_HP_BG, (*HP_BAR_POS, *HP_BAR_SIZE))
        pygame.draw.rect(screen, COLOR_HP_FG, (HP_BAR_POS[0], HP_BAR_POS[1], HP_BAR_SIZE[0] * (hp / max_hp), HP_BAR_SIZE[1]))

        # マガジン
        for i in range(MAX_AMMO):
            box = pygame.Rect(AMMO_BOX_ORIGIN[0] + i * AMMO_BOX_GAP, AMMO_BOX_ORIGIN[1], *AMMO_BOX_SIZE)
            if i < ammo:
                pygame.draw.rect(screen, COLOR_AMMO_FULL, box)
            else:
                pygame.draw.rect(screen, COLOR_AMMO_EMPTY, box, 2)

        # リロードゲージ
        if reload:
            rate = max(0.0, min(1.0, 1.0 - (reload_time / reload_max)))
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
                txt = font.render(str(grenade_count), True, COLOR_COUNT_TEXT)
                screen.blit(txt, txt.get_rect(center=(slot.centerx + 18, slot.centery + 18)))

                count_box = pygame.Rect(slot.x + 10, slot.y + 55, 50, 12)
                pygame.draw.rect(screen, COLOR_COUNT_BG, count_box)
                pygame.draw.rect(screen, COLOR_GRENADE_BAR, (count_box.x, count_box.y, 50.0 * grenade_count / MAX_GRENADES, 12))

            elif i == 1:
                screen.blit(medkit_tex, medkit_tex.get_rect(center=slot.center))
                txt = font.render(str(medkit_count), True, COLOR_COUNT_TEXT)
                screen.blit(txt, txt.get_rect(center=(slot.centerx + 18, slot.centery + 18)))

                count_box = pygame.Rect(slot.x + 10, slot.y + 55, 50, 12)
                pygame.draw.rect(screen, COLOR_COUNT_BG, count_box)
                pygame.draw.rect(screen, COLOR_MEDKIT_BAR, (count_box.x, count_box.y, 50.0 * medkit_count / MAX_MEDKITS, 12))

            # スロット番号
            num_txt = font.render(str(i + 1), True, COLOR_SLOT_NUMBER)
            screen.blit(num_txt, (slot.x + 5, slot.y + 5))

        pygame.display.flip()

if __name__ == "__main__":
    main()
