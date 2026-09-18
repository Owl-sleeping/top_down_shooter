"""起動時のモード選択・接続確立を行う簡易メニュー画面。"""

import socket

import pygame

from backend.network import Client, Connection, Host
from backend.maps import GameMap, MAPS, get_map_by_name
from backend.weapons import Weapon, WEAPONS, get_weapon_by_name
from constants import WIDTH, HEIGHT, NETWORK_PORT, COLOR_BG, COLOR_PLAYER

# "arial"はCJKグリフを持たないため、日本語表示にはIME非依存で日本語Windowsに
# 標準搭載されているYu Gothicを使う(HUDの英語表示用フォントとは別に用意する)。
_MENU_FONT_NAME = "yugothic"
_LINE_HEIGHT = 28


def run_menu(
    screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font
) -> tuple[str, Connection | None, int, GameMap, dict[int, Weapon]]:
    """[1]ローカルプレイ [2]ホストになる [3]参加する を選択させる。
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
            result = _host_flow(screen, clock, menu_font, game_map, host_weapon)
            if result is None:
                continue
            connection, client_weapon = result
            return "host", connection, 0, game_map, {0: host_weapon, 1: client_weapon}

        if choice == "client":
            connection = _client_flow(screen, clock, menu_font)
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
        "[2] オンライン対戦: ホストになる",
        "[3] オンライン対戦: 参加する",
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
    lines = ["使用する武器を選択してください", ""]
    lines += [f"[{i + 1}] {w.name}" for i, w in enumerate(WEAPONS)]
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
                for i, w in enumerate(WEAPONS):
                    if event.key == pygame.K_1 + i:
                        return w

        _draw_lines(screen, font, lines)
        pygame.display.flip()


def _wait_for_map_selection(
    screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, connection: Connection
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


def _host_flow(
    screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, game_map: GameMap, host_weapon: Weapon
) -> tuple[Connection, Weapon] | None:
    host_net = Host(NETWORK_PORT)
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        local_ip = "(取得失敗)"

    waiting_lines = [
        "ホストとして待機中...",
        "",
        f"ローカルIP: {local_ip}  ポート: {NETWORK_PORT}",
        "友人と対戦するには、ルーターでこのポートを開放し",
        "あなたのグローバルIPを友人に伝えてください。",
        "",
        "接続を待っています...",
        "",
        "ESC でキャンセル",
    ]
    try:
        connection: Connection | None = None
        while connection is None:
            clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return None

            connection = host_net.accept(poll_timeout=0.05)
            if connection is None:
                _draw_lines(screen, font, waiting_lines)
                pygame.display.flip()

        connection.send({"type": "map_select", "map": game_map.name, "weapon": host_weapon.name})

        # クライアントが自分の武器を選ぶまで待つ
        weapon_wait_lines = ["対戦相手の武器選択を待っています...", "", "ESC でキャンセル"]
        while True:
            clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    connection.close()
                    return None

            if not connection.connected:
                return None

            for msg in connection.poll():
                if msg.get("type") == "weapon_select":
                    return connection, get_weapon_by_name(msg["weapon"])

            _draw_lines(screen, font, weapon_wait_lines)
            pygame.display.flip()
    finally:
        host_net.close()


def _client_flow(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> Connection | None:
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
                    if not text.strip():
                        continue
                    ip, _, port_str = text.strip().partition(":")
                    port = int(port_str) if port_str.isdigit() else NETWORK_PORT
                    try:
                        return Client.connect(ip, port)
                    except OSError as exc:
                        error = f"接続失敗: {exc}"
                        continue

                if event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode.isprintable():
                    text += event.unicode

        lines = [
            "参加する",
            "",
            "ホストのIPアドレスを入力してください",
            "(例: 123.45.67.89 または 123.45.67.89:5555)",
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
