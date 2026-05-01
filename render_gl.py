from __future__ import annotations

import math
import struct
from typing import Iterable, List, Optional, Tuple

import pygame

from config import EMPTY, GRID_SPACING, HOVER_RADIUS, P1, P2, UI_FONT_SIZE
from render import (
    GOLD,
    P1_CORE,
    P1_GLOW,
    P2_CORE,
    P2_GLOW,
    VISUAL_Z_SCALE,
    cell_to_world,
    load_ui_font,
)

try:
    import moderngl as mgl
except Exception:  # pragma: no cover - the caller handles fallback.
    mgl = None


Vec3 = Tuple[float, float, float]
Mat4 = List[List[float]]
GL_WORLD_SCALE = 0.80
BOARD_PAD = 0.5
PIECE_RADIUS = 0.31
LAST_RING_RADIUS = 0.50
GHOST_RADIUS = 0.34
SLOT_DOT_RADIUS = 0.055


def is_available() -> bool:
    return mgl is not None


def _v_add(a: Vec3, b: Vec3) -> Vec3:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def _v_sub(a: Vec3, b: Vec3) -> Vec3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _v_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v_cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _v_len(v: Vec3) -> float:
    return math.sqrt(max(1e-12, _v_dot(v, v)))


def _v_norm(v: Vec3) -> Vec3:
    length = _v_len(v)
    return v[0] / length, v[1] / length, v[2] / length


def _mat_identity() -> Mat4:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_mul(a: Mat4, b: Mat4) -> Mat4:
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def _mat_vec(m: Mat4, v: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    return (
        sum(m[0][k] * v[k] for k in range(4)),
        sum(m[1][k] * v[k] for k in range(4)),
        sum(m[2][k] * v[k] for k in range(4)),
        sum(m[3][k] * v[k] for k in range(4)),
    )


def _mat_pack(m: Mat4) -> bytes:
    return struct.pack("16f", *(m[r][c] for c in range(4) for r in range(4)))


def _perspective(fov_deg: float, aspect: float, near: float, far: float) -> Mat4:
    f = 1.0 / math.tan(math.radians(fov_deg) * 0.5)
    return [
        [f / aspect, 0.0, 0.0, 0.0],
        [0.0, f, 0.0, 0.0],
        [0.0, 0.0, (far + near) / (near - far), (2.0 * far * near) / (near - far)],
        [0.0, 0.0, -1.0, 0.0],
    ]


def _look_at(eye: Vec3, target: Vec3, up: Vec3 = (0.0, 0.0, 1.0)) -> Mat4:
    f = _v_norm(_v_sub(target, eye))
    s = _v_norm(_v_cross(f, up))
    u = _v_cross(s, f)
    return [
        [s[0], s[1], s[2], -_v_dot(s, eye)],
        [u[0], u[1], u[2], -_v_dot(u, eye)],
        [-f[0], -f[1], -f[2], _v_dot(f, eye)],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _model_matrix(pos: Vec3, scale: Vec3) -> Mat4:
    return [
        [scale[0], 0.0, 0.0, pos[0]],
        [0.0, scale[1], 0.0, pos[1]],
        [0.0, 0.0, scale[2], pos[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _sphere_mesh(stacks: int = 28, slices: int = 36) -> bytes:
    rows: List[float] = []
    for i in range(stacks):
        t0 = math.pi * i / stacks
        t1 = math.pi * (i + 1) / stacks
        for j in range(slices):
            p0 = 2.0 * math.pi * j / slices
            p1 = 2.0 * math.pi * (j + 1) / slices
            quad = ((t0, p0), (t1, p0), (t1, p1), (t0, p0), (t1, p1), (t0, p1))
            for theta, phi in quad:
                x = math.sin(theta) * math.cos(phi)
                y = math.sin(theta) * math.sin(phi)
                z = math.cos(theta)
                rows.extend((x, y, z, x, y, z))
    return struct.pack(f"{len(rows)}f", *rows)


class ModernGLRenderer:
    def __init__(self, screen: pygame.Surface, camera, x_size: int, y_size: int, z_size: int):
        if mgl is None:
            raise RuntimeError("ModernGL is not installed")

        self.screen = screen
        self.cam = camera
        self.X, self.Y, self.Z = x_size, y_size, z_size
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.DEPTH_TEST)
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        self.font = load_ui_font(UI_FONT_SIZE)
        self.small = load_ui_font(18)
        self.tiny = load_ui_font(15)

        self._sphere_prog = self._sphere_program()
        self._sphere_vbo = self.ctx.buffer(_sphere_mesh())
        self._sphere_vao = self.ctx.vertex_array(
            self._sphere_prog,
            [(self._sphere_vbo, "3f 3f", "in_pos", "in_norm")],
        )
        self._sphere_count = self._sphere_vbo.size // (6 * 4)

        self._flat_prog = self._flat_program()
        self._overlay_prog = self._overlay_program()
        self._quad_vbo = self.ctx.buffer(reserve=6 * 4 * 4)
        self._quad_vao = self.ctx.vertex_array(
            self._overlay_prog,
            [(self._quad_vbo, "2f 2f", "in_pos", "in_uv")],
        )
        self._white_tex = self.ctx.texture((1, 1), 4, b"\xff\xff\xff\xff")
        self._last_tick = pygame.time.get_ticks()
        self.time = 0.0

    def draw(self, board, current_player: int, hover_col: Optional[Tuple[int, int]],
             mode_text: str, episodes: int, human_player: int, two_player: bool = False):
        w, h = self.screen.get_size()
        self.ctx.viewport = (0, 0, w, h)

        now_tick = pygame.time.get_ticks()
        self.time += min(0.05, max(0.0, (now_tick - self._last_tick) / 1000.0))
        self._last_tick = now_tick

        view, proj, eye = self._camera_matrices(w, h)
        vp = _mat_mul(proj, view)
        self.ctx.clear(0.018, 0.021, 0.033, 1.0, depth=1.0)

        self._draw_background_grid(vp)
        self._draw_board_glass(vp, hover_col, board)

        last_move = board.moves[-1] if board.moves else None
        if last_move:
            self._draw_piece(last_move.player, self._slot_world(last_move.x, last_move.y, last_move.z), PIECE_RADIUS, vp, eye, last=True)

        for x in range(self.X):
            for y in range(self.Y):
                top = board.top_z(x, y)
                for z in range(top + 1):
                    player = board.get(x, y, z)
                    if player != EMPTY:
                        is_last = last_move is not None and (last_move.x, last_move.y, last_move.z) == (x, y, z)
                        if is_last:
                            continue
                        dimmed = hover_col is not None and (x, y) != hover_col
                        self._draw_piece(player, self._slot_world(x, y, z), PIECE_RADIUS, vp, eye, alpha=0.32 if dimmed else 1.0)

        if hover_col is not None:
            next_z = board.next_free_z(*hover_col)
            if next_z is not None:
                self._draw_hover(current_player, hover_col[0], hover_col[1], next_z, vp, eye)

        self._draw_hud(board, current_player, mode_text, episodes, human_player, two_player)
        if hover_col is not None:
            self._draw_column_panel(board, hover_col)
        self._draw_minimap(board, hover_col)

    def pick_column_from_mouse(self, board, mx: int, my: int) -> Optional[Tuple[int, int]]:
        w, h = self.screen.get_size()
        view, proj, _ = self._camera_matrices(w, h)
        vp = _mat_mul(proj, view)
        best = None
        best_d2 = 10**18
        for x in range(self.X):
            for y in range(self.Y):
                next_z = board.next_free_z(x, y)
                if next_z is None:
                    continue
                sx, sy, _ = self._project_world(self._slot_world(x, y, next_z), vp, w, h)
                dx = mx - sx
                dy = my - sy
                d2 = dx * dx + dy * dy
                if d2 < best_d2:
                    best_d2 = d2
                    best = (x, y)
        return best if best is not None and best_d2 <= HOVER_RADIUS * HOVER_RADIUS * 1.6 else None

    def _camera_matrices(self, w: int, h: int) -> Tuple[Mat4, Mat4, Vec3]:
        yaw = math.radians(self.cam.yaw_deg)
        pitch = math.radians(self.cam.pitch_deg)
        dist = self.cam.dist * 2.45
        horizontal = math.cos(pitch) * dist
        eye = (
            math.sin(yaw) * horizontal,
            -math.cos(yaw) * horizontal,
            math.sin(pitch) * dist + 3.2,
        )
        view = _look_at(eye, (0.0, 0.0, 0.15))
        proj = _perspective(34.0, w / max(1, h), 0.1, 120.0)
        return view, proj, eye

    def _slot_world(self, x: int, y: int, z: int) -> Vec3:
        wx, wy, wz = cell_to_world(x, y, z, self.X, self.Y, self.Z)
        return wx * GL_WORLD_SCALE, wy * GL_WORLD_SCALE, wz * VISUAL_Z_SCALE * GL_WORLD_SCALE

    def _board_world(self, x: float, y: float, z: int) -> Vec3:
        wx, wy, wz = cell_to_world(x, y, z, self.X, self.Y, self.Z)
        return wx * GL_WORLD_SCALE, wy * GL_WORLD_SCALE, wz * VISUAL_Z_SCALE * GL_WORLD_SCALE

    def _project_world(self, pos: Vec3, vp: Mat4, w: int, h: int) -> Tuple[int, int, float]:
        clip = _mat_vec(vp, (pos[0], pos[1], pos[2], 1.0))
        inv_w = 1.0 / max(1e-6, clip[3])
        nx, ny, nz = clip[0] * inv_w, clip[1] * inv_w, clip[2] * inv_w
        return int((nx * 0.5 + 0.5) * w), int((1.0 - (ny * 0.5 + 0.5)) * h), nz

    def _draw_background_grid(self, vp: Mat4):
        span = GRID_SPACING * 8.0
        z = -GRID_SPACING * 2.9
        points: List[Vec3] = []
        for i in range(-8, 9):
            t = i * GRID_SPACING
            points.append((-span, t, z))
            points.append((span, t, z))
            points.append((t, -span, z))
            points.append((t, span, z))
        self._draw_lines(points, vp, (0.18, 0.27, 0.37, 0.22), width=1.0)

    def _draw_board_glass(self, vp: Mat4, hover_col: Optional[Tuple[int, int]], board):
        self.ctx.disable(mgl.CULL_FACE)
        self.ctx.depth_mask = False

        x0 = -BOARD_PAD
        y0 = -BOARD_PAD
        x1 = self.X - 1 + BOARD_PAD
        y1 = self.Y - 1 + BOARD_PAD

        for z in range(self.Z):
            corners = [
                self._board_world(x0, y0, z),
                self._board_world(x1, y0, z),
                self._board_world(x1, y1, z),
                self._board_world(x0, y1, z),
            ]
            plane = [corners[0], corners[1], corners[2], corners[0], corners[2], corners[3]]
            self._draw_triangles(plane, vp, (0.14, 0.30, 0.46, 0.050 + z * 0.006))

            lines: List[Vec3] = []
            for x in range(self.X + 1):
                gx = x - BOARD_PAD
                lines.extend((self._board_world(gx, y0, z), self._board_world(gx, y1, z)))
            for y in range(self.Y + 1):
                gy = y - BOARD_PAD
                lines.extend((self._board_world(x0, gy, z), self._board_world(x1, gy, z)))
            self._draw_lines(lines, vp, (0.40, 0.66, 0.88, 0.20 + z * 0.016), width=1.0)
            self._draw_lines([corners[0], corners[1], corners[1], corners[2], corners[2], corners[3], corners[3], corners[0]],
                             vp, (0.68, 0.84, 1.0, 0.30 + z * 0.012), width=1.4)

        corner_lines: List[Vec3] = []
        for corner in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            corner_lines.extend((self._board_world(corner[0], corner[1], 0), self._board_world(corner[0], corner[1], self.Z - 1)))
        self._draw_lines(corner_lines, vp, (0.66, 0.84, 1.0, 0.48), width=1.8)

        if hover_col is not None:
            x, y = hover_col
            self._draw_focus_cell_volume(x, y, vp)
            self._draw_lines(
                [self._slot_world(x, y, 0), self._slot_world(x, y, self.Z - 1)],
                vp,
                (1.0, 0.78, 0.24, 0.88),
                width=2.4,
            )
            for z in range(self.Z):
                pos = self._slot_world(x, y, z)
                alpha = 0.22 if board.get(x, y, z) == EMPTY else 0.11
                self._draw_piece(0, pos, SLOT_DOT_RADIUS, vp, (0.0, 0.0, 12.0), slot=True, alpha=alpha)

        self.ctx.depth_mask = True

    def _draw_focus_cell_volume(self, x: int, y: int, vp: Mat4):
        x0 = x - BOARD_PAD
        x1 = x + BOARD_PAD
        y0 = y - BOARD_PAD
        y1 = y + BOARD_PAD
        z0 = 0
        z1 = self.Z - 1
        bottom = [
            self._board_world(x0, y0, z0),
            self._board_world(x1, y0, z0),
            self._board_world(x1, y1, z0),
            self._board_world(x0, y1, z0),
        ]
        top = [
            self._board_world(x0, y0, z1),
            self._board_world(x1, y0, z1),
            self._board_world(x1, y1, z1),
            self._board_world(x0, y1, z1),
        ]
        faces: List[Vec3] = []
        for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
            faces.extend((bottom[i], bottom[j], top[j], bottom[i], top[j], top[i]))
        self._draw_triangles(faces, vp, (0.18, 0.66, 0.88, 0.070))
        outline: List[Vec3] = []
        for z in range(self.Z):
            a = self._board_world(x0, y0, z)
            b = self._board_world(x1, y0, z)
            c = self._board_world(x1, y1, z)
            d = self._board_world(x0, y1, z)
            outline.extend((a, b, b, c, c, d, d, a))
        for i in range(4):
            outline.extend((bottom[i], top[i]))
        self._draw_lines(outline, vp, (0.86, 0.95, 1.0, 0.36), width=1.2)

    def _draw_hover(self, player: int, x: int, y: int, z: int, vp: Mat4, eye: Vec3):
        pos = self._slot_world(x, y, z)
        self._draw_piece(player, pos, GHOST_RADIUS, vp, eye, ghost=True, alpha=0.34)
        ring_points = self._circle_points(pos, LAST_RING_RADIUS, 48)
        self._draw_lines(ring_points, vp, (1.0, 0.82, 0.28, 0.82), width=2.0)

    def _draw_piece(self, player: int, pos: Vec3, radius: float, vp: Mat4, eye: Vec3,
                    last: bool = False, ghost: bool = False, slot: bool = False, alpha: float = 1.0):
        if slot:
            color = (0.72, 0.86, 1.0, alpha)
            emissive = 0.05
        elif player == P1:
            color = (P1_CORE[0] / 255.0, P1_CORE[1] / 255.0, P1_CORE[2] / 255.0, alpha)
            emissive = 0.10
        else:
            color = (P2_CORE[0] / 255.0, P2_CORE[1] / 255.0, P2_CORE[2] / 255.0, alpha)
            emissive = 0.10
        if ghost:
            emissive = 0.55
        if last:
            radius *= 1.05
            emissive = 0.28

        model = _model_matrix(pos, (radius, radius, radius))
        mvp = _mat_mul(vp, model)
        prog = self._sphere_prog
        prog["u_mvp"].write(_mat_pack(mvp))
        prog["u_model"].write(_mat_pack(model))
        prog["u_color"].value = color
        prog["u_light"].value = (4.0, -5.0, 8.0)
        prog["u_eye"].value = eye
        prog["u_emissive"].value = emissive
        self._sphere_vao.render(mode=mgl.TRIANGLES, vertices=self._sphere_count)

        if last:
            self._draw_lines(self._circle_points(pos, radius * 1.62, 64), vp, (1.0, 0.88, 0.42, 0.88), width=2.0)

    def _circle_points(self, center: Vec3, radius: float, segments: int) -> List[Vec3]:
        points: List[Vec3] = []
        for i in range(segments):
            a = math.tau * i / segments
            b = math.tau * (i + 1) / segments
            points.append((center[0] + math.cos(a) * radius, center[1] + math.sin(a) * radius, center[2]))
            points.append((center[0] + math.cos(b) * radius, center[1] + math.sin(b) * radius, center[2]))
        return points

    def _draw_lines(self, points: Iterable[Vec3], vp: Mat4, color: Tuple[float, float, float, float], width: float = 1.0):
        pts = list(points)
        if not pts:
            return
        data = struct.pack(f"{len(pts) * 3}f", *(c for p in pts for c in p))
        vbo = self.ctx.buffer(data)
        vao = self.ctx.vertex_array(self._flat_prog, [(vbo, "3f", "in_pos")])
        self._flat_prog["u_mvp"].write(_mat_pack(vp))
        self._flat_prog["u_color"].value = color
        self.ctx.line_width = width
        vao.render(mode=mgl.LINES, vertices=len(pts))
        vbo.release()
        vao.release()

    def _draw_triangles(self, points: Iterable[Vec3], vp: Mat4, color: Tuple[float, float, float, float]):
        pts = list(points)
        data = struct.pack(f"{len(pts) * 3}f", *(c for p in pts for c in p))
        vbo = self.ctx.buffer(data)
        vao = self.ctx.vertex_array(self._flat_prog, [(vbo, "3f", "in_pos")])
        self._flat_prog["u_mvp"].write(_mat_pack(vp))
        self._flat_prog["u_color"].value = color
        vao.render(mode=mgl.TRIANGLES, vertices=len(pts))
        vbo.release()
        vao.release()

    def _draw_hud(self, board, current_player: int, mode_text: str, _episodes: int, human_player: int, two_player: bool):
        winner = board.check_winner()
        if winner != 0:
            if two_player:
                msg = "红方获胜！" if winner == P1 else "蓝方获胜！"
            else:
                msg = "你赢了！" if winner == human_player else "AI 赢了！"
            msg += "   R 重开   M 主菜单   Q 退出"
        elif board.is_full():
            msg = "平局!   R 重开   M 主菜单   Q 退出"
        else:
            color_label = "红" if current_player == P1 else "蓝"
            if two_player:
                msg = f"轮到: {color_label}方 | {mode_text}"
            else:
                turn_label = "你" if current_player == human_player else "AI"
                msg = f"轮到: {turn_label}({color_label}) | {mode_text}"

        tip = "A/D 旋转   W/S 抬头   R 重开   M 菜单   Q 退出   +/- MCTS   [ ] AB"
        self._begin_overlay()
        self._draw_rect(18, 14, 620, 68, (0.03, 0.045, 0.075, 0.78), (0.45, 0.62, 0.82, 0.35))
        self._draw_text(msg, 36, 24, self.font, (238, 244, 255))
        self._draw_text(tip, 36, 55, self.small, (176, 190, 214))
        badge = "GPU 3D ModernGL"
        badge_w = 168
        self._draw_rect(
            self.screen.get_width() - badge_w - 24,
            self.screen.get_height() - 54,
            badge_w,
            34,
            (0.17, 0.28, 0.12, 0.78),
            (0.54, 0.92, 0.32, 0.48),
        )
        self._draw_text(badge, self.screen.get_width() - badge_w - 12, self.screen.get_height() - 47, self.small, (192, 255, 150))
        self._end_overlay()

    def _draw_column_panel(self, board, focus_col: Tuple[int, int]):
        x, y = focus_col
        next_z = board.next_free_z(x, y)
        panel_x = self.screen.get_width() - 220 - 24
        panel_y = 92
        self._begin_overlay()
        self._draw_rect(panel_x, panel_y, 220, 310, (0.035, 0.05, 0.075, 0.82), (0.45, 0.62, 0.82, 0.38))
        self._draw_text(f"列 ({x}, {y})", panel_x + 16, panel_y + 14, self.font, (236, 241, 250))
        self._draw_text("已满" if next_z is None else f"下一手 z={next_z}", panel_x + 16, panel_y + 45, self.small, (184, 198, 218))

        rail_x = panel_x + 72
        top_y = panel_y + 82
        slot_gap = 42
        self._draw_rect(rail_x - 1, top_y, 2, slot_gap * (self.Z - 1), (0.38, 0.50, 0.66, 0.52))
        last = board.moves[-1] if board.moves else None
        for display_idx, z in enumerate(range(self.Z - 1, -1, -1)):
            cy = top_y + display_idx * slot_gap
            if next_z == z:
                self._draw_rect(panel_x + 14, cy - 18, 192, 36, (1.0, 0.80, 0.22, 0.10), (1.0, 0.82, 0.25, 0.45))
            player = board.get(x, y, z)
            color = (0.36, 0.46, 0.58)
            if player == P1:
                color = tuple(c / 255 for c in P1_CORE)
            elif player == P2:
                color = tuple(c / 255 for c in P2_CORE)
            self._draw_text(f"z {z}", panel_x + 20, cy - 10, self.small, (202, 212, 230))
            self._draw_rect(rail_x - 8, cy - 8, 16, 16, (*color, 0.95), (0.85, 0.93, 1.0, 0.6))
            if next_z == z:
                self._draw_text("NEXT", panel_x + 132, cy - 10, self.small, GOLD)
            elif last is not None and (last.x, last.y, last.z) == (x, y, z):
                self._draw_text("LAST", panel_x + 132, cy - 10, self.small, (255, 255, 255))
        self._end_overlay()

    def _draw_minimap(self, board, focus_col: Optional[Tuple[int, int]]):
        panel_w = 238
        panel_h = 238
        panel_x = 22
        panel_y = self.screen.get_height() - panel_h - 22
        cell = 34
        gap = 4
        start_x = panel_x + 19
        start_y = panel_y + 48
        last = board.moves[-1] if board.moves else None

        self._begin_overlay()
        self._draw_rect(panel_x, panel_y, panel_w, panel_h, (0.035, 0.050, 0.075, 0.84), (0.42, 0.56, 0.74, 0.40))
        self._draw_text("顶视列图", panel_x + 16, panel_y + 12, self.small, (226, 235, 248))

        p1 = tuple(c / 255.0 for c in P1_CORE)
        p2 = tuple(c / 255.0 for c in P2_CORE)
        for y in range(self.Y - 1, -1, -1):
            for x in range(self.X):
                gx = start_x + x * (cell + gap)
                gy = start_y + (self.Y - 1 - y) * (cell + gap)
                is_focus = focus_col == (x, y)
                self._draw_rect(gx, gy, cell, cell, (0.070, 0.095, 0.135, 0.92), (0.32, 0.42, 0.56, 0.45))
                stripe_h = max(3, (cell - 10) // self.Z)
                for z in range(self.Z):
                    player = board.get(x, y, z)
                    if player == P1:
                        color = (*p1, 0.92)
                    elif player == P2:
                        color = (*p2, 0.92)
                    else:
                        color = (0.20, 0.25, 0.34, 0.48)
                    sy = gy + cell - 6 - (z + 1) * stripe_h
                    self._draw_rect(gx + 7, sy, cell - 14, max(2, stripe_h - 1), color)

                if last is not None and (last.x, last.y) == (x, y):
                    self._draw_rect(gx + cell // 2 - 3, gy + cell // 2 - 3, 6, 6, (1.0, 1.0, 1.0, 0.78))
                if is_focus:
                    self._draw_rect(gx - 3, gy - 3, cell + 6, cell + 6, (1.0, 0.80, 0.22, 0.12), (1.0, 0.82, 0.25, 0.85))
        self._end_overlay()

    def _begin_overlay(self):
        self.ctx.disable(mgl.DEPTH_TEST)
        self.ctx.depth_mask = False

    def _end_overlay(self):
        self.ctx.depth_mask = True
        self.ctx.enable(mgl.DEPTH_TEST)

    def _draw_rect(self, x: int, y: int, w: int, h: int, color, border=None):
        self._draw_quad(x, y, w, h, color)
        if border is not None:
            self._draw_quad(x, y, w, 1, border)
            self._draw_quad(x, y + h - 1, w, 1, border)
            self._draw_quad(x, y, 1, h, border)
            self._draw_quad(x + w - 1, y, 1, h, border)

    def _draw_text(self, text: str, x: int, y: int, font: pygame.font.Font, color):
        rgb = color if isinstance(color[0], int) else tuple(int(c * 255) for c in color[:3])
        surf = font.render(text, True, rgb).convert_alpha()
        tex = self.ctx.texture(surf.get_size(), 4, pygame.image.tostring(surf, "RGBA", True))
        tex.filter = (mgl.LINEAR, mgl.LINEAR)
        self._draw_quad(x, y, surf.get_width(), surf.get_height(), (1.0, 1.0, 1.0, 1.0), tex)
        tex.release()

    def _draw_quad(self, x: int, y: int, w: int, h: int, color, tex=None):
        sw, sh = self.screen.get_size()
        x0 = x / sw * 2.0 - 1.0
        x1 = (x + w) / sw * 2.0 - 1.0
        y0 = 1.0 - y / sh * 2.0
        y1 = 1.0 - (y + h) / sh * 2.0
        data = struct.pack(
            "24f",
            x0, y0, 0.0, 1.0,
            x0, y1, 0.0, 0.0,
            x1, y1, 1.0, 0.0,
            x0, y0, 0.0, 1.0,
            x1, y1, 1.0, 0.0,
            x1, y0, 1.0, 1.0,
        )
        self._quad_vbo.write(data)
        self._overlay_prog["u_color"].value = color
        self._overlay_prog["u_use_tex"].value = 1 if tex is not None else 0
        (tex or self._white_tex).use(0)
        self._overlay_prog["u_tex"].value = 0
        self._quad_vao.render(mode=mgl.TRIANGLES, vertices=6)

    def _sphere_program(self):
        return self.ctx.program(
            vertex_shader="""
                #version 330
                in vec3 in_pos;
                in vec3 in_norm;
                uniform mat4 u_mvp;
                uniform mat4 u_model;
                out vec3 v_norm;
                out vec3 v_world;
                void main() {
                    vec4 world = u_model * vec4(in_pos, 1.0);
                    v_world = world.xyz;
                    v_norm = mat3(u_model) * in_norm;
                    gl_Position = u_mvp * vec4(in_pos, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                in vec3 v_norm;
                in vec3 v_world;
                uniform vec4 u_color;
                uniform vec3 u_light;
                uniform vec3 u_eye;
                uniform float u_emissive;
                out vec4 fragColor;
                void main() {
                    vec3 n = normalize(v_norm);
                    vec3 l = normalize(u_light - v_world);
                    vec3 v = normalize(u_eye - v_world);
                    float diff = max(dot(n, l), 0.0);
                    vec3 r = reflect(-l, n);
                    float spec = pow(max(dot(r, v), 0.0), 38.0);
                    float rim = pow(1.0 - max(dot(n, v), 0.0), 2.2);
                    vec3 color = u_color.rgb * (0.28 + diff * 0.78);
                    color += vec3(1.0, 0.96, 0.88) * spec * 0.55;
                    color += u_color.rgb * rim * 0.42;
                    color += u_color.rgb * u_emissive;
                    fragColor = vec4(color, u_color.a);
                }
            """,
        )

    def _flat_program(self):
        return self.ctx.program(
            vertex_shader="""
                #version 330
                in vec3 in_pos;
                uniform mat4 u_mvp;
                void main() {
                    gl_Position = u_mvp * vec4(in_pos, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                uniform vec4 u_color;
                out vec4 fragColor;
                void main() {
                    fragColor = u_color;
                }
            """,
        )

    def _overlay_program(self):
        return self.ctx.program(
            vertex_shader="""
                #version 330
                in vec2 in_pos;
                in vec2 in_uv;
                out vec2 v_uv;
                void main() {
                    v_uv = in_uv;
                    gl_Position = vec4(in_pos, 0.0, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                uniform vec4 u_color;
                uniform sampler2D u_tex;
                uniform int u_use_tex;
                in vec2 v_uv;
                out vec4 fragColor;
                void main() {
                    if (u_use_tex == 1) {
                        fragColor = texture(u_tex, v_uv) * u_color;
                    } else {
                        fragColor = u_color;
                    }
                }
            """,
        )
