import pygame

from constants import WIDTH, HEIGHT, WINDOW_TITLE
from game import Game


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20, bold=True)

    Game(screen, clock, font).run()


if __name__ == "__main__":
    main()
