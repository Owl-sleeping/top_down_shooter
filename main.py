import pygame

from constants import WIDTH, HEIGHT, WINDOW_TITLE
from backend.game import Game
from frontend.menu import run_menu
from resources import IMAGES_DIR


def main() -> None:
    pygame.init()
    pygame.display.set_icon(pygame.image.load(str(IMAGES_DIR / "icon.png")))
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20, bold=True)

    mode, connection, local_id, game_map, weapons = run_menu(screen, clock, font)
    Game(
        screen, clock, font,
        mode=mode, connection=connection, local_id=local_id, game_map=game_map, weapons=weapons,
    ).run()


if __name__ == "__main__":
    main()
