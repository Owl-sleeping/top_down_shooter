"""起動時のモード選択・接続確立を行う簡易メニュー画面。"""

import socket

import pygame

from backend.network import Client, Connection, Host
from constants import WIDTH, HEIGHT, NETWORK_PORT, COLOR_BG, COLOR_PLAYER

# "arial"はCJKグリフを持たないため、日本語表示にはIME非依存で日本語Windowsに
# 標準搭載されているYu Gothicを使う(HUDの英語表示用フォントとは別に用意する)。
_MENU_FONT_NAME = "yugothic"
_LINE_HEIGHT = 28


def run_menu(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> tuple[str, Connection | None, int]:
    """[1]ローカルプレイ [2]ホストになる [3]参加する を選択させる。
    戻り値: (mode, connection, local_id)"""
    menu_font = pygame.font.SysFont(_MENU_FONT_NAME, 24)

    while True:
        choice = _select_mode(screen, clock, menu_font)

        if choice == "solo":
            return "solo", None, 0

        if choice == "host":
            connection = _host_flow(screen, clock, menu_font)
            if connection is not None:
                return "host", connection, 0
            continue

        if choice == "client":
            connection = _client_flow(screen, clock, menu_font)
            if connection is not None:
                return "client", connection, 1
            continue


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


def _host_flow(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> Connection | None:
    host_net = Host(NETWORK_PORT)
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        local_ip = "(取得失敗)"

    lines = [
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
        while True:
            clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return None

            connection = host_net.accept(poll_timeout=0.05)
            if connection is not None:
                return connection

            _draw_lines(screen, font, lines)
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
