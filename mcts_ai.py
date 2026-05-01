from __future__ import annotations
import math, random
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
from board3d import Board3D
from config import P1, P2, MAX_ROLLOUT_STEPS

def other(p:int) -> int:
    return P1 if p == P2 else P2

def center_score(move: Tuple[int,int], X:int, Y:int) -> float:
    # prefer center columns
    cx = (X - 1) * 0.5
    cy = (Y - 1) * 0.5
    x,y = move
    return -((x - cx)**2 + (y - cy)**2)

def immediate_winning_moves(board: Board3D, player:int) -> List[Tuple[int,int]]:
    wins = []
    for m in board.valid_moves():
        board.drop(m[0], m[1], player)
        if board.check_winner() == player:
            wins.append(m)
        board.undo()
    return wins

def immediate_block_moves(board: Board3D, player:int) -> List[Tuple[int,int]]:
    # moves that prevent opponent immediate win: if opponent has a winning response, block that column now
    opp = other(player)
    opp_wins = set(immediate_winning_moves(board, opp))
    if not opp_wins:
        return []
    # blocking means playing in one of those (x,y) columns (because gravity: only that column matters)
    return list(opp_wins)

def rollout_policy_move(board: Board3D, player:int) -> Tuple[int,int]:
    # 1) take win if exists
    wins = immediate_winning_moves(board, player)
    if wins:
        return random.choice(wins)
    # 2) block opponent win if needed
    blocks = immediate_block_moves(board, player)
    if blocks:
        return random.choice(blocks)
    # 3) otherwise, biased random toward center
    moves = board.valid_moves()
    X = 5  # board is 5x5 in this project; kept explicit for speed/stability
    Y = 5
    # softmax-like sampling by center preference
    scores = [center_score(m, X, Y) for m in moves]
    mx = max(scores)
    weights = [math.exp((s-mx)*0.35) for s in scores]
    total = sum(weights)
    r = random.random()*total
    acc = 0.0
    for m,w in zip(moves,weights):
        acc += w
        if acc >= r:
            return m
    return moves[-1]

@dataclass
class Node:
    parent: Optional["Node"]
    move: Optional[Tuple[int,int]]
    visits: int = 0
    value: float = 0.0          # accumulated reward from root player's perspective
    children: Optional[Dict[Tuple[int,int], "Node"]] = None
    untried: Optional[List[Tuple[int,int]]] = None

    def __post_init__(self):
        self.children = {} if self.children is None else self.children
        self.untried = [] if self.untried is None else self.untried

class MCTSAI:
    """Stronger MCTS with tactical checks + biased rollouts.
    - Before search: if there is an immediate win, take it. If opponent has immediate win, block it.
    - During rollouts: win/block/center-biased policy (instead of pure random).
    """
    def __init__(self, simulations:int=500, c:float=1.35):
        self.simulations = simulations
        self.c = c

    def choose(self, board: Board3D, player:int) -> Tuple[int,int]:
        valid_moves = board.valid_moves()
        if not valid_moves:
            raise ValueError("MCTSAI.choose called with no legal moves")

        # Tactical pre-checks
        wins = immediate_winning_moves(board, player)
        if wins:
            return random.choice(wins)
        blocks = immediate_block_moves(board, player)
        if blocks:
            return random.choice(blocks)

        root = Node(parent=None, move=None)
        root.untried = valid_moves.copy()
        root_player = player

        for _ in range(self.simulations):
            b = board.clone()
            node = root
            p = player

            # Selection
            while (not node.untried) and node.children:
                node = self._uct_select(node)
                b.drop(node.move[0], node.move[1], p)
                p = other(p)

            # Expansion
            if node.untried:
                # progressive bias: prefer center moves during expansion
                moves = node.untried
                # sample from top-k by center score
                X = 5; Y = 5
                scored = sorted(moves, key=lambda m: center_score(m,X,Y), reverse=True)
                k = min(6, len(scored))
                m = random.choice(scored[:k])
                node.untried.remove(m)

                b.drop(m[0], m[1], p)
                p = other(p)
                child = Node(parent=node, move=m)
                child.untried = b.valid_moves()
                node.children[m] = child
                node = child

            # Rollout
            winner = b.check_winner()
            steps = 0
            while winner == 0 and (not b.is_full()) and steps < MAX_ROLLOUT_STEPS:
                mv = rollout_policy_move(b, p)
                b.drop(mv[0], mv[1], p)
                winner = b.check_winner()
                p = other(p)
                steps += 1

            # Backprop (root perspective)
            if winner == root_player:
                reward = 1.0
            elif winner == 0:
                reward = 0.5
            else:
                reward = 0.0

            while node is not None:
                node.visits += 1
                node.value += reward
                node = node.parent

        if not root.children:
            return random.choice(valid_moves)

        # choose by highest visit count, tie-break by value
        best_move = None
        best_visits = -1
        best_value = -1e18
        for m, ch in root.children.items():
            if ch.visits > best_visits or (ch.visits == best_visits and ch.value > best_value):
                best_visits = ch.visits
                best_value = ch.value
                best_move = m
        if best_move is None:
            return random.choice(valid_moves)
        return best_move

    def _uct_select(self, node: Node) -> Node:
        logN = math.log(max(1, node.visits))
        best_child = None
        best_score = -1e18
        for ch in node.children.values():
            if ch.visits == 0:
                score = 1e9
            else:
                exploit = ch.value / ch.visits
                explore = self.c * math.sqrt(logN / ch.visits)
                score = exploit + explore
            if score > best_score:
                best_score = score
                best_child = ch
        if best_child is None:
            raise RuntimeError("UCT selection called on a node without children")
        return best_child
