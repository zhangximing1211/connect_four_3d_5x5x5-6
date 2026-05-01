from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import math, random
from board3d import Board3D
from config import P1, P2, CONNECT_N, X_SIZE, Y_SIZE, Z_SIZE

def other(p:int) -> int:
    return P1 if p == P2 else P2

def in_bounds(x:int,y:int,z:int) -> bool:
    return 0 <= x < X_SIZE and 0 <= y < Y_SIZE and 0 <= z < Z_SIZE

DIRS = [
    (1,0,0),(0,1,0),(0,0,1),
    (1,1,0),(1,-1,0),
    (1,0,1),(1,0,-1),
    (0,1,1),(0,1,-1),
    (1,1,1),(1,1,-1),(1,-1,1),(1,-1,-1),
]

def precompute_lines() -> List[List[Tuple[int,int,int]]]:
    lines=[]
    for x in range(X_SIZE):
        for y in range(Y_SIZE):
            for z in range(Z_SIZE):
                for dx,dy,dz in DIRS:
                    ex = x + (CONNECT_N-1)*dx
                    ey = y + (CONNECT_N-1)*dy
                    ez = z + (CONNECT_N-1)*dz
                    if in_bounds(ex,ey,ez):
                        lines.append([(x+k*dx, y+k*dy, z+k*dz) for k in range(CONNECT_N)])
    return lines

LINES = precompute_lines()

# You can tune W[3] here
W = {0:0, 1:1, 2:14, 3:220, 4:100000}

# --- Opening phase control (cheap strength boost, low compute) ---
# In the first OPENING_PLIES half-moves, we discourage stacking in z more aggressively
# to improve x-y coverage for territory control.
OPENING_PLIES = 14          # ~7 moves each side
OPENING_Z_PENALTY_MULT = 2.0


def center_bonus(x:int,y:int) -> float:
    cx = (X_SIZE-1)*0.5
    cy = (Y_SIZE-1)*0.5
    return -((x-cx)**2 + (y-cy)**2)

def z_for_move(board: Board3D, m: Tuple[int,int]) -> int:
    z = board.next_free_z(m[0], m[1])
    return z if z is not None else 999

def immediate_wins(board: Board3D, player:int) -> List[Tuple[int,int]]:
    wins=[]
    for (x,y) in board.valid_moves():
        board.drop(x,y,player)
        if board.check_winner() == player:
            wins.append((x,y))
        board.undo()
    return wins

def count_immediate_wins_after(board: Board3D, player:int) -> int:
    c = 0
    for (x,y) in board.valid_moves():
        board.drop(x,y,player)
        if board.check_winner() == player:
            c += 1
        board.undo()
    return c

def fork_moves(board: Board3D, player:int) -> List[Tuple[int,int]]:
    forks=[]
    for (x,y) in board.valid_moves():
        board.drop(x,y,player)
        if board.check_winner() != player:
            if count_immediate_wins_after(board, player) >= 2:
                forks.append((x,y))
        board.undo()
    return forks

def evaluate(board: Board3D, root:int) -> float:
    opp = other(root)
    score = 0.0

    for seg in LINES:
        rc = 0
        oc = 0
        for x,y,z in seg:
            v = board.get(x,y,z)
            if v == root:
                rc += 1
            elif v == opp:
                oc += 1
        if rc and oc:
            continue
        if rc:
            score += W[rc]
        elif oc:
            # defense coefficient is here: 1.15 -> 1.25 to defend harder
            score -= W[oc] * 1.15

    for x in range(X_SIZE):
        for y in range(Y_SIZE):
            tz = board.top_z(x,y)
            if tz >= 0:
                v = board.get(x,y,tz)
                if v == root:
                    score += 0.35 * center_bonus(x,y)
                elif v == opp:
                    score -= 0.35 * center_bonus(x,y)

    # z-height regularizer: discourage wasting moves on vertical stacking early
    mult = OPENING_Z_PENALTY_MULT if len(board.moves) < OPENING_PLIES else 1.0
    for x in range(X_SIZE):
        for y in range(Y_SIZE):
            top = board.top_z(x,y)
            for z in range(top+1):
                v = board.get(x,y,z)
                if v == root:
                    score -= (0.35 * mult) * z
                elif v == opp:
                    score += 0.10 * z
    return score


_rng = random.Random(1337)
_Z = [[[[_rng.getrandbits(64) for _ in range(3)] for _ in range(Z_SIZE)] for _ in range(Y_SIZE)] for _ in range(X_SIZE)]

def board_hash(board: Board3D) -> int:
    h = 0
    for x in range(X_SIZE):
        for y in range(Y_SIZE):
            top = board.top_z(x,y)
            for z in range(top+1):
                v = board.get(x,y,z)
                h ^= _Z[x][y][z][v]
    return h

EXACT = 0
LOWER = 1
UPPER = 2

@dataclass
class TTEntry:
    depth: int
    value: float
    flag: int
    best_move: Optional[Tuple[int,int]]

@dataclass
class AlphaBetaAI:
    depth: int = 4
    tt_size: int = 200000
    use_forks: bool = True

    def __post_init__(self):
        self.tt: Dict[int, TTEntry] = {}

    def choose(self, board: Board3D, player:int) -> Tuple[int,int]:
        self.tt.clear()
        legal_moves = board.valid_moves()
        if not legal_moves:
            raise ValueError("AlphaBetaAI.choose called with no legal moves")

        # --- 禁止 AI 第一步走 z 轴（只能落在空柱子上）---
        if player == P2 and board.moves and len(board.moves) == 1:
            legal = [(x, y) for (x, y) in legal_moves if board.next_free_z(x, y) == 0]
            if legal:
                return max(legal, key=lambda m: center_bonus(m[0], m[1]))


        wins = immediate_wins(board, player)
        if wins:
            return max(wins, key=lambda m: center_bonus(m[0],m[1]))

        blocks = immediate_wins(board, other(player))
        if blocks:
            return max(blocks, key=lambda m: center_bonus(m[0],m[1]))

        if self.use_forks:
            forks = fork_moves(board, player)
            if forks:
                return max(forks, key=lambda m: center_bonus(m[0],m[1]))
            opp_forks = set(fork_moves(board, other(player)))
            if opp_forks:
                direct = [m for m in board.valid_moves() if m in opp_forks]
                if direct:
                    return max(direct, key=lambda m: center_bonus(m[0],m[1]))

        moves = self._ordered_moves(board, legal_moves, player, pv_move=None)

        best_move = moves[0]
        best_val = -math.inf
        alpha = -math.inf
        beta = math.inf

        for m in moves:
            board.drop(m[0], m[1], player)
            val = self._search(board, other(player), self.depth - 1, alpha, beta, root=player)
            board.undo()
            if val > best_val:
                best_val = val
                best_move = m
            alpha = max(alpha, val)
            if alpha >= beta:
                break
        return best_move

    def _ordered_moves(self, board: Board3D, moves: List[Tuple[int,int]], player:int, pv_move: Optional[Tuple[int,int]]) -> List[Tuple[int,int]]:
        opp = other(player)
        scored=[]
        for m in moves:
            s = 0.0
            if pv_move is not None and m == pv_move:
                s += 1e6

            # Prefer lower z (spread on x-y plane) unless tactics override
                        # Opening-aware: punish high-z stacking more in the first OPENING_PLIES plies
            z = z_for_move(board, m)
            mult = OPENING_Z_PENALTY_MULT if len(board.moves) < OPENING_PLIES else 1.0
            s -= 250.0 * mult * z
            board.drop(m[0], m[1], player)
            if board.check_winner() == player:
                s += 9e5
            board.undo()

            board.drop(m[0], m[1], opp)
            if board.check_winner() == opp:
                s += 6e5
            board.undo()

            s += 220.0 * center_bonus(m[0],m[1])
            scored.append((s,m))
        scored.sort(reverse=True, key=lambda t:t[0])
        return [m for _,m in scored]

    def _search(self, board: Board3D, to_move:int, depth:int, alpha:float, beta:float, root:int) -> float:
        winner = board.check_winner()
        if winner != 0:
            if winner == root:
                return 1e6 + depth*30
            else:
                return -1e6 - depth*30
        if board.is_full():
            return 0.0
        if depth <= 0:
            return evaluate(board, root)

        h = board_hash(board) ^ (to_move * 0x9e3779b97f4a7c15)
        ent = self.tt.get(h)
        if ent is not None and ent.depth >= depth:
            if ent.flag == EXACT:
                return ent.value
            if ent.flag == LOWER:
                alpha = max(alpha, ent.value)
            elif ent.flag == UPPER:
                beta = min(beta, ent.value)
            if alpha >= beta:
                return ent.value

        iw = immediate_wins(board, to_move)
        if iw:
            if to_move == root:
                return 1e6 + depth*30
            else:
                return -1e6 - depth*30

        pv = ent.best_move if ent is not None else None
        moves = self._ordered_moves(board, board.valid_moves(), to_move, pv_move=pv)

        maximizing = to_move == root
        best = -math.inf if maximizing else math.inf
        best_move = moves[0]
        orig_alpha = alpha
        orig_beta = beta

        for m in moves:
            board.drop(m[0], m[1], to_move)
            val = self._search(board, other(to_move), depth - 1, alpha, beta, root)
            board.undo()

            if maximizing:
                if val > best:
                    best = val
                    best_move = m
                if val > alpha:
                    alpha = val
            else:
                if val < best:
                    best = val
                    best_move = m
                if val < beta:
                    beta = val
            if alpha >= beta:
                break

        flag = EXACT
        if best <= orig_alpha:
            flag = UPPER
        elif best >= orig_beta:
            flag = LOWER

        if len(self.tt) >= self.tt_size:
            self.tt.clear()
        self.tt[h] = TTEntry(depth=depth, value=best, flag=flag, best_move=best_move)
        return best
