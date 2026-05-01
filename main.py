from __future__ import annotations
import pygame
from config import WIDTH, HEIGHT, FPS, YAW_STEP, PITCH_STEP, X_SIZE, Y_SIZE, Z_SIZE
from game import Game
from camera import Camera
from render import Renderer, MenuScene

try:
    from render_gl import ModernGLRenderer, is_available as gl_renderer_available
except Exception:
    ModernGLRenderer = None

    def gl_renderer_available() -> bool:
        return False

STATE_MENU = "menu"
STATE_GAME = "game"

def main():
    pygame.init()
    pygame.display.set_caption("立体四子棋 5×5×5 — AlphaBeta / MCTS")

    def open_cpu_window():
        try:
            return pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF, vsync=1)
        except TypeError:
            return pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)

    def open_gl_window():
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        try:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        except pygame.error:
            pass
        try:
            return pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF, vsync=1)
        except TypeError:
            return pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)

    screen = open_cpu_window()
    clock = pygame.time.Clock()

    cam = Camera()
    game = Game()
    renderer = Renderer(screen, cam, X_SIZE, Y_SIZE, Z_SIZE)
    renderer.render_backend = "CPU Pygame"
    menu = MenuScene(screen)

    def switch_to_game_renderer():
        nonlocal screen, renderer
        if gl_renderer_available() and ModernGLRenderer is not None:
            try:
                screen = open_gl_window()
                renderer = ModernGLRenderer(screen, cam, X_SIZE, Y_SIZE, Z_SIZE)
                pygame.display.set_caption("立体四子棋 5×5×5 — GPU 3D ModernGL")
                return
            except Exception as exc:
                print(f"ModernGL renderer unavailable, falling back to Pygame renderer: {exc}")
        screen = open_cpu_window()
        renderer = Renderer(screen, cam, X_SIZE, Y_SIZE, Z_SIZE)
        renderer.render_backend = "CPU Pygame"
        pygame.display.set_caption("立体四子棋 5×5×5 — CPU Pygame fallback")

    def switch_to_menu_renderer():
        nonlocal screen, renderer, menu
        screen = open_cpu_window()
        renderer = Renderer(screen, cam, X_SIZE, Y_SIZE, Z_SIZE)
        renderer.render_backend = "CPU Pygame"
        menu = MenuScene(screen)
        pygame.display.set_caption("立体四子棋 5×5×5 — AlphaBeta / MCTS")

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
                        switch_to_game_renderer()
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
                    switch_to_menu_renderer()
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
