"""
Asset loading with graceful procedural fallbacks.

Every load attempt is isolated — a missing or corrupted file degrades
gracefully to a programmatically generated substitute, so the game always
runs regardless of asset availability.
"""
from __future__ import annotations

import os
from typing import Optional

import pygame

from .constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PIPE_WIDTH,
    PIPE_HEIGHT,
)

# Resolved once at import time so callers don't need to compute paths.
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _asset_path(filename: str) -> str:
    return os.path.join(_ASSETS_DIR, filename)


def _try_load_image(
    filename: str,
    scale: Optional[tuple[int, int]] = None,
) -> Optional[pygame.Surface]:
    """Load and optionally scale an image. Returns None on any failure."""
    path = _asset_path(filename)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, scale) if scale else img
    except pygame.error:
        return None


def _try_load_sound(filename: str) -> Optional[pygame.mixer.Sound]:
    """Load a sound file. Returns None if unavailable or mixer not ready."""
    path = _asset_path(filename)
    if not os.path.exists(path):
        return None
    try:
        return pygame.mixer.Sound(path)
    except pygame.error:
        return None


class AssetLoader:
    """
    Loads and caches all game assets.

    Callers access sprites via ``loader.sprites[key]`` (always a Surface)
    and sounds via ``loader.sounds[key]`` (a Sound or None — callers must
    guard against None before calling .play()).

    Digit sprites for the score display are in ``loader.digit_sprites``
    (list of 10 Surfaces indexed 0–9, or an empty list if unavailable).
    """

    # Target sizes for each sprite category.
    _BIRD_SIZE = (50, 50)
    _DIGIT_SIZE = (28, 40)
    _MESSAGE_SIZE = (184, 160)

    def __init__(self) -> None:
        ground_y = int(SCREEN_HEIGHT * 0.79)
        self._ground_y = ground_y
        self.sprites: dict[str, pygame.Surface] = {}
        self.sounds: dict[str, Optional[pygame.mixer.Sound]] = {}
        self.digit_sprites: list[pygame.Surface] = []
        self._load_all()

    # ── Private loaders ──────────────────────────────────────────────────────

    def _load_all(self) -> None:
        self._load_background()
        self._load_bird()
        self._load_pipes()
        self._load_ground()
        self._load_digits()
        self._load_message()
        self._load_sounds()

    def _load_background(self) -> None:
        bg = _try_load_image("Background.jpg")
        if bg:
            self.sprites["background"] = pygame.transform.smoothscale(
                bg, (SCREEN_WIDTH, SCREEN_HEIGHT)
            )
        else:
            self.sprites["background"] = _make_gradient_background()

    def _load_bird(self) -> None:
        bird = _try_load_image("bird.png", scale=self._BIRD_SIZE)
        self.sprites["bird"] = bird if bird else _make_bird_sprite()

    def _load_pipes(self) -> None:
        pipe = _try_load_image("Pipe.png", scale=(PIPE_WIDTH, PIPE_HEIGHT))
        if pipe:
            self.sprites["pipe_bottom"] = pipe
            self.sprites["pipe_top"] = pygame.transform.flip(pipe, False, True)
        else:
            top, bottom = _make_pipe_sprites()
            self.sprites["pipe_top"] = top
            self.sprites["pipe_bottom"] = bottom

    def _load_ground(self) -> None:
        base = _try_load_image("base.png")
        ground_height = SCREEN_HEIGHT - self._ground_y + 20
        if base:
            self.sprites["ground"] = pygame.transform.smoothscale(
                base, (SCREEN_WIDTH + 100, ground_height)
            )
        else:
            self.sprites["ground"] = _make_ground_sprite(
                SCREEN_WIDTH, SCREEN_HEIGHT, self._ground_y
            )

    def _load_digits(self) -> None:
        digits = [
            _try_load_image(f"{i}.png", scale=self._DIGIT_SIZE) for i in range(10)
        ]
        # Use sprite digits only if every digit loaded successfully.
        if all(d is not None for d in digits):
            self.digit_sprites = digits  # type: ignore[assignment]
        else:
            self.digit_sprites = []

    def _load_message(self) -> None:
        # message.png is used for the menu "get ready" panel. Optional.
        self.sprites["message"] = _try_load_image(
            "message.png", scale=self._MESSAGE_SIZE
        )

    def _load_sounds(self) -> None:
        sound_files: dict[str, str] = {
            "wing": "wing.mp3",
            "point": "point.mp3",
            "hit": "hit.mp3",
            "die": "Die.mp3",
            "swoosh": "swoosh.mp3",
        }
        for key, filename in sound_files.items():
            self.sounds[key] = _try_load_sound(filename)

    # ── Helper ───────────────────────────────────────────────────────────────

    def play_sound(self, key: str) -> None:
        """Play a sound by key; silently no-ops if the sound is unavailable."""
        sound = self.sounds.get(key)
        if sound is not None:
            sound.play()


# ─────────────────────────────────────────────────────────────────────────────
# Procedural asset generators (used as fallbacks)
# ─────────────────────────────────────────────────────────────────────────────

def _make_gradient_background() -> pygame.Surface:
    bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        r = max(0, min(255, int(135 - y * 0.08)))
        g = max(0, min(255, int(206 - y * 0.08)))
        b = max(0, min(255, int(235 - y * 0.04)))
        pygame.draw.line(bg, (r, g, b), (0, y), (SCREEN_WIDTH, y))
    return bg


def _make_bird_sprite() -> pygame.Surface:
    size = 34
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (255, 220, 50), (2, 2, size - 4, size - 4))
    pygame.draw.ellipse(s, (220, 180, 0), (2, 2, size - 4, size - 4), 2)
    pygame.draw.circle(s, (255, 255, 255), (22, 12), 6)
    pygame.draw.circle(s, (0, 0, 0), (24, 12), 3)
    pygame.draw.polygon(s, (255, 100, 0), [(26, 14), (32, 16), (26, 18)])
    return s


def _make_pipe_sprites() -> tuple[pygame.Surface, pygame.Surface]:
    w, h = PIPE_WIDTH, PIPE_HEIGHT
    bottom = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(bottom, (0, 200, 0), (0, 0, w, h))
    pygame.draw.rect(bottom, (0, 150, 0), (0, 0, w, h), 3)
    pygame.draw.rect(bottom, (0, 180, 0), (-2, 0, w + 4, 30))
    pygame.draw.rect(bottom, (0, 130, 0), (-2, 0, w + 4, 30), 3)
    pygame.draw.line(bottom, (100, 255, 100), (5, 30), (5, h), 3)
    top = pygame.transform.rotate(bottom, 180)
    return top, bottom


def _make_ground_sprite(sw: int, sh: int, ground_y: int) -> pygame.Surface:
    w = sw + 100
    h = sh - ground_y + 20
    ground = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(ground, (34, 139, 34), (0, 0, w, 15))
    pygame.draw.rect(ground, (139, 69, 19), (0, 15, w, h - 15))
    for i in range(0, w, 20):
        pygame.draw.line(ground, (160, 82, 45), (i, 15), (i, h), 2)
    return ground
