"""武器の定義。"""


class Weapon:
    def __init__(
        self,
        name: str,
        image_filename: str,
        held_image_filename: str,
        magazine_size: int,
        fire_rate: float,
        reload_time: float,
        bullet_speed: float,
        bullet_damage: int,
        pellet_count: int,
        spread_degrees: float,
        bullet_range: float,
    ) -> None:
        self.name = name
        self.image_filename = image_filename
        self.held_image_filename = held_image_filename  # 画像
        self.magazine_size = magazine_size
        self.fire_rate = fire_rate            # 発射クールダウン
        self.reload_time = reload_time        # リロードにかかる時間
        self.bullet_speed = bullet_speed      # 弾速
        self.bullet_damage = bullet_damage    # 1発あたりの威力
        self.pellet_count = pellet_count      # 1トリガーで発射される弾の数
        self.spread_degrees = spread_degrees  # 弾のばらけ角度
        self.bullet_range = bullet_range      # 発射地点からこの距離を超えると弾が消える


# 各武器のステータス。
WEAPONS: list[Weapon] = [
    Weapon(
        name="AKS74U",
        image_filename="AKS74U.png",
        held_image_filename="AKS74U_up.png",
        magazine_size=30,
        fire_rate=0.12,      # 速度:中
        reload_time=1.8,
        bullet_speed=900,
        bullet_damage=20,    # 威力20
        pellet_count=1,
        spread_degrees=4,    # 収束:低
        bullet_range=833,
    ),
    Weapon(
        name="M870",
        image_filename="M870.png",
        held_image_filename="M870_up.png",
        magazine_size=8,     # 弾8
        fire_rate=0.6,       # 速度:低
        reload_time=2.5,
        bullet_speed=700,
        bullet_damage=10,    # 5発の散弾で合計威力50
        pellet_count=5,      # 5発の散弾
        spread_degrees=25,   # 散弾の広がり
        bullet_range=250,
    ),
    Weapon(
        name="M700",
        image_filename="M700.png",
        held_image_filename="M700_up.png",
        magazine_size=5,     # 弾5
        fire_rate=1.5,       # 激遅い
        reload_time=2.2,
        bullet_speed=1400,
        bullet_damage=70,    # 高威力
        pellet_count=1,
        spread_degrees=0,    # 精密射撃、ばらけない
        bullet_range=1900,   # 最長の射程
    ),
    Weapon(
        name="MP5K",
        image_filename="MP5K.png",
        held_image_filename="MP5K_up.png",
        magazine_size=25,    # 弾25
        fire_rate=0.08,      # 最速の連射速度
        reload_time=1.4,
        bullet_speed=850,
        bullet_damage=8,     # 1発は弱いが連射でカバー
        pellet_count=1,
        spread_degrees=5,
        bullet_range=700,    # 中距離
    ),
]


def get_weapon_by_name(name: str) -> Weapon:
    return next((w for w in WEAPONS if w.name == name), WEAPONS[0])
