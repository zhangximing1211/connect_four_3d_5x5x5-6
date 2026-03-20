from __future__ import annotations
import pygame
from config import WIDTH, HEIGHT, FPS, YAW_STEP, PITCH_STEP, X_SIZE, Y_SIZE, Z_SIZE
from game import Game
from camera import Camera
from render import Renderer, MenuScene

STATE_MENU = "menu"
STATE_GAME = "game"

def main():
    pygame.init()
    pygame.display.set_caption("立体四子棋 5×5×5 — AlphaBeta / MCTS")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    cam = Camera()
    game = Game()
    renderer = Renderer(screen, cam, X_SIZE, Y_SIZE, Z_SIZE)
    menu = MenuScene(screen)

    state = STATE_MENU
    running = True
    hover = None

    while running:
        clock.tick(FPS)
        mx, my = pygame.mouse.get_pos()

        # ─────────── 菜单状态 ───────────
        if state == STATE_MENU:
            menu.update_hover(mx, my)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    choice = menu.handle_click(mx, my)
                    if choice is not None:
                        if choice == "human_first":
                            game.configure(human_first=True, engine=menu.selected_ai)
                        elif choice == "ai_first":
                            game.configure(human_first=False, engine=menu.selected_ai)
                        elif choice == "two_player":
                            game.configure(two_player=True)
                        state = STATE_GAME

            menu.draw()
            pygame.display.flip()
            continue

        # ─────────── 游戏状态 ───────────
        hover = renderer.pick_column_from_mouse(game.board, mx, my)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_r:
                    game.reset()
                elif event.key == pygame.K_m:
                    # 回到主菜单
                    game.reset()
                    state = STATE_MENU

                # view control
                elif event.key == pygame.K_a:
                    cam.rotate(dyaw=-YAW_STEP)
                elif event.key == pygame.K_d:
                    cam.rotate(dyaw=+YAW_STEP)
                elif event.key == pygame.K_w:
                    cam.rotate(dpitch=+PITCH_STEP)
                elif event.key == pygame.K_s:
                    cam.rotate(dpitch=-PITCH_STEP)

                # MCTS episodes adjust
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    game.set_episodes(game.episodes + 250)
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                    game.set_episodes(game.episodes - 250)

                # AlphaBeta depth adjust
                elif event.key == pygame.K_LEFTBRACKET:
                    game.set_ab_depth(game.ab_depth - 1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    game.set_ab_depth(game.ab_depth + 1)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hover is not None and game.is_human_turn():
                    game.handle_drop(hover)

        game.maybe_ai_move()
        renderer.draw(game.board, game.current, hover,
                      game.mode_text(), game.episodes, game.human_player, game.two_player)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
