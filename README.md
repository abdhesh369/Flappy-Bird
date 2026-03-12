# Flappy Bird

A polished Python/Pygame clone of the classic mobile game.

## Requirements

- Python 3.9+
- pygame ≥ 2.1.0

## Setup

```bash
# 1. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the game
python main.py
```

## Controls

| Input | Action |
|---|---|
| `Space` / `↑` / Click | Flap |
| `ESC` or `P` | Pause / Resume |
| `ESC` on menu | Quit |

## Project Structure

```
FlappyBird/
├── assets/             Game assets (sprites, sounds)
├── src/
│   ├── constants.py    All constants and the GameState enum
│   ├── entities.py     Bird, Pipe, Particle classes
│   ├── assets.py       Asset loader with procedural fallbacks
│   ├── score.py        High-score persistence (JSON)
│   └── game.py         Main game loop and state machine
├── tests/
│   ├── test_entities.py  Physics and collision unit tests
│   └── test_score.py     Persistence round-trip tests
├── main.py             Entry point
├── requirements.txt
└── README.md
```

## Running Tests

```bash
pytest tests/ -v
```

Tests run headlessly via SDL dummy drivers — no display required.

## Features

- Persistent high score saved to `high_score.json`
- Pause / resume with `ESC` or `P`
- Screen shake + particle burst on death
- Digit-sprite score display
- Difficulty ramp (speed + spawn rate increase every 5 points)
- Graceful asset fallbacks (runs without any asset files)
