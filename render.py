from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import pygame
from config import X_SIZE, Y_SIZE, GRID_SPACING, DISC_RADIUS, HOVER_RADIUS, UI_FONT_SIZE, EMPTY, P1, P2
from camera import Camera

FONT_PATH_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

FONT_NAME_CANDIDATES = [
    "Hiragino Sans GB",
    "STHeiti",
    "PingFang SC",
    "Arial Unicode MS",
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "WenQuanYi Zen Hei",
]

VISUAL_Z_SCALE = 1.22
COLUMN_LINE_COLOR = (120, 132, 165, 110)
EMPTY_SLOT_COLOR = (215, 222, 240, 48)
FILLED_SLOT_COLOR = (255, 255, 255, 30)
FOCUS_COLUMN_COLOR = (255, 215, 110, 220)
FOCUS_SLOT_COLOR = (255, 240, 180, 170)
FOCUS_LABEL_COLOR = (255, 245, 210)
PANEL_BG_COLOR = (20, 24, 34, 220)
PANEL_BORDER_COLOR = (96, 120, 170)
PANEL_NEXT_COLOR = (255, 220, 90)
PANEL_LAST_MOVE_COLOR = (255, 255, 255)


def load_ui_font(size: int, bold: bool = False) -> pygame.font.Font:
    for font_path in FONT_PATH_CANDIDATES:
        if Path(font_path).exists():
            font = pygame.font.Font(font_path, size)
            font.set_bold(bold)
            return font

    for font_name in FONT_NAME_CANDIDATES:
        matched = pygame.font.match_font(font_name)
        if matched:
            font = pygame.font.Font(matched, size)
            font.set_bold(bold)
            return font

    return pygame.font.SysFont(None, size, bold=bold)

def cell_to_world(x:int, y:int, z:int, X:int, Y:int, Z:int) -> Tuple[float,float,float]:
    cx = (X - 1) * 0.5
    cy = (Y - 1) * 0.5
    cz = (Z - 1) * 0.5
    wx = (x - cx) * GRID_SPACING
    wy = (y - cy) * GRID_SPACING
    wz = (z - cz) * GRID_SPACING
    return wx, wy, wz

# ─────────────────── 菜单按钮 ───────────────────
class MenuButton:
    def __init__(self, rect: pygame.Rect, text: str, color: Tuple[int,int,int],
                 hover_color: Tuple[int,int,int], text_color: Tuple[int,int,int] = (255,255,255)):
        self.rect = rect
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.hovered = False

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        c = self.hover_color if self.hovered else self.color
        # shadow
        shadow = pygame.Rect(self.rect.x + 4, self.rect.y + 4, self.rect.w, self.rect.h)
        pygame.draw.rect(screen, (0, 0, 0, 80), shadow, border_radius=14)
        # button body
        pygame.draw.rect(screen, c, self.rect, border_radius=14)
        # border
        border_c = (255, 255, 255, 60) if self.hovered else (180, 180, 200)
        pygame.draw.rect(screen, border_c, self.rect, width=2, border_radius=14)
        # text
        surf = font.render(self.text, True, self.text_color)
        tx = self.rect.centerx - surf.get_width() // 2
        ty = self.rect.centery - surf.get_height() // 2
        screen.blit(surf, (tx, ty))

    def check_hover(self, mx: int, my: int):
        self.hovered = self.rect.collidepoint(mx, my)

    def is_clicked(self, mx: int, my: int) -> bool:
        return self.rect.collidepoint(mx, my)


# ─────────────────── 主菜单场景 ───────────────────
class MenuScene:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        w, h = screen.get_size()
        self.title_font = load_ui_font(52, bold=True)
        self.sub_font = load_ui_font(22)
        self.btn_font = load_ui_font(30)

        btn_w, btn_h = 360, 72
        gap = 28
        total_h = btn_h * 3 + gap * 2
        start_y = h // 2 - total_h // 2 + 40

        cx = w // 2 - btn_w // 2

        self.btn_human_first = MenuButton(
            pygame.Rect(cx, start_y, btn_w, btn_h),
            "我先下棋（人类先手）",
            (40, 120, 200), (60, 150, 240)
        )
        self.btn_ai_first = MenuButton(
            pygame.Rect(cx, start_y + btn_h + gap, btn_w, btn_h),
            "AI 先下棋（AI先手）",
            (180, 60, 80), (220, 80, 100)
        )
        self.btn_two_player = MenuButton(
            pygame.Rect(cx, start_y + (btn_h + gap) * 2, btn_w, btn_h),
            "双人对战",
            (60, 140, 80), (80, 175, 100)
        )

        self.buttons = [self.btn_human_first, self.btn_ai_first, self.btn_two_player]

        # AI type selection buttons (smaller, below main buttons)
        small_w, small_h = 160, 46
        small_y = start_y + (btn_h + gap) * 3 + 20
        sx = w // 2 - (small_w * 2 + 16) // 2
        self.btn_ab = MenuButton(
            pygame.Rect(sx, small_y, small_w, small_h),
            "AlphaBeta AI",
            (80, 80, 110), (100, 100, 140)
        )
        self.btn_mcts = MenuButton(
            pygame.Rect(sx + small_w + 16, small_y, small_w, small_h),
            "MCTS AI",
            (80, 80, 110), (100, 100, 140)
        )
        self.ai_type_buttons = [self.btn_ab, self.btn_mcts]

        self.selected_ai = "ab"  # default

        # particles for background decoration
        import random
        self.particles = [(random.randint(0, w), random.randint(0, h),
                           random.uniform(0.2, 1.0), random.randint(1, 3)) for _ in range(60)]

    def update_hover(self, mx: int, my: int):
        for b in self.buttons + self.ai_type_buttons:
            b.check_hover(mx, my)

    def handle_click(self, mx: int, my: int) -> Optional[str]:
        """Returns 'human_first', 'ai_first', 'two_player', or None"""
        if self.btn_human_first.is_clicked(mx, my):
            return "human_first"
        if self.btn_ai_first.is_clicked(mx, my):
            return "ai_first"
        if self.btn_two_player.is_clicked(mx, my):
            return "two_player"
        if self.btn_ab.is_clicked(mx, my):
            self.selected_ai = "ab"
            return None
        if self.btn_mcts.is_clicked(mx, my):
            self.selected_ai = "mcts"
            return None
        return None

    def draw(self):
        w, h = self.screen.get_size()

        # background gradient (top-down)
        for y_line in range(h):
            t = y_line / h
            r = int(10 + 12 * t)
            g = int(10 + 8 * t)
            b = int(22 + 18 * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y_line), (w, y_line))

        # floating particles
        for i, (px, py, alpha, size) in enumerate(self.particles):
            c = int(100 * alpha)
            pygame.draw.circle(self.screen, (c, c, int(c * 1.4)), (int(px), int(py)), size)
            # slow drift
            self.particles[i] = ((px + 0.15) % w, (py - 0.1 * alpha) % h, alpha, size)

        # title
        title_surf = self.title_font.render("立体四子棋  5×5×5", True, (230, 235, 255))
        tx = w // 2 - title_surf.get_width() // 2
        self.screen.blit(title_surf, (tx, 80))

        # subtitle
        sub_surf = self.sub_font.render("三维空间  ·  连四获胜  ·  旋转视角", True, (160, 165, 190))
        sx = w // 2 - sub_surf.get_width() // 2
        self.screen.blit(sub_surf, (sx, 145))

        # decorative line
        lx = w // 2
        pygame.draw.line(self.screen, (80, 85, 120), (lx - 120, 182), (lx + 120, 182), 2)

        # main buttons
        for b in self.buttons:
            b.draw(self.screen, self.btn_font)

        # AI type label
        label = self.sub_font.render("AI 类型：", True, (180, 180, 200))
        lbl_x = self.btn_ab.rect.x - label.get_width() - 12
        lbl_y = self.btn_ab.rect.centery - label.get_height() // 2
        self.screen.blit(label, (lbl_x, lbl_y))

        # draw AI type buttons with selection indicator
        for b in self.ai_type_buttons:
            b.draw(self.screen, self.sub_font)

        # highlight selected AI
        sel_btn = self.btn_ab if self.selected_ai == "ab" else self.btn_mcts
        pygame.draw.rect(self.screen, (255, 220, 80), sel_btn.rect, width=3, border_radius=14)

        # bottom tip
        tip = self.sub_font.render("按 ESC 退出  ·  游戏中按 M 回到主菜单", True, (120, 120, 145))
        self.screen.blit(tip, (w // 2 - tip.get_width() // 2, h - 50))


# ─────────────────── 游戏渲染器 ───────────────────
class Renderer:
    def __init__(self, screen: pygame.Surface, camera: Camera, X:int, Y:int, Z:int):
        self.screen = screen
        self.cam = camera
        self.X, self.Y, self.Z = X, Y, Z
        self.font = load_ui_font(UI_FONT_SIZE)
        self.small = load_ui_font(18)

    def draw(self, board, current_player:int, hover_col: Optional[Tuple[int,int]],
             mode_text:str, episodes:int, human_player:int, two_player: bool = False):
        w,h = self.screen.get_size()
        self.screen.fill((14, 14, 20))
        focus_col = hover_col
        if focus_col is None and board.moves:
            last_move = board.moves[-1]
            focus_col = (last_move.x, last_move.y)

        col_centers: Dict[Tuple[int,int], Tuple[int,int,float]] = {}
        slot_centers: Dict[Tuple[int,int], List[Tuple[int,int,float]]] = {}
        for x in range(self.X):
            for y in range(self.Y):
                slots = [self._project_slot(x, y, z, w, h) for z in range(self.Z)]
                slot_centers[(x,y)] = slots
                col_centers[(x,y)] = slots[0]

        self._draw_grid(col_centers)
        self._draw_columns(board, slot_centers, focus_col)

        discs = []
        for x in range(self.X):
            for y in range(self.Y):
                top = board.top_z(x,y)
                for z in range(top+1):
                    p = board.get(x,y,z)
                    if p != EMPTY:
                        sx,sy,depth = slot_centers[(x,y)][z]
                        discs.append((depth, z, p, sx, sy))
        discs.sort(reverse=True, key=lambda t: t[0])

        for depth, z, p, sx, sy in discs:
            self._draw_disc(p, sx, sy, z, depth)

        if hover_col is not None:
            x,y = hover_col
            next_z = board.next_free_z(x,y)
            if next_z is not None:
                sx,sy,depth = slot_centers[(x,y)][next_z]
                hover_radius = self._disc_radius(depth) + 4
                pygame.draw.circle(self.screen, (230,230,255), (sx,sy), hover_radius, 2)
                if next_z > 0:
                    below_sx, below_sy, _ = slot_centers[(x,y)][next_z - 1]
                    pygame.draw.line(self.screen, (180, 190, 220), (below_sx, below_sy), (sx, sy), 2)

        self._draw_column_panel(board, focus_col)
        self._draw_ui(board, current_player, mode_text, episodes, human_player, two_player)

    def _draw_grid(self, col_centers: Dict[Tuple[int,int], Tuple[int,int,float]]):
        corners = [(0,0), (self.X-1,0), (self.X-1, self.Y-1), (0, self.Y-1)]
        pts = [col_centers[c][:2] for c in corners]
        pygame.draw.polygon(self.screen, (38,38,54), pts, width=0)
        pygame.draw.polygon(self.screen, (110,110,145), pts, width=3)

        for y in range(self.Y):
            for x in range(self.X-1):
                p1 = col_centers[(x,y)][:2]
                p2 = col_centers[(x+1,y)][:2]
                pygame.draw.line(self.screen, (85,85,115), p1, p2, 2)
        for x in range(self.X):
            for y in range(self.Y-1):
                p1 = col_centers[(x,y)][:2]
                p2 = col_centers[(x,y+1)][:2]
                pygame.draw.line(self.screen, (85,85,115), p1, p2, 2)

        for (x,y),(sx,sy,_) in col_centers.items():
            pygame.draw.circle(self.screen, (155,155,185), (sx,sy), 5)
            txt = self.small.render(f"{x},{y}", True, (215,215,235))
            self.screen.blit(txt, (sx+6, sy+6))

    def _project_slot(self, x:int, y:int, z:int, w:int, h:int) -> Tuple[int,int,float]:
        wx, wy, wz = cell_to_world(x, y, z, self.X, self.Y, self.Z)
        return self.cam.project(wx, wy, wz * VISUAL_Z_SCALE, w, h)

    def _disc_radius(self, depth: float) -> int:
        perspective = self.cam.dist / max(0.75, depth)
        radius = int(round(DISC_RADIUS * perspective))
        return max(9, min(17, radius))

    def _draw_columns(self, board, slot_centers: Dict[Tuple[int,int], List[Tuple[int,int,float]]],
                      focus_col: Optional[Tuple[int,int]]):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        for (x, y), slots in slot_centers.items():
            bottom = slots[0]
            top = slots[-1]
            is_focus = focus_col == (x, y)
            line_color = FOCUS_COLUMN_COLOR if is_focus else COLUMN_LINE_COLOR
            line_width = 6 if is_focus else 4
            pygame.draw.line(overlay, line_color, bottom[:2], top[:2], line_width)

            for z, (sx, sy, depth) in enumerate(slots):
                slot_radius = max(4, self._disc_radius(depth) - 5)
                filled = board.get(x, y, z) != EMPTY
                if is_focus:
                    slot_radius += 2
                    slot_color = (255, 255, 255, 42) if filled else FOCUS_SLOT_COLOR
                    slot_width = 0 if filled else 2
                else:
                    slot_color = FILLED_SLOT_COLOR if filled else EMPTY_SLOT_COLOR
                    slot_width = 0 if filled else 1
                pygame.draw.circle(overlay, slot_color, (sx, sy), slot_radius, slot_width)

            if is_focus:
                next_z = board.next_free_z(x, y)
                for z, (sx, sy, _) in enumerate(slots):
                    label = self.small.render(f"z={z}", True, FOCUS_LABEL_COLOR)
                    overlay.blit(label, (sx + 14, sy - label.get_height() // 2))
                    if next_z == z:
                        pygame.draw.circle(overlay, PANEL_NEXT_COLOR, (sx, sy), 6)
                        if z > 0:
                            prev_sx, prev_sy, _ = slots[z - 1]
                            pygame.draw.line(overlay, PANEL_NEXT_COLOR, (prev_sx, prev_sy), (sx, sy), 3)

        self.screen.blit(overlay, (0, 0))

    def _draw_column_panel(self, board, focus_col: Optional[Tuple[int,int]]):
        if focus_col is None:
            return

        panel_w = 250
        panel_h = 360
        panel_x = self.screen.get_width() - panel_w - 28
        panel_y = 92
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL_BG_COLOR, panel.get_rect(), border_radius=20)
        pygame.draw.rect(panel, PANEL_BORDER_COLOR, panel.get_rect(), width=2, border_radius=20)

        x, y = focus_col
        next_z = board.next_free_z(x, y)
        title = self.font.render(f"当前列 ({x}, {y})", True, (240, 244, 255))
        panel.blit(title, (18, 16))

        if next_z is None:
            subtitle_text = "这一列已满"
        else:
            subtitle_text = f"下一手将落在 z={next_z}"
        subtitle = self.small.render(subtitle_text, True, (188, 196, 220))
        panel.blit(subtitle, (18, 48))

        rail_x = 86
        top_y = 94
        slot_gap = 48
        bottom_y = top_y + slot_gap * (self.Z - 1)
        pygame.draw.line(panel, (120, 140, 185), (rail_x, top_y), (rail_x, bottom_y), 4)

        last_move = board.moves[-1] if board.moves else None
        last_is_focus = last_move is not None and (last_move.x, last_move.y) == focus_col

        for display_idx, z in enumerate(range(self.Z - 1, -1, -1)):
            cy = top_y + display_idx * slot_gap
            cx = rail_x
            player = board.get(x, y, z)

            row_rect = pygame.Rect(22, cy - 20, panel_w - 44, 40)
            if next_z == z:
                pygame.draw.rect(panel, (255, 220, 90, 28), row_rect, border_radius=12)
                pygame.draw.rect(panel, PANEL_NEXT_COLOR, row_rect, width=2, border_radius=12)

            if player == EMPTY:
                pygame.draw.circle(panel, (90, 105, 135), (cx, cy), 14, 2)
            elif player == P1:
                pygame.draw.circle(panel, (235, 70, 80), (cx, cy), 14)
                pygame.draw.circle(panel, (255, 150, 160), (cx, cy), 14, 3)
            else:
                pygame.draw.circle(panel, (70, 175, 245), (cx, cy), 14)
                pygame.draw.circle(panel, (155, 220, 255), (cx, cy), 14, 3)

            if last_is_focus and last_move is not None and last_move.z == z:
                pygame.draw.circle(panel, PANEL_LAST_MOVE_COLOR, (cx, cy), 19, 2)

            z_label = self.small.render(f"z={z}", True, (230, 235, 248))
            panel.blit(z_label, (20, cy - z_label.get_height() // 2))

            if player == EMPTY:
                status_text = "空"
                status_color = (160, 170, 190)
            elif player == P1:
                status_text = "红方"
                status_color = (255, 170, 176)
            else:
                status_text = "蓝方"
                status_color = (172, 228, 255)

            status = self.small.render(status_text, True, status_color)
            panel.blit(status, (118, cy - status.get_height() // 2))

            if next_z == z:
                next_badge = self.small.render("NEXT", True, PANEL_NEXT_COLOR)
                panel.blit(next_badge, (174, cy - next_badge.get_height() // 2))
            elif last_is_focus and last_move is not None and last_move.z == z:
                last_badge = self.small.render("LAST", True, PANEL_LAST_MOVE_COLOR)
                panel.blit(last_badge, (174, cy - last_badge.get_height() // 2))

        help_text = self.small.render("悬停棋盘列可查看其 Z 轴剖面", True, (150, 160, 184))
        panel.blit(help_text, (18, panel_h - 30))
        self.screen.blit(panel, panel_rect.topleft)

    def _draw_disc(self, player:int, sx:int, sy:int, z:int, depth: float):
        if player == P1:
            base = (235, 70, 80)
            rim  = (255, 150, 160)
        else:
            base = (70, 175, 245)
            rim  = (155, 220, 255)

        radius = self._disc_radius(depth)
        shade = max(0.65, 1.0 - 0.07*z)
        color = (int(base[0]*shade), int(base[1]*shade), int(base[2]*shade))
        rimc  = (int(rim[0]*shade),  int(rim[1]*shade),  int(rim[2]*shade))

        shadow_radius = radius + 2
        shadow_surface = pygame.Surface((shadow_radius * 4, shadow_radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(
            shadow_surface,
            (0, 0, 0, 55),
            (shadow_radius * 2, shadow_radius * 2),
            shadow_radius,
        )
        self.screen.blit(shadow_surface, (sx - shadow_radius * 2 + 2, sy - shadow_radius * 2 + 3))

        pygame.draw.circle(self.screen, color, (sx,sy), radius)
        pygame.draw.circle(self.screen, rimc, (sx,sy), radius, max(2, radius // 4))
        highlight_x = sx - max(3, radius // 3)
        highlight_y = sy - max(4, radius // 2)
        pygame.draw.circle(self.screen, (255,255,255), (highlight_x, highlight_y), max(3, radius // 3), 2)

    def _draw_ui(self, board, current_player:int, mode_text:str, episodes:int,
                 human_player:int, two_player: bool):
        winner = board.check_winner()
        if winner != 0:
            if two_player:
                result = "红方获胜！" if winner == P1 else "蓝方获胜！"
            elif winner == human_player:
                result = "你赢了！"
            else:
                result = "AI 赢了！"
            msg = f"{result}   (R 重开, M 主菜单, Q 退出)"
        elif board.is_full():
            msg = "平局! (R 重开, M 主菜单, Q 退出)"
        else:
            color_label = "红" if current_player == P1 else "蓝"
            if two_player:
                turn_label = f"{color_label}方"
                msg = f"轮到: {turn_label} | {mode_text}"
            else:
                turn_label = "你" if current_player == human_player else "AI"
                msg = f"轮到: {turn_label}({color_label}) | {mode_text} | episodes={episodes}"

        surf = self.font.render(msg, True, (240,240,250))
        self.screen.blit(surf, (18, 16))
        tip = self.small.render(
            "A/D旋转 W/S抬头 | +/-调episodes | [ ]调AB深度 | R重开 | M主菜单 | Q退出",
            True, (210,210,230)
        )
        self.screen.blit(tip, (18, 44))

    def pick_column_from_mouse(self, board, mx:int, my:int) -> Optional[Tuple[int,int]]:
        w,h = self.screen.get_size()
        best = None
        best_d2 = 10**18
        for x in range(self.X):
            for y in range(self.Y):
                next_z = board.next_free_z(x,y)
                if next_z is None:
                    continue
                sx,sy,depth = self._project_slot(x, y, next_z, w, h)
                dx = mx - sx
                dy = my - sy
                d2 = dx*dx + dy*dy
                if d2 < best_d2:
                    best_d2 = d2
                    best = (x, y, self._disc_radius(depth))
        if best is None:
            return None
        x, y, radius = best
        hit_radius = max(HOVER_RADIUS, radius + 6)
        return (x, y) if best_d2 <= (hit_radius * hit_radius) else None
