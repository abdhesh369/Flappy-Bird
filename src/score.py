"""
Persistent high-score storage using JSON.

Failures are non-fatal: a corrupt or missing file is silently replaced.
Callers always receive a valid integer regardless of disk state.
"""
from __future__ import annotations

import json
import os
from typing import Union

from .constants import HIGH_SCORE_FILE


def load_high_score() -> int:
    """
    Read the persisted high score from disk.

    Returns:
        The stored high score, or 0 if the file is absent or unreadable.
    """
    if not os.path.exists(HIGH_SCORE_FILE):
        return 0
    try:
        with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return max(0, int(data.get("high_score", 0)))
    except (json.JSONDecodeError, ValueError, OSError, TypeError):
        return 0


def save_high_score(score: int) -> None:
    """
    Persist the high score to disk.

    Args:
        score: The new high score to write.

    Disk errors are silently swallowed — the game must remain playable even
    on read-only file systems or when running from a protected directory.
    """
    try:
        with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as fh:
            json.dump({"high_score": score}, fh)
    except OSError:
        pass
