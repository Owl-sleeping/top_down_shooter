import math
import sys
import pygame


# 初期化、定数

pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Top-down Shooter (Pygame Port)")
clock = pygame.time.Clock()


# 色定義

COLOR_BG = (5, 8, 13)
COLOR_WALL = (128, 140, 153)
COLOR_PLAYER = (255, 255, 255)
COLOR_BULLET = (255, 255, 0)
COLOR_GRENADE = (255, 165, 0)
COLOR_GUN = (13, 13, 13)
font = pygame.font.SysFont("arial", 20, bold=True)


# クラス定義

class Vision:
    def __init__(self, walls):
        self.walls = walls

    def ray(self, p, angle):
        ray_end = (p[0] + math.cos(angle) * 2000, p[1] + math.sin(angle) * 2000)
        closest_hit = ray_end
        min_dist_sq = 2000 ** 2

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
        n = 80
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
        self.speed = 800
        self.vel = [math.cos(angle) * self.speed, math.sin(angle) * self.speed]
        self.alive = True
        self.width, self.height = 24, 6

    def update(self, dt):
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

    def get_rect(self):
        return pygame.Rect(self.pos[0] - 12, self.pos[1] - 3, self.width, self.height)

    def draw(self, surface):
        # 回転した矩形の描画
        rect_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        rect_surf.fill(COLOR_BULLET)
        rotated_surf = pygame.transform.rotate(rect_surf, -math.degrees(self.angle))
        new_rect = rotated_surf.get_rect(center=(self.pos[0], self.pos[1]))
        surface.blit(rotated_surf, new_rect.topleft)

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
        self.speed = 500
        self.vel = [math.cos(angle) * self.speed, math.sin(angle) * self.speed]
        self.timer = 1.2
        self.exploded = False
        self.radius = 150

    def update(self, dt):
        if self.exploded:
            return
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.vel[0] *= 0.98
        self.vel[1] *= 0.98

        self.timer -= dt
        if self.timer <= 0:
            self.exploded = True

    def draw(self, surface):
        if not self.exploded:
            pygame.draw.circle(surface, COLOR_GRENADE, (int(self.pos[0]), int(self.pos[1])), 6)

    def explosion_circle(self):
        return (self.pos[0], self.pos[1], self.radius * (2.0 / 3.0))


class Explosion:
    def __init__(self, circle_data):
        self.x, self.y, self.radius = circle_data
        self.timer = 2.0
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
    grenade_tex = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(grenade_tex, (255, 140, 0), (24, 24), 20)
    
    medkit_tex = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.rect(medkit_tex, (0, 200, 100), (8, 8, 32, 32))
    pygame.draw.rect(medkit_tex, (255, 255, 255), (20, 12, 8, 24))
    pygame.draw.rect(medkit_tex, (255, 255, 255), (12, 20, 24, 8))

    grenade_count = 3
    medkit_count = 2

    walls = [
        pygame.Rect(600, 200, 60, 300),
        pygame.Rect(300, 100, 120, 50),
        pygame.Rect(850, 450, 200, 80)
    ]

    vision = Vision(walls)
    player_rect = pygame.Rect(200, 360, 36, 36)

    bullets = []
    grenades = []
    explosions = []

    hp = 20
    max_hp = 20
    ammo = 10
    timer = 0.0
    reload = False
    reload_time = 0.0
    reload_max = 1.5

    speed = 400.0
    fov = math.radians(60)
    fire_rate = 0.12

    while True:
        dt = clock.tick(60) / 1000.0

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
                    hp = min(hp + 5, max_hp)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # リロード：マウス右
                if event.button == 3 and ammo < 10 and not reload:
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
            center[0] + math.cos(direction) * 20 + side[0] * 15,
            center[1] + math.sin(direction) * 20 + side[1] * 15
        )
        muzzle = (
            gun_pos[0] + math.cos(direction) * 30,
            gun_pos[1] + math.sin(direction) * 30
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
                hp = max(0, hp - 5)
                e.damaged = True
            e.timer -= dt
        explosions = [e for e in explosions if e.timer > 0]

        # リロード処理
        if reload:
            reload_time -= dt
            if reload_time <= 0:
                ammo = 10
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
        dark_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 217)) # 0.85 * 255 ≈ 217

        # 視界ポリゴンの作成
        tris = vision.get_triangles(center, direction, fov)
        vision_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for t in tris:
            pygame.draw.polygon(vision_surf, (255, 255, 255, 90), t)
        
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
            alpha = max(0, int(255 * (e.timer / 2.0)))
            exp_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(exp_surf, (255, 76, 25, alpha), (int(e.x), int(e.y)), int(e.radius), 10)
            screen.blit(exp_surf, (0, 0))

        # プレイヤー描画
        pygame.draw.rect(screen, COLOR_PLAYER, player_rect)

        # 銃描画
        gun_surf = pygame.Surface((50, 12), pygame.SRCALPHA)
        gun_surf.fill(COLOR_GUN)
        rotated_gun = pygame.transform.rotate(gun_surf, -math.degrees(direction))
        gun_rect = rotated_gun.get_rect(center=gun_pos)
        screen.blit(rotated_gun, gun_rect.topleft)

        # HPバー
        pygame.draw.rect(screen, (204, 25, 25), (20, 20, 250, 20))
        pygame.draw.rect(screen, (25, 255, 25), (20, 20, 250 * (hp / max_hp), 20))

        # マガジン
        for i in range(10):
            box = pygame.Rect(20 + i * 25, 60, 18, 30)
            if i < ammo:
                pygame.draw.rect(screen, (255, 204, 0), box)
            else:
                pygame.draw.rect(screen, (128, 128, 128), box, 2)

        # リロードゲージ
        if reload:
            rate = max(0.0, min(1.0, 1.0 - (reload_time / reload_max)))
            pygame.draw.rect(screen, (50, 50, 50), (20, 110, 200, 10))
            pygame.draw.rect(screen, (50, 255, 50), (20, 110, 200 * rate, 10))
            txt = font.render("RELOAD", True, (255, 255, 255))
            screen.blit(txt, (230, 105))

        # インベントリ
        for i in range(3):
            slot = pygame.Rect(900 + i * 90, 600, 70, 70)
            pygame.draw.rect(screen, (25, 25, 25), slot)
            pygame.draw.rect(screen, (200, 200, 200), slot, 3)

            # アイテム表示
            if i == 0:
                screen.blit(grenade_tex, grenade_tex.get_rect(center=slot.center))
                txt = font.render(str(grenade_count), True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=(slot.centerx + 18, slot.centery + 18)))
                
                count_box = pygame.Rect(slot.x + 10, slot.y + 55, 50, 12)
                pygame.draw.rect(screen, (50, 50, 50), count_box)
                pygame.draw.rect(screen, (255, 153, 0), (count_box.x, count_box.y, 50.0 * grenade_count / 3.0, 12))

            elif i == 1:
                screen.blit(medkit_tex, medkit_tex.get_rect(center=slot.center))
                txt = font.render(str(medkit_count), True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=(slot.centerx + 18, slot.centery + 18)))
                
                count_box = pygame.Rect(slot.x + 10, slot.y + 55, 50, 12)
                pygame.draw.rect(screen, (50, 50, 50), count_box)
                pygame.draw.rect(screen, (50, 255, 76), (count_box.x, count_box.y, 50.0 * medkit_count / 2.0, 12))

            # スロット番号
            num_txt = font.render(str(i + 1), True, (150, 150, 150))
            screen.blit(num_txt, (slot.x + 5, slot.y + 5))

        pygame.display.flip()

if __name__ == "__main__":
    main()