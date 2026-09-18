"""プレイヤーの状態（位置・HP・弾薬・所持品）と振る舞いを表すクラス。"""

import math
import pygame

from constants import (
    PLAYER_SIZE, PLAYER_SPEED, PLAYER_MAX_HP, MEDKIT_HEAL_AMOUNT,
    MAX_AMMO, FIRE_RATE, RELOAD_TIME,
    MAX_GRENADES, MAX_MEDKITS,
    GUN_FORWARD_OFFSET, GUN_SIDE_OFFSET, GUN_MUZZLE_OFFSET,
)


class Player:
    def __init__(self, pos):
        self.rect = pygame.Rect(pos[0], pos[1], PLAYER_SIZE, PLAYER_SIZE)
        self.speed = PLAYER_SPEED

        self.max_hp = PLAYER_MAX_HP
        self.hp = PLAYER_MAX_HP

        self.ammo = MAX_AMMO
        self.fire_timer = 0.0
        self.reload = False
        self.reload_time = 0.0

        self.grenade_count = MAX_GRENADES
        self.medkit_count = MAX_MEDKITS

        self.direction = 0.0
        self.gun_pos = self.rect.center
        self.muzzle = self.rect.center

    @property
    def is_dead(self):
        return self.hp <= 0

    def move(self, move_dir, walls, dt):
        """move_dirは(x, y)の入力方向(正規化前)。壁に当たった軸だけ移動を止め、
        直交する軸には引き続き移動できるようにする(壁沿いのスライド移動)。"""
        dx, dy = move_dir
        if dx == 0 and dy == 0:
            return

        length = math.hypot(dx, dy)
        dx = (dx / length) * self.speed * dt
        dy = (dy / length) * self.speed * dt

        self.rect.x += dx
        for w in walls:
            if self.rect.colliderect(w):
                if dx > 0:
                    self.rect.right = w.left
                elif dx < 0:
                    self.rect.left = w.right

        self.rect.y += dy
        for w in walls:
            if self.rect.colliderect(w):
                if dy > 0:
                    self.rect.bottom = w.top
                elif dy < 0:
                    self.rect.top = w.bottom

    def update_aim(self, cursor_pos):
        center = self.rect.center
        self.direction = math.atan2(cursor_pos[1] - center[1], cursor_pos[0] - center[0])

        side = (math.cos(self.direction + math.radians(90)), math.sin(self.direction + math.radians(90)))
        self.gun_pos = (
            center[0] + math.cos(self.direction) * GUN_FORWARD_OFFSET + side[0] * GUN_SIDE_OFFSET,
            center[1] + math.sin(self.direction) * GUN_FORWARD_OFFSET + side[1] * GUN_SIDE_OFFSET
        )
        self.muzzle = (
            self.gun_pos[0] + math.cos(self.direction) * GUN_MUZZLE_OFFSET,
            self.gun_pos[1] + math.sin(self.direction) * GUN_MUZZLE_OFFSET
        )

    def update_cooldowns(self, dt):
        self.fire_timer -= dt
        if self.reload:
            self.reload_time -= dt
            if self.reload_time <= 0:
                self.ammo = MAX_AMMO
                self.reload = False

    def try_fire(self):
        """発射条件を満たしていれば(銃口位置, 向き)を返し内部状態を消費する。満たさなければNone。"""
        if self.fire_timer <= 0 and self.ammo > 0 and not self.reload:
            self.ammo -= 1
            self.fire_timer = FIRE_RATE
            return (self.muzzle, self.direction)
        return None

    def start_reload(self):
        if self.ammo < MAX_AMMO and not self.reload:
            self.reload = True
            self.reload_time = RELOAD_TIME

    def try_throw_grenade(self, cursor_pos):
        """投擲条件を満たしていれば(発射位置, 向き)を返し内部状態を消費する。満たさなければNone。"""
        if self.grenade_count > 0:
            self.grenade_count -= 1
            center = self.rect.center
            direction = math.atan2(cursor_pos[1] - center[1], cursor_pos[0] - center[0])
            return (center, direction)
        return None

    def use_medkit(self):
        if self.medkit_count > 0:
            self.medkit_count -= 1
            self.hp = min(self.hp + MEDKIT_HEAL_AMOUNT, self.max_hp)

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
