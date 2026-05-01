from __future__ import annotations
from typing import Optional, Tuple
from config import P1, P2, DEFAULT_EPISODES
from board3d import Board3D
from mcts_ai import MCTSAI
from alpha_beta_ai import AlphaBetaAI


class Game:
    def __init__(self):
        self.board = Board3D()
        self.current = P1

        self.two_player = False
        self.human_player = P1
        self.ai_player = P2

        self.episodes = DEFAULT_EPISODES
        self.ab_depth = 4

        self.ai_engine = "ab"
        self.ai_mcts: Optional[MCTSAI] = None
        self.ai_ab: Optional[AlphaBetaAI] = AlphaBetaAI(depth=self.ab_depth)

    def configure(self, human_first: bool = True, engine: str = "ab", two_player: bool = False):
        self.two_player = two_player
        if self.two_player:
            self.human_player = P1
            self.ai_player = 0
            self.ai_mcts = None
            self.ai_ab = None
            self.reset()
            return

        if human_first:
            self.human_player = P1
            self.ai_player = P2
        else:
            self.human_player = P2
            self.ai_player = P1
        self.ai_engine = engine if engine in ("ab", "mcts") else "ab"
        self._rebuild_ai()
        self.reset()

    def _rebuild_ai(self):
        if self.two_player:
            self.ai_mcts = None
            self.ai_ab = None
            return
        if self.ai_engine == "mcts":
            self.ai_mcts = MCTSAI(simulations=self.episodes)
            self.ai_ab = None
        else:
            self.ai_ab = AlphaBetaAI(depth=self.ab_depth)
            self.ai_mcts = None

    def reset(self):
        self.board.reset()
        self.current = P1

    def set_ai_engine(self, engine: str):
        self.ai_engine = engine if engine in ("ab", "mcts") else "ab"
        self._rebuild_ai()

    def set_episodes(self, episodes: int):
        self.episodes = max(50, min(8000, episodes))
        if self.ai_mcts is not None:
            self.ai_mcts.simulations = self.episodes

    def set_ab_depth(self, depth: int):
        self.ab_depth = max(2, min(6, depth))
        if self.ai_ab is not None:
            self.ai_ab.depth = self.ab_depth

    def mode_text(self) -> str:
        if self.two_player:
            return "双人对战"
        who = "First" if self.ai_player == P1 else "Second"
        if self.ai_engine == "mcts":
            return f"AI({who}, MCTS)"
        return f"AI({who}, AB d={self.ab_depth})"

    def is_human_turn(self) -> bool:
        if self.two_player:
            return True
        return self.current == self.human_player

    def handle_drop(self, col: Tuple[int, int]) -> bool:
        if self.board.check_winner() != 0 or self.board.is_full():
            return False
        x, y = col
        mv = self.board.drop(x, y, self.current)
        if mv is None:
            return False
        self.current = P1 if self.current == P2 else P2
        return True

    def maybe_ai_move(self):
        if self.two_player:
            return
        if self.board.check_winner() != 0 or self.board.is_full():
            return
        if self.current == self.ai_player:
            if self.ai_engine == "mcts" and self.ai_mcts is not None:
                x, y = self.ai_mcts.choose(self.board, self.ai_player)
                self.handle_drop((x, y))
            elif self.ai_engine == "ab" and self.ai_ab is not None:
                x, y = self.ai_ab.choose(self.board, self.ai_player)
                self.handle_drop((x, y))
