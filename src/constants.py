"""
Game-wide constants and enumerations.

All magic numbers live here. If a value needs to change, change it once.
"""
from enum import Enum, auto

# ── Display ──────────────────────────────────────────────────────────────────
FPS: int = 60
SCREEN_WIDTH: int = 400
SCREEN_HEIGHT: int = 700
GROUND_Y_RATIO: float = 0.79   # Ground starts at this fraction of screen height

# ── Pipe mechanics ───────────────────────────────────────────────────────────
PIPE_GAP: int = 160             # Vertical opening between top and bottom pipe
PIPE_FREQUENCY_MS: int = 1500   # Milliseconds between pipe spawns at base difficulty
PIPE_FREQUENCY_MIN_MS: int = 800
PIPE_VELOCITY_BASE: float = -3.0
PIPE_VELOCITY_MIN: float = -8.0
PIPE_WIDTH: int = 52
PIPE_HEIGHT: int = 400
SCORE_PER_DIFFICULTY_STEP: int = 5  # Score increment that triggers a difficulty increase

# ── Bird physics ─────────────────────────────────────────────────────────────
GRAVITY: float = 0.5
FLAP_STRENGTH: float = -8.0     # Instantaneous upward velocity applied on flap
MAX_FALL_VELOCITY: float = 10.0 # Terminal downward velocity (positive = down)
MAX_RISE_VELOCITY: float = -8.0 # Terminal upward velocity (negative = up)
FLAP_COOLDOWN_FRAMES: int = 10  # Frames the player must wait before flapping again
HITBOX_MARGIN: int = 4          # Pixels trimmed from each side of the sprite for the hitbox

# ── Game feel ────────────────────────────────────────────────────────────────
GRACE_PERIOD_MS: int = 500      # Invincibility window at game start (milliseconds)
SCREEN_SHAKE_FRAMES: int = 12   # How many frames the screen shakes after death
SCREEN_SHAKE_INTENSITY: int = 6 # Maximum pixel offset during shake

# ── Persistence ──────────────────────────────────────────────────────────────
HIGH_SCORE_FILE: str = "high_score.json"

# ── Colours ──────────────────────────────────────────────────────────────────
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (255, 215, 0)
RED_BRIGHT = (255, 50, 50)
TRANSPARENT_BLACK = (0, 0, 0, 180)


class GameState(Enum):
    """Explicit state machine — no raw strings, no silent typo bugs."""
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
