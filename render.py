from __future__ import annotations
import math
import random
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

VISUAL_Z_SCALE = 1.04
SPRITE_SCALE = 4
BG_TOP = (5, 8, 16)
BG_BOTTOM = (22, 19, 30)
COLUMN_LINE_COLOR = (104, 142, 178, 82)
EMPTY_SLOT_COLOR = (220, 230, 250, 30)
FILLED_SLOT_COLOR = (255, 255, 255, 24)
FOCUS_COLUMN_COLOR = (255, 211, 96, 230)
FOCUS_SLOT_COLOR = (255, 235, 164, 170)
PANEL_NEXT_COLOR = (255, 220, 90)
PANEL_LAST_MOVE_COLOR = (255, 255, 255)
P1_CORE = (255, 72, 84)
P1_EDGE = (132, 18, 36)
P1_LIGHT = (255, 176, 168)
P1_GLOW = (255, 64, 86)
P2_CORE = (56, 188, 255)
P2_EDGE = (14, 68, 132)
P2_LIGHT = (176, 238, 255)
P2_GLOW = (64, 203, 255)
GOLD = (255, 218, 102)


def clamp255(value: float) -> int:
    return max(0, min(255, int(round(value))))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return (
        clamp255(lerp(a[0], b[0], t)),
        clamp255(lerp(a[1], b[1], t)),
        clamp255(lerp(a[2], b[2], t)),
    )


def scale_color(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple(clamp255(c * factor) for c in color)


def alpha_color(color: Tuple[int, int, int], alpha: int) -> Tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


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
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shadow = self.rect.move(0, 8)
        pygame.draw.rect(overlay, (0, 0, 0, 95), shadow, border_radius=12)
        glow_alpha = 70 if self.hovered else 32
        pygame.draw.rect(overlay, alpha_color(c, glow_alpha), self.rect.inflate(14, 14), border_radius=16)
        pygame.draw.rect(overlay, alpha_color(c, 235), self.rect, border_radius=12)
        pygame.draw.rect(overlay, (255, 255, 255, 58), self.rect.inflate(-4, -4), width=1, border_radius=10)
        border_c = GOLD if self.hovered else (135, 162, 210)
        pygame.draw.rect(overlay, border_c, self.rect, width=2, border_radius=12)
        screen.blit(overlay, (0, 0))

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

        btn_w, btn_h = 390, 74
        gap = 28
        total_h = btn_h * 3 + gap * 2
        start_y = h // 2 - total_h // 2 + 40

        cx = w // 2 - btn_w // 2

        self.btn_human_first = MenuButton(
            pygame.Rect(cx, start_y, btn_w, btn_h),
            "我先下棋（人类先手）",
            (32, 116, 184), (53, 161, 232)
        )
        self.btn_ai_first = MenuButton(
            pygame.Rect(cx, start_y + btn_h + gap, btn_w, btn_h),
            "AI 先下棋（AI先手）",
            (177, 50, 68), (226, 70, 88)
        )
        self.btn_two_player = MenuButton(
            pygame.Rect(cx, start_y + (btn_h + gap) * 2, btn_w, btn_h),
            "双人对战",
            (42, 130, 94), (58, 171, 124)
        )

        self.buttons = [self.btn_human_first, self.btn_ai_first, self.btn_two_player]

        # AI type selection buttons (smaller, below main buttons)
        small_w, small_h = 160, 46
        small_y = start_y + (btn_h + gap) * 3 + 20
        sx = w // 2 - (small_w * 2 + 16) // 2
        self.btn_ab = MenuButton(
            pygame.Rect(sx, small_y, small_w, small_h),
            "AlphaBeta AI",
            (43, 49, 70), (68, 78, 112)
        )
        self.btn_mcts = MenuButton(
            pygame.Rect(sx + small_w + 16, small_y, small_w, small_h),
            "MCTS AI",
            (43, 49, 70), (68, 78, 112)
        )
        self.ai_type_buttons = [self.btn_ab, self.btn_mcts]

        self.selected_ai = "ab"  # default

        rng = random.Random(1261)
        self.particles = [
            (
                rng.randint(0, w),
                rng.randint(0, h),
                rng.uniform(0.18, 0.95),
                rng.randint(1, 3),
                rng.choice((P1_GLOW, P2_GLOW, GOLD, (185, 205, 255))),
            )
            for _ in range(96)
        ]

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
        now = pygame.time.get_ticks() * 0.001

        for y_line in range(h):
            t = y_line / h
            pygame.draw.line(self.screen, lerp_color(BG_TOP, BG_BOTTOM, t), (0, y_line), (w, y_line))

        light = pygame.Surface((w, h), pygame.SRCALPHA)
        sweep_x = int((math.sin(now * 0.32) * 0.5 + 0.5) * w)
        pygame.draw.line(light, (68, 202, 255, 28), (sweep_x - 540, h), (sweep_x + 250, 0), 120)
        pygame.draw.line(light, (255, 84, 105, 20), (sweep_x + 420, h), (sweep_x - 140, 0), 90)
        for i in range(7):
            y = int(h * (0.18 + i * 0.095) + math.sin(now * 0.4 + i) * 6)
            pygame.draw.line(light, (255, 255, 255, 10), (0, y), (w, y - 38), 1)
        self.screen.blit(light, (0, 0))

        for i, (px, py, alpha, size, color) in enumerate(self.particles):
            pulse = 0.72 + 0.28 * math.sin(now * 1.3 + i * 0.77)
            c = scale_color(color, alpha * pulse)
            pygame.draw.circle(self.screen, c, (int(px), int(py)), size)
            self.particles[i] = ((px + 0.22 * alpha) % w, (py - 0.12 * alpha) % h, alpha, size, color)

        self._draw_showcase_cube(now)

        title_shadow = self.title_font.render("立体四子棋  5×5×5", True, (0, 0, 0))
        self.screen.blit(title_shadow, (w // 2 - title_shadow.get_width() // 2 + 3, 78 + 5))
        title_surf = self.title_font.render("立体四子棋  5×5×5", True, (230, 235, 255))
        tx = w // 2 - title_surf.get_width() // 2
        self.screen.blit(title_surf, (tx, 80))

        sub_surf = self.sub_font.render("5×5×5 策略空间  ·  连四获胜  ·  旋转视角", True, (172, 187, 214))
        sx = w // 2 - sub_surf.get_width() // 2
        self.screen.blit(sub_surf, (sx, 145))

        lx = w // 2
        line_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.line(line_overlay, (77, 204, 255, 80), (lx - 170, 184), (lx + 170, 184), 5)
        pygame.draw.line(line_overlay, GOLD + (210,), (lx - 120, 184), (lx + 120, 184), 2)
        self.screen.blit(line_overlay, (0, 0))

        for b in self.buttons:
            b.draw(self.screen, self.btn_font)

        label = self.sub_font.render("AI 类型：", True, (190, 202, 225))
        lbl_x = self.btn_ab.rect.x - label.get_width() - 12
        lbl_y = self.btn_ab.rect.centery - label.get_height() // 2
        self.screen.blit(label, (lbl_x, lbl_y))

        for b in self.ai_type_buttons:
            b.draw(self.screen, self.sub_font)

        sel_btn = self.btn_ab if self.selected_ai == "ab" else self.btn_mcts
        selector = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(selector, (255, 220, 80, 75), sel_btn.rect.inflate(10, 10), border_radius=17)
        pygame.draw.rect(selector, GOLD, sel_btn.rect, width=3, border_radius=12)
        self.screen.blit(selector, (0, 0))

        tip = self.sub_font.render("按 ESC 退出  ·  游戏中按 M 回到主菜单", True, (134, 149, 176))
        self.screen.blit(tip, (w // 2 - tip.get_width() // 2, h - 50))

    def _project_preview(self, x: float, y: float, z: float, center: Tuple[int, int],
                         scale: float, yaw: float, pitch: float) -> Tuple[int, int, float]:
        cy, sy = math.cos(yaw), math.sin(yaw)
        x1 = x * cy - y * sy
        y1 = x * sy + y * cy
        cp, sp = math.cos(pitch), math.sin(pitch)
        y2 = y1 * cp - z * sp
        z2 = y1 * sp + z * cp
        depth = max(0.6, 9.8 - y2)
        return (
            int(center[0] + (x1 / depth) * scale),
            int(center[1] - (z2 / depth) * scale),
            depth,
        )

    def _draw_showcase_cube(self, now: float):
        w, h = self.screen.get_size()
        center = (int(w * 0.23), int(h * 0.58))
        yaw = now * 0.22 + math.radians(30)
        pitch = math.radians(24)
        scale = min(w, h) * 0.34
        spacing = 0.92
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)

        pts = {}
        for x in range(X_SIZE):
            for y in range(Y_SIZE):
                for z in range(5):
                    wx = (x - 2) * spacing
                    wy = (y - 2) * spacing
                    wz = (z - 2) * spacing * 0.94
                    pts[(x, y, z)] = self._project_preview(wx, wy, wz, center, scale, yaw, pitch)

        base_corners = [pts[(0, 0, 0)][:2], pts[(4, 0, 0)][:2], pts[(4, 4, 0)][:2], pts[(0, 4, 0)][:2]]
        pygame.draw.polygon(overlay, (255, 255, 255, 16), base_corners)
        pygame.draw.polygon(overlay, (96, 168, 224, 115), base_corners, width=2)

        for x in range(X_SIZE):
            for y in range(Y_SIZE):
                bottom = pts[(x, y, 0)][:2]
                top = pts[(x, y, 4)][:2]
                pygame.draw.line(overlay, (72, 184, 232, 38), bottom, top, 8)
                pygame.draw.line(overlay, (158, 210, 248, 125), bottom, top, 2)

        for z in (0, 4):
            for y in range(Y_SIZE):
                for x in range(X_SIZE - 1):
                    pygame.draw.line(overlay, (122, 155, 205, 72), pts[(x, y, z)][:2], pts[(x + 1, y, z)][:2], 1)
            for x in range(X_SIZE):
                for y in range(Y_SIZE - 1):
                    pygame.draw.line(overlay, (122, 155, 205, 72), pts[(x, y, z)][:2], pts[(x, y + 1, z)][:2], 1)

        preview_moves = [
            (0, 0, 0, P1), (0, 0, 1, P2), (1, 1, 0, P2), (2, 2, 0, P1),
            (2, 2, 1, P1), (2, 2, 2, P2), (3, 2, 0, P2), (3, 3, 0, P1),
            (4, 4, 0, P2), (4, 4, 1, P1), (1, 3, 0, P1),
        ]
        preview_discs = []
        for x, y, z, player in preview_moves:
            sx, sy, depth = pts[(x, y, z)]
            preview_discs.append((depth, sx, sy, player))
        preview_discs.sort(reverse=True)
        for depth, sx, sy, player in preview_discs:
            radius = max(10, min(18, int(15 * 9.8 / depth)))
            color = P1_CORE if player == P1 else P2_CORE
            glow = P1_GLOW if player == P1 else P2_GLOW
            pygame.draw.circle(overlay, alpha_color(glow, 60), (sx, sy), radius + 7)
            pygame.draw.circle(overlay, scale_color(color, 0.55), (sx + 3, sy + 4), radius)
            pygame.draw.circle(overlay, color, (sx, sy), radius)
            pygame.draw.circle(overlay, (255, 255, 255, 155), (sx - radius // 3, sy - radius // 3), max(3, radius // 4))

        self.screen.blit(overlay, (0, 0))


# ─────────────────── 游戏渲染器 ───────────────────
class Renderer:
    def __init__(self, screen: pygame.Surface, camera: Camera, X:int, Y:int, Z:int):
        self.screen = screen
        self.cam = camera
        self.X, self.Y, self.Z = X, Y, Z
        self.font = load_ui_font(UI_FONT_SIZE)
        self.small = load_ui_font(18)
        self._background_cache: Optional[pygame.Surface] = None
        self._background_size: Optional[Tuple[int, int]] = None
        self._disc_cache: Dict[Tuple[int, int, int], pygame.Surface] = {}
        self._ghost_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self._shadow_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self._last_tick = pygame.time.get_ticks()
        self.time = 0.0

    def draw(self, board, current_player:int, hover_col: Optional[Tuple[int,int]],
             mode_text:str, episodes:int, human_player:int, two_player: bool = False):
        w,h = self.screen.get_size()
        now_tick = pygame.time.get_ticks()
        self.time += min(0.05, max(0.0, (now_tick - self._last_tick) / 1000.0))
        self._last_tick = now_tick
        self._draw_background(w, h)
        focus_col = hover_col

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
                        discs.append((depth, z, p, sx, sy, x, y))
        discs.sort(reverse=True, key=lambda t: t[0])

        for depth, z, p, sx, sy, x, y in discs:
            dimmed = focus_col is not None and (x, y) != focus_col
            self._draw_disc(p, sx, sy, z, depth, dimmed)

        if board.moves:
            last = board.moves[-1]
            sx, sy, depth = slot_centers[(last.x, last.y)][last.z]
            self._draw_last_move_marker(sx, sy, self._disc_radius(depth))

        if hover_col is not None:
            x,y = hover_col
            next_z = board.next_free_z(x,y)
            if next_z is not None:
                sx,sy,depth = slot_centers[(x,y)][next_z]
                hover_radius = self._disc_radius(depth) + 5
                self._draw_ghost_disc(current_player, sx, sy, hover_radius, next_z)
                if next_z > 0:
                    below_sx, below_sy, _ = slot_centers[(x,y)][next_z - 1]
                    guide = pygame.Surface((w, h), pygame.SRCALPHA)
                    pygame.draw.line(guide, (255, 220, 90, 118), (below_sx, below_sy), (sx, sy), 3)
                    self.screen.blit(guide, (0, 0))

        self._draw_column_panel(board, focus_col)
        self._draw_minimap(board, focus_col)
        self._draw_ui(board, current_player, mode_text, episodes, human_player, two_player)

    def _draw_last_move_marker(self, sx: int, sy: int, radius: int):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        pulse = 0.65 + 0.35 * math.sin(self.time * 4.0)
        pygame.draw.circle(overlay, (255, 255, 255, int(46 + 32 * pulse)), (sx, sy), radius + 8, 2)
        pygame.draw.circle(overlay, (255, 222, 100, int(40 + 35 * pulse)), (sx, sy), radius + 13, 1)
        self.screen.blit(overlay, (0, 0))

    def _build_background(self, w: int, h: int) -> pygame.Surface:
        bg = pygame.Surface((w, h))
        for y in range(h):
            t = y / max(1, h - 1)
            base = lerp_color(BG_TOP, BG_BOTTOM, t)
            pygame.draw.line(bg, base, (0, y), (w, y))

        rng = random.Random(2309)
        for _ in range(44):
            x = rng.randrange(0, max(1, w))
            y = rng.randrange(0, max(1, h))
            alpha = rng.uniform(0.16, 0.48)
            size = rng.choice((1, 1, 2))
            color = rng.choice(((126, 154, 190), (165, 185, 220), (206, 216, 238)))
            pygame.draw.circle(bg, scale_color(color, alpha), (x, y), size)

        horizon = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(5):
            y = int(h * (0.37 + i * 0.075))
            alpha = max(5, 16 - i * 2)
            pygame.draw.line(horizon, (110, 142, 178, alpha), (0, y), (w, y - int(h * 0.03)), 1)
        bg.blit(horizon, (0, 0))
        return bg.convert()

    def _draw_background(self, w: int, h: int):
        if self._background_cache is None or self._background_size != (w, h):
            self._background_cache = self._build_background(w, h)
            self._background_size = (w, h)
        self.screen.blit(self._background_cache, (0, 0))

        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 34), (0, 0, w, int(h * 0.11)))
        pygame.draw.rect(overlay, (0, 0, 0, 28), (0, int(h * 0.82), w, int(h * 0.18)))
        self.screen.blit(overlay, (0, 0))

    def _draw_grid(self, col_centers: Dict[Tuple[int,int], Tuple[int,int,float]]):
        w, h = self.screen.get_size()
        pts = [
            self._project_slot(-0.5, -0.5, 0, w, h)[:2],
            self._project_slot(self.X - 0.5, -0.5, 0, w, h)[:2],
            self._project_slot(self.X - 0.5, self.Y - 0.5, 0, w, h)[:2],
            self._project_slot(-0.5, self.Y - 0.5, 0, w, h)[:2],
        ]
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shadow_pts = [(x, y + 22) for x, y in pts]
        pygame.draw.polygon(overlay, (0, 0, 0, 74), shadow_pts)
        pygame.draw.polygon(overlay, (16, 24, 36, 142), pts)
        pygame.draw.polygon(overlay, (92, 150, 196, 74), pts, width=5)
        pygame.draw.polygon(overlay, (176, 210, 240, 116), pts, width=2)

        for x in range(self.X + 1):
            gx = x - 0.5
            p1 = self._project_slot(gx, -0.5, 0, w, h)[:2]
            p2 = self._project_slot(gx, self.Y - 0.5, 0, w, h)[:2]
            pygame.draw.line(overlay, (94, 142, 184, 74), p1, p2, 1)
        for y in range(self.Y + 1):
            gy = y - 0.5
            p1 = self._project_slot(-0.5, gy, 0, w, h)[:2]
            p2 = self._project_slot(self.X - 0.5, gy, 0, w, h)[:2]
            pygame.draw.line(overlay, (94, 142, 184, 74), p1, p2, 1)

        for (x,y),(sx,sy,_) in col_centers.items():
            pygame.draw.circle(overlay, (28, 37, 50, 220), (sx, sy), 5)
            pygame.draw.circle(overlay, (136, 168, 202, 128), (sx, sy), 5, 1)
            pygame.draw.circle(overlay, (225, 234, 244, 138), (sx, sy), 2)

        self.screen.blit(overlay, (0, 0))

    def _project_slot(self, x:int, y:int, z:int, w:int, h:int) -> Tuple[int,int,float]:
        wx, wy, wz = cell_to_world(x, y, z, self.X, self.Y, self.Z)
        return self.cam.project(wx, wy, wz * VISUAL_Z_SCALE, w, h)

    def _disc_radius(self, depth: float) -> int:
        perspective = self.cam.dist / max(0.75, depth)
        radius = int(round(DISC_RADIUS * perspective))
        return max(8, min(18, radius))

    def _draw_columns(self, board, slot_centers: Dict[Tuple[int,int], List[Tuple[int,int,float]]],
                      focus_col: Optional[Tuple[int,int]]):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        w, h = self.screen.get_size()
        layers = []
        for z in range(self.Z):
            avg_depth = sum(slot_centers[(x, y)][z][2] for x in range(self.X) for y in range(self.Y)) / (self.X * self.Y)
            layers.append((avg_depth, z))

        for _, z in sorted(layers, reverse=True):
            corners = [
                self._project_slot(-0.5, -0.5, z, w, h)[:2],
                self._project_slot(self.X - 0.5, -0.5, z, w, h)[:2],
                self._project_slot(self.X - 0.5, self.Y - 0.5, z, w, h)[:2],
                self._project_slot(-0.5, self.Y - 0.5, z, w, h)[:2],
            ]
            layer_alpha = 10 + z * 3
            line_alpha = 46 + z * 8
            pygame.draw.polygon(overlay, (70, 128, 168, layer_alpha), corners)
            pygame.draw.polygon(overlay, (166, 204, 236, line_alpha), corners, width=1)

            for x in range(self.X + 1):
                gx = x - 0.5
                p1 = self._project_slot(gx, -0.5, z, w, h)[:2]
                p2 = self._project_slot(gx, self.Y - 0.5, z, w, h)[:2]
                pygame.draw.line(overlay, (108, 158, 202, max(24, line_alpha - 16)), p1, p2, 1)
            for y in range(self.Y + 1):
                gy = y - 0.5
                p1 = self._project_slot(-0.5, gy, z, w, h)[:2]
                p2 = self._project_slot(self.X - 0.5, gy, z, w, h)[:2]
                pygame.draw.line(overlay, (108, 158, 202, max(24, line_alpha - 16)), p1, p2, 1)

            label_pt = slot_centers[(self.X - 1, self.Y - 1)][z]
            pygame.draw.circle(overlay, (180, 205, 232, 70), label_pt[:2], 3)

        for corner in ((-0.5, -0.5), (self.X - 0.5, -0.5), (self.X - 0.5, self.Y - 0.5), (-0.5, self.Y - 0.5)):
            bottom = self._project_slot(corner[0], corner[1], 0, w, h)
            top = self._project_slot(corner[0], corner[1], self.Z - 1, w, h)
            pygame.draw.line(overlay, (86, 128, 168, 48), bottom[:2], top[:2], 2)
            pygame.draw.line(overlay, (220, 235, 255, 34), bottom[:2], top[:2], 1)

        if focus_col is not None:
            slots = slot_centers[focus_col]
            bottom = slots[0]
            top = slots[-1]
            pygame.draw.line(overlay, (0, 0, 0, 52), (bottom[0] + 2, bottom[1] + 4), (top[0] + 2, top[1] + 4), 13)
            pygame.draw.line(overlay, (255, 221, 108, 86), bottom[:2], top[:2], 12)
            pygame.draw.line(overlay, FOCUS_COLUMN_COLOR, bottom[:2], top[:2], 5)
            pygame.draw.line(overlay, (255, 255, 255, 84), bottom[:2], top[:2], 1)

            next_z = board.next_free_z(*focus_col)
            for z, (sx, sy, depth) in enumerate(slots):
                slot_radius = max(5, self._disc_radius(depth) - 6)
                filled = board.get(focus_col[0], focus_col[1], z) != EMPTY
                if filled:
                    pygame.draw.circle(overlay, (255, 255, 255, 36), (sx, sy), slot_radius)
                else:
                    pygame.draw.circle(overlay, (255, 221, 122, 50), (sx, sy), slot_radius + 4, 1)
                    pygame.draw.circle(overlay, FOCUS_SLOT_COLOR, (sx, sy), slot_radius, 2)

                if next_z == z:
                    pulse = 0.65 + 0.35 * math.sin(self.time * 5.2)
                    pygame.draw.circle(overlay, (255, 222, 100, int(58 * pulse)), (sx, sy), slot_radius + 9)
                    pygame.draw.circle(overlay, PANEL_NEXT_COLOR, (sx, sy), 6)
                    if z > 0:
                        prev_sx, prev_sy, _ = slots[z - 1]
                        pygame.draw.line(overlay, (255, 222, 100, 122), (prev_sx, prev_sy), (sx, sy), 3)

        self.screen.blit(overlay, (0, 0))

    def _draw_column_panel(self, board, focus_col: Optional[Tuple[int,int]]):
        if focus_col is None:
            return

        panel_w = 220
        panel_h = 310
        panel_x = self.screen.get_width() - panel_w - 24
        panel_y = 92
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (11, 15, 23, 214), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (112, 142, 182, 135), panel.get_rect(), width=1, border_radius=14)

        x, y = focus_col
        next_z = board.next_free_z(x, y)
        title = self.font.render(f"列 ({x}, {y})", True, (236, 241, 250))
        panel.blit(title, (16, 14))

        if next_z is None:
            subtitle_text = "已满"
        else:
            subtitle_text = f"下一手 z={next_z}"
        subtitle = self.small.render(subtitle_text, True, (182, 194, 214))
        panel.blit(subtitle, (16, 45))

        rail_x = 72
        top_y = 82
        slot_gap = 42
        bottom_y = top_y + slot_gap * (self.Z - 1)
        pygame.draw.line(panel, (85, 108, 140), (rail_x, top_y), (rail_x, bottom_y), 3)

        last_move = board.moves[-1] if board.moves else None
        last_is_focus = last_move is not None and (last_move.x, last_move.y) == focus_col

        for display_idx, z in enumerate(range(self.Z - 1, -1, -1)):
            cy = top_y + display_idx * slot_gap
            cx = rail_x
            player = board.get(x, y, z)

            row_rect = pygame.Rect(14, cy - 18, panel_w - 28, 36)
            if next_z == z:
                pygame.draw.rect(panel, (255, 220, 90, 22), row_rect, border_radius=9)
                pygame.draw.rect(panel, (255, 220, 90, 150), row_rect, width=1, border_radius=9)

            if player == EMPTY:
                pygame.draw.circle(panel, (93, 111, 140), (cx, cy), 12, 1)
            elif player == P1:
                pygame.draw.circle(panel, P1_CORE, (cx, cy), 12)
                pygame.draw.circle(panel, P1_LIGHT, (cx, cy), 12, 2)
            else:
                pygame.draw.circle(panel, P2_CORE, (cx, cy), 12)
                pygame.draw.circle(panel, P2_LIGHT, (cx, cy), 12, 2)

            if last_is_focus and last_move is not None and last_move.z == z:
                pygame.draw.circle(panel, PANEL_LAST_MOVE_COLOR, (cx, cy), 16, 1)

            z_label = self.small.render(f"z {z}", True, (202, 212, 230))
            panel.blit(z_label, (20, cy - z_label.get_height() // 2))

            badge = ""
            badge_color = (190, 202, 220)
            if next_z == z:
                badge = "NEXT"
                badge_color = PANEL_NEXT_COLOR
            elif last_is_focus and last_move is not None and last_move.z == z:
                badge = "LAST"
                badge_color = PANEL_LAST_MOVE_COLOR
            if badge:
                badge_surf = self.small.render(badge, True, badge_color)
                panel.blit(badge_surf, (132, cy - badge_surf.get_height() // 2))

        self.screen.blit(panel, panel_rect.topleft)

    def _draw_minimap(self, board, focus_col: Optional[Tuple[int, int]]):
        panel_w = 238
        panel_h = 238
        panel_x = 22
        panel_y = self.screen.get_height() - panel_h - 22
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (9, 13, 20, 214), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (105, 135, 174, 120), panel.get_rect(), width=1, border_radius=14)

        title = self.small.render("顶视列图", True, (226, 235, 248))
        panel.blit(title, (16, 12))

        cell = 34
        gap = 4
        start_x = 19
        start_y = 48
        last = board.moves[-1] if board.moves else None

        for y in range(self.Y - 1, -1, -1):
            for x in range(self.X):
                gx = start_x + x * (cell + gap)
                gy = start_y + (self.Y - 1 - y) * (cell + gap)
                rect = pygame.Rect(gx, gy, cell, cell)
                is_focus = focus_col == (x, y)
                pygame.draw.rect(panel, (18, 25, 36, 230), rect, border_radius=7)
                pygame.draw.rect(panel, (82, 104, 134, 115), rect, width=1, border_radius=7)

                stripe_h = max(3, (cell - 10) // self.Z)
                for z in range(self.Z):
                    p = board.get(x, y, z)
                    if p == EMPTY:
                        color = (52, 65, 84, 120)
                    elif p == P1:
                        color = (*P1_CORE, 225)
                    else:
                        color = (*P2_CORE, 225)
                    stripe_y = gy + cell - 6 - (z + 1) * stripe_h
                    pygame.draw.rect(panel, color, (gx + 7, stripe_y, cell - 14, stripe_h - 1), border_radius=2)

                if last is not None and (last.x, last.y) == (x, y):
                    pygame.draw.circle(panel, (255, 255, 255, 190), rect.center, 4)

                if is_focus:
                    pygame.draw.rect(panel, (255, 220, 90, 72), rect.inflate(7, 7), border_radius=10)
                    pygame.draw.rect(panel, PANEL_NEXT_COLOR, rect.inflate(3, 3), width=2, border_radius=9)

        self.screen.blit(panel, (panel_x, panel_y))

    def _player_palette(self, player: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int],
                                                    Tuple[int, int, int], Tuple[int, int, int]]:
        if player == P1:
            return P1_CORE, P1_EDGE, P1_LIGHT, P1_GLOW
        return P2_CORE, P2_EDGE, P2_LIGHT, P2_GLOW

    def _make_soft_shadow(self, radius: int, alpha: int) -> pygame.Surface:
        scale = 3
        width = (radius * 4 + 22) * scale
        height = (radius * 2 + 16) * scale
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        cx, cy = width // 2, height // 2
        max_rx = int(radius * 1.7 * scale)
        max_ry = int(radius * 0.7 * scale)
        for i in range(16, 0, -1):
            t = i / 16
            rx = max(1, int(max_rx * t))
            ry = max(1, int(max_ry * t))
            a = int(alpha * (1 - t) ** 1.8)
            rect = pygame.Rect(cx - rx, cy - ry, rx * 2, ry * 2)
            pygame.draw.ellipse(shadow, (0, 0, 0, a), rect)
        return pygame.transform.smoothscale(shadow, (width // scale, height // scale)).convert_alpha()

    def _get_shadow(self, radius: int, alpha: int = 120) -> pygame.Surface:
        key = (radius, alpha)
        if key not in self._shadow_cache:
            self._shadow_cache[key] = self._make_soft_shadow(radius, alpha)
        return self._shadow_cache[key]

    def _make_disc_sprite(self, player: int, radius: int, z: int) -> pygame.Surface:
        core, edge, light, glow = self._player_palette(player)
        shade = max(0.66, 1.0 - 0.052 * z)
        core = scale_color(core, shade)
        edge = scale_color(edge, shade * 0.95)
        light = scale_color(light, max(0.82, shade))
        glow = scale_color(glow, shade)

        scale = SPRITE_SCALE
        pad = 18
        size = (radius * 2 + pad * 2) * scale
        center = size // 2
        rr = radius * scale
        surf = pygame.Surface((size, size), pygame.SRCALPHA)

        for grow in range(10, 0, -1):
            alpha = int(5 + grow * 3.2)
            pygame.draw.circle(surf, alpha_color(glow, alpha), (center, center), rr + grow * scale)

        pygame.draw.circle(surf, edge, (center, center), rr)
        steps = max(12, radius)
        for i in range(steps):
            t = i / max(1, steps - 1)
            rad = int(rr * (1.0 - 0.045 * i))
            if rad <= 0:
                break
            ox = int(-rr * 0.17 * t)
            oy = int(-rr * 0.24 * t)
            color = lerp_color(edge, core, min(1.0, 0.22 + t * 0.86))
            pygame.draw.circle(surf, color, (center + ox, center + oy), rad)

        pygame.draw.circle(surf, alpha_color(light, 190), (center, center), rr, max(2, rr // 10))
        pygame.draw.circle(surf, (0, 0, 0, 96), (center + rr // 10, center + rr // 7), rr - rr // 12, max(2, rr // 12))

        gloss_rect = pygame.Rect(center - int(rr * 0.62), center - int(rr * 0.72), int(rr * 1.05), int(rr * 0.58))
        pygame.draw.ellipse(surf, (255, 255, 255, 54), gloss_rect)
        pygame.draw.circle(surf, (255, 255, 255, 205), (center - rr // 3, center - rr // 3), max(3, rr // 7))
        pygame.draw.circle(surf, (255, 255, 255, 84), (center - rr // 3, center - rr // 3), max(5, rr // 4), 2)

        final_size = size // scale
        return pygame.transform.smoothscale(surf, (final_size, final_size)).convert_alpha()

    def _get_disc_sprite(self, player: int, radius: int, z: int) -> pygame.Surface:
        key = (player, radius, z)
        if key not in self._disc_cache:
            self._disc_cache[key] = self._make_disc_sprite(player, radius, z)
        return self._disc_cache[key]

    def _make_ghost_sprite(self, player: int, radius: int) -> pygame.Surface:
        _, _, light, glow = self._player_palette(player)
        scale = SPRITE_SCALE
        pad = 18
        size = (radius * 2 + pad * 2) * scale
        center = size // 2
        rr = radius * scale
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        for grow in range(12, 0, -1):
            pygame.draw.circle(surf, alpha_color(glow, 5 + grow * 4), (center, center), rr + grow * scale)
        pygame.draw.circle(surf, alpha_color(glow, 58), (center, center), rr)
        pygame.draw.circle(surf, alpha_color(light, 220), (center, center), rr, max(3, rr // 8))
        pygame.draw.circle(surf, (255, 255, 255, 140), (center - rr // 4, center - rr // 4), max(4, rr // 6))
        final_size = size // scale
        return pygame.transform.smoothscale(surf, (final_size, final_size)).convert_alpha()

    def _draw_ghost_disc(self, player: int, sx: int, sy: int, radius: int, _z: int):
        pulse = 0.92 + 0.08 * math.sin(self.time * 6.0)
        radius = max(8, int(radius * pulse))
        key = (player, radius)
        if key not in self._ghost_cache:
            self._ghost_cache[key] = self._make_ghost_sprite(player, radius)
        sprite = self._ghost_cache[key]
        self.screen.blit(sprite, (sx - sprite.get_width() // 2, sy - sprite.get_height() // 2))

    def _draw_disc(self, player:int, sx:int, sy:int, z:int, depth: float, dimmed: bool = False):
        radius = self._disc_radius(depth)
        shadow = self._get_shadow(radius, 64 if dimmed else 128)
        if not dimmed:
            self.screen.blit(shadow, (sx - shadow.get_width() // 2 + radius // 4,
                                      sy - shadow.get_height() // 2 + radius // 2))
        sprite = self._get_disc_sprite(player, radius, z)
        if dimmed:
            sprite = sprite.copy()
            sprite.set_alpha(78)
        self.screen.blit(sprite, (sx - sprite.get_width() // 2, sy - sprite.get_height() // 2))

    def _draw_ui(self, board, current_player:int, mode_text:str, _episodes:int,
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
                msg = f"轮到: {turn_label}({color_label}) | {mode_text}"

        surf = self.font.render(msg, True, (240,240,250))
        tip = self.small.render(
            "A/D 旋转   W/S 抬头   R 重开   M 菜单   Q 退出   +/- MCTS   [ ] AB",
            True, (178, 190, 212)
        )

        w = self.screen.get_width()
        hud_w = min(w - 320, max(540, surf.get_width() + 36, tip.get_width() + 36))
        hud = pygame.Surface((hud_w, 68), pygame.SRCALPHA)
        pygame.draw.rect(hud, (8, 12, 20, 196), hud.get_rect(), border_radius=12)
        pygame.draw.rect(hud, (120, 150, 190, 90), hud.get_rect(), width=1, border_radius=12)
        hud.blit(surf, (18, 10))
        hud.blit(tip, (18, 40))
        self.screen.blit(hud, (18, 14))

        backend = getattr(self, "render_backend", "CPU Pygame")
        badge = self.small.render(backend, True, (255, 230, 130))
        badge_w = badge.get_width() + 24
        badge_layer = pygame.Surface((badge_w, 34), pygame.SRCALPHA)
        pygame.draw.rect(badge_layer, (70, 52, 12, 170), badge_layer.get_rect(), border_radius=10)
        pygame.draw.rect(badge_layer, (255, 220, 90, 120), badge_layer.get_rect(), width=1, border_radius=10)
        badge_layer.blit(badge, (12, 7))
        self.screen.blit(badge_layer, (w - badge_w - 24, self.screen.get_height() - 54))

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
