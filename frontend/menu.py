"""起動時のモード選択・接続確立を行う簡易メニュー画面。"""

import pygame

from backend import relay_connection
from backend.relay_connection import RelayConnection
from backend.maps import GameMap, MAPS, get_map_by_name
from backend.weapons import Weapon, WEAPONS, get_weapon_by_name
from frontend.weapon_sprites import load_weapon_portraits
from frontend.hud import create_weapon_icon_frame
from constants import WIDTH, HEIGHT, RELAY_URL, COLOR_BG, COLOR_PLAYER, WEAPON_ICON_FRAME_SIZE

# "arial"はCJKグリフを持たないため、日本語表示にはIME非依存で日本語Windowsに
# 標準搭載されているYu Gothicを使う(HUDの英語表示用フォントとは別に用意する)。
_MENU_FONT_NAME = "yugothic"
_LINE_HEIGHT = 28


def run_menu(
    screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font
) -> tuple[str, RelayConnection | None, int, GameMap, dict[int, Weapon]]:
    """[1]ローカルプレイ [2]ルームを作る [3]ルームに参加する を選択させる。
    戻り値: (mode, connection, local_id, game_map, weapons)"""
    menu_font = pygame.font.SysFont(_MENU_FONT_NAME, 24)

    while True:
        choice = _select_mode(screen, clock, menu_font)

        if choice == "solo":
            game_map = _select_map(screen, clock, menu_font)
            if game_map is None:
                continue
            weapon = _select_weapon(screen, clock, menu_font)
            if weapon is None:
                continue
            return "solo", None, 0, game_map, {0: weapon}

        if choice == "host":
            game_map = _select_map(screen, clock, menu_font)
            if game_map is None:
                continue
            host_weapon = _select_weapon(screen, clock, menu_font)
            if host_weapon is None:
                continue
            result = _host_relay_flow(screen, clock, menu_font, game_map, host_weapon)
            if result is None:
                continue
            connection, client_weapon = result
            return "host", connection, 0, game_map, {0: host_weapon, 1: client_weapon}

        if choice == "client":
            connection = _client_relay_flow(screen, clock, menu_font)
            if connection is None:
                continue
            received = _wait_for_map_selection(screen, clock, menu_font, connection)
            if received is None:
                connection.close()
                continue
            game_map, host_weapon = received
            client_weapon = _select_weapon(screen, clock, menu_font)
            if client_weapon is None:
                connection.close()
                continue
            connection.send({"type": "weapon_select", "weapon": client_weapon.name})
            return "client", connection, 1, game_map, {0: host_weapon, 1: client_weapon}


def _select_mode(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> str:
    lines = [
        "2D TOP-DOWN SHOOTER",
        "",
        "[1] ローカルプレイ",
        "[2] オンライン対戦: ルームを作る",
        "[3] オンライン対戦: ルームに参加する",
        "",
        "ESC で終了",
    ]
    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit
                if event.key == pygame.K_1:
                    return "solo"
                if event.key == pygame.K_2:
                    return "host"
                if event.key == pygame.K_3:
                    return "client"

        _draw_lines(screen, font, lines)
        pygame.display.flip()


def _select_map(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> GameMap | None:
    lines = ["マップを選択してください", ""]
    lines += [f"[{i + 1}] {m.name}" for i, m in enumerate(MAPS)]
    lines += ["", "ESC で戻る"]

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                for i, m in enumerate(MAPS):
                    if event.key == pygame.K_1 + i:
                        return m

        _draw_lines(screen, font, lines)
        pygame.display.flip()


def _select_weapon(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> Weapon | None:
    icon_frame = create_weapon_icon_frame()
    portraits = load_weapon_portraits()

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                for i, w in enumerate(WEAPONS):
                    if event.key == pygame.K_1 + i:
                        return w

        _draw_weapon_select(screen, font, icon_frame, portraits)
        pygame.display.flip()


def _draw_weapon_select(
    screen: pygame.Surface, font: pygame.font.Font, icon_frame: pygame.Surface, portraits: dict[str, pygame.Surface]
) -> None:
    screen.fill(COLOR_BG)

    title = font.render("使用する武器を選択してください", True, COLOR_PLAYER)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 80)))

    row_height = 100
    total_height = row_height * len(WEAPONS)
    start_y = HEIGHT // 2 - total_height // 2
    icon_x = WIDTH // 2 - 220

    for i, w in enumerate(WEAPONS):
        row_y = start_y + i * row_height
        screen.blit(icon_frame, (icon_x, row_y))

        portrait = portraits[w.name]
        icon_center = (icon_x + WEAPON_ICON_FRAME_SIZE[0] // 2, row_y + WEAPON_ICON_FRAME_SIZE[1] // 2)
        screen.blit(portrait, portrait.get_rect(center=icon_center))

        label = font.render(f"[{i + 1}] {w.name}", True, COLOR_PLAYER)
        label_x = icon_x + WEAPON_ICON_FRAME_SIZE[0] + 24
        label_y = row_y + WEAPON_ICON_FRAME_SIZE[1] // 2 - label.get_height() // 2
        screen.blit(label, (label_x, label_y))

    hint = font.render("ESC で戻る", True, COLOR_PLAYER)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, start_y + total_height + 30)))


def _wait_for_map_selection(
    screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, connection: RelayConnection
) -> tuple[GameMap, Weapon] | None:
    lines = ["ホストの選択を待っています...", "", "ESC でキャンセル"]

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None

        if not connection.connected:
            return None

        for msg in connection.poll():
            if msg.get("type") == "map_select":
                return get_map_by_name(msg["map"]), get_weapon_by_name(msg["weapon"])

        _draw_lines(screen, font, lines)
        pygame.display.flip()


def _show_message(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, lines: list[str]) -> None:
    """何かキーが押されるまでメッセージを表示し続ける(エラー表示用)。"""
    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                return
        _draw_lines(screen, font, lines)
        pygame.display.flip()


def _host_relay_flow(
    screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, game_map: GameMap, host_weapon: Weapon
) -> tuple[RelayConnection, Weapon] | None:
    try:
        conn, code = relay_connection.create_room(RELAY_URL)
    except ConnectionError as exc:
        _show_message(screen, clock, font, [
            "中継サーバーに接続できませんでした",
            "",
            str(exc),
            "",
            "何かキーを押すと戻ります",
        ])
        return None

    waiting_lines = [
        "ルームを作成しました",
        "",
        f"ルームコード:  {code}",
        "",
        "この4桁の番号を友達に伝えてください",
        "友達が「ルームに参加する」から入力すると対戦が始まります",
        "",
        "ESC でキャンセル",
    ]
    weapon_wait_lines = ["対戦相手の武器選択を待っています...", "", "ESC でキャンセル"]

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                conn.close()
                return None

        if conn.failed:
            conn.close()
            _show_message(screen, clock, font, [
                "接続が失われました", "", "何かキーを押すと戻ります",
            ])
            return None

        if conn.connected:
            break

        _draw_lines(screen, font, waiting_lines)
        pygame.display.flip()

    conn.send({"type": "map_select", "map": game_map.name, "weapon": host_weapon.name})

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                conn.close()
                return None

        if not conn.connected:
            return None

        for msg in conn.poll():
            if msg.get("type") == "weapon_select":
                return conn, get_weapon_by_name(msg["weapon"])

        _draw_lines(screen, font, weapon_wait_lines)
        pygame.display.flip()


def _client_relay_flow(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> RelayConnection | None:
    text = ""
    error: str | None = None

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None

                if event.key == pygame.K_RETURN:
                    code = text.strip()
                    if not (code.isdigit() and len(code) == 4):
                        error = "4桁の数字で入力してください"
                        continue
                    try:
                        return relay_connection.join_room(RELAY_URL, code)
                    except ConnectionError as exc:
                        error = f"参加失敗: {exc}"
                        continue

                if event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode.isdigit() and len(text) < 4:
                    text += event.unicode

        lines = [
            "参加する",
            "",
            "友達から伝えられた4桁のルームコードを入力してください",
            "",
            f"> {text}",
            "",
            "Enter で接続, ESC でキャンセル",
        ]
        if error:
            lines += ["", error]

        _draw_lines(screen, font, lines)
        pygame.display.flip()


def _draw_lines(screen: pygame.Surface, font: pygame.font.Font, lines: list[str]) -> None:
    screen.fill(COLOR_BG)
    y = HEIGHT // 2 - (len(lines) * _LINE_HEIGHT) // 2
    for line in lines:
        surf = font.render(line, True, COLOR_PLAYER)
        screen.blit(surf, surf.get_rect(center=(WIDTH // 2, y)))
        y += _LINE_HEIGHT
