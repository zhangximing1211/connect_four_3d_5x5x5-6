# 3D Connect Four 5x5x5

## Project Report

### 1. Introduction

This project is a 3D board game called **3D Connect Four 5x5x5**, developed with **Python** and **Pygame**. The idea is based on the traditional Connect Four game, but the board is extended from a two-dimensional grid into a three-dimensional space. Instead of only thinking in rows and columns, players must also consider height and spatial alignment. This design makes the game more challenging, more strategic, and more suitable as a small game development project that combines programming, interface design, and artificial intelligence.

### 2. Game Design

The game board is a **5x5x5 cubic space**. A player does not place a piece freely in any position of the cube. Instead, the player selects one column on the **x-y plane**, and the piece will automatically fall to the lowest available position along the **z-axis**. This rule is simple to understand, but it creates a much deeper level of strategy because each move affects both the current layer and future stacking opportunities.

The winning condition is to connect **four pieces in a straight line**. Unlike the normal 2D version, a winning line in this game can appear in many directions: horizontal, vertical, diagonal on a plane, or even full space diagonals across the 3D board. Because of this, the game requires players to think carefully about structure, timing, and multi-layer threats.

From the visual design perspective, the project uses a rotatable camera view so that players can inspect the board from different angles. The interface also provides menu options, turn information, restart commands, and highlighted columns to make interaction clearer. Additional visual aids are used to improve z-axis reading, which is important in a 3D game because stacked pieces are harder to identify than pieces on a flat board.

### 3. Game Instructions

After launching the program, players enter the main menu and can choose one of three modes:

- **Human First**: the human player makes the first move against the AI.
- **AI First**: the AI moves first.
- **Two-Player Mode**: both sides are controlled by human players.

During the game, players use the **mouse left button** to choose a column and place a piece. The program automatically drops the piece to the correct z-axis position. The camera can be adjusted to improve visibility:

- `A / D`: rotate the view left or right
- `W / S`: tilt the camera upward or downward
- `R`: restart the current game
- `M`: return to the main menu
- `Q / ESC`: quit the game

The game also includes AI-related settings. Players can choose between **MCTS** and **Alpha-Beta** AI in the menu. If MCTS is used, the number of simulations can be adjusted. If Alpha-Beta is used, the search depth can be changed. These functions allow users to compare different AI behaviors and difficulty levels.

### 4. Technical Features

This project is not only a game, but also a simple demonstration of AI and game system design. It includes:

- 3D board representation and move validation
- win detection in multiple 3D directions
- camera projection and interactive rendering
- menu and game state switching
- support for both human-vs-human and human-vs-AI gameplay
- AI decision-making using MCTS and Alpha-Beta search

### 5. Conclusion

In conclusion, **3D Connect Four 5x5x5** is a strategy game that expands a classic game concept into three-dimensional space. The project combines rule design, user interaction, visual presentation, and AI techniques in one complete application. It is both entertaining and educational, and it demonstrates how traditional games can be redesigned into richer and more complex digital experiences.

## Requirements

- Python 3.9+
- Pygame

## Installation

```bash
python3 -m pip install pygame
```

## Run

```bash
python3 main.py
```
