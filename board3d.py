from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from config import X_SIZE, Y_SIZE, Z_SIZE, CONNECT_N, EMPTY

DIRS = [
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 1, 0),
    (1, -1, 0),
    (1, 0, 1),
    (1, 0, -1),
    (0, 1, 1),
    (0, 1, -1),
    (1, 1, 1),
    (1, 1, -1),
    (1, -1, 1),
    (1, -1, -1),
]

def in_bounds(x:int, y:int, z:int) -> bool:
    return 0 <= x < X_SIZE and 0 <= y < Y_SIZE and 0 <= z < Z_SIZE

def in_bounds_xy(x:int, y:int) -> bool:
    return 0 <= x < X_SIZE and 0 <= y < Y_SIZE

def idx(x:int, y:int, z:int) -> int:
    return (x * Y_SIZE + y) * Z_SIZE + z

@dataclass(frozen=True)
class Move:
    x: int
    y: int
    z: int
    player: int

class Board3D:
    def __init__(self):
        self.cells: List[int] = [EMPTY] * (X_SIZE * Y_SIZE * Z_SIZE)
        self.heights: List[int] = [0] * (X_SIZE * Y_SIZE)  # next free z
        self.moves: List[Move] = []

    def reset(self):
        for i in range(len(self.cells)):
            self.cells[i] = EMPTY
        for i in range(len(self.heights)):
            self.heights[i] = 0
        self.moves.clear()

    def get(self, x:int, y:int, z:int) -> int:
        return self.cells[idx(x,y,z)]

    def set(self, x:int, y:int, z:int, v:int):
        self.cells[idx(x,y,z)] = v

    def next_free_z(self, x:int, y:int) -> Optional[int]:
        if not in_bounds_xy(x, y):
            return None
        h = self.heights[x * Y_SIZE + y]
        return h if h < Z_SIZE else None

    def top_z(self, x:int, y:int) -> int:
        if not in_bounds_xy(x, y):
            return -1
        return self.heights[x * Y_SIZE + y] - 1

    def valid_moves(self) -> List[Tuple[int,int]]:
        out = []
        for x in range(X_SIZE):
            for y in range(Y_SIZE):
                if self.heights[x * Y_SIZE + y] < Z_SIZE:
                    out.append((x,y))
        return out

    def drop(self, x:int, y:int, player:int) -> Optional[Move]:
        if not in_bounds_xy(x, y) or player == EMPTY:
            return None
        col = x * Y_SIZE + y
        z = self.heights[col]
        if z >= Z_SIZE:
            return None
        self.set(x,y,z,player)
        self.heights[col] += 1
        mv = Move(x,y,z,player)
        self.moves.append(mv)
        return mv

    def undo(self) -> Optional[Move]:
        if not self.moves:
            return None
        mv = self.moves.pop()
        col = mv.x * Y_SIZE + mv.y
        self.heights[col] -= 1
        self.set(mv.x, mv.y, mv.z, EMPTY)
        return mv

    def is_full(self) -> bool:
        return all(h >= Z_SIZE for h in self.heights)

    def check_winner(self) -> int:
        if not self.moves:
            return 0
        mv = self.moves[-1]
        return mv.player if self._win_from(mv.x, mv.y, mv.z, mv.player) else 0

    def _count_dir(self, x:int, y:int, z:int, dx:int, dy:int, dz:int, player:int) -> int:
        c = 0
        nx, ny, nz = x + dx, y + dy, z + dz
        while in_bounds(nx,ny,nz) and self.get(nx,ny,nz) == player:
            c += 1
            nx += dx; ny += dy; nz += dz
        return c

    def _win_from(self, x:int, y:int, z:int, player:int) -> bool:
        for dx,dy,dz in DIRS:
            a = self._count_dir(x,y,z, dx,dy,dz, player)
            b = self._count_dir(x,y,z, -dx,-dy,-dz, player)
            if 1 + a + b >= CONNECT_N:
                return True
        return False

    def clone(self) -> "Board3D":
        b = Board3D()
        b.cells = self.cells.copy()
        b.heights = self.heights.copy()
        b.moves = self.moves.copy()
        return b
