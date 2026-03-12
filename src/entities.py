"""
Game entities: Bird, Pipe, Particle.

Each class is responsible for its own physics, collision geometry, and rendering.
No game-state logic lives here — entities are pure data + behaviour.
"""
from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from .constants import (
    GRAVITY,
    FLAP_STRENGTH,
    MAX_FALL_VELOCITY,
    MAX_RISE_VELOCITY,
    FLAP_COOLDOWN_FRAMES,
    HITBOX_MARGIN,
    PIPE_GAP,
)


# ─────────────────────────────────────────────────────────────────────────────
# Bird
# ─────────────────────────────────────────────────────────────────────────────

class Bird:
    """
    Player-controlled bird with Euler-integrated gravity and sprite rotation.

    Physics notes:
    - Velocity increases each frame by GRAVITY (positive = falling).
    - FLAP_STRENGTH is negative (upward), clamped to MAX_RISE_VELOCITY.
    - A cooldown prevents spam-flapping from negating gravity entirely.
    - The hitbox is intentionally smaller than the visible sprite to avoid
      penalising the player for transparent sprite corners.
    """

    def __init__(self, x: int, y: int, sprite: pygame.Surface) -> None:
        self.x: int = x
        self.y: float = float(y)
        self.sprite = sprite
        self.width: int = sprite.get_width()
        self.height: int = sprite.get_height()

        self.velocity: float = 0.0
        self.angle: float = 0.0
        self._flap_cooldown: int = 0

    # ── Public interface ─────────────────────────────────────────────────────

    def flap(self) -> bool:
        """
        Apply upward impulse.

        Returns:
            True if the flap was accepted; False if still in cooldown.
        """
        if self._flap_cooldown > 0:
            return False
        self.velocity = FLAP_STRENGTH
        self._flap_cooldown = FLAP_COOLDOWN_FRAMES
        return True

    def update(self) -> None:
        """Advance physics by one simulation frame."""
        self.velocity = max(
            MAX_RISE_VELOCITY,
            min(self.velocity + GRAVITY, MAX_FALL_VELOCITY),
        )
        self.y += self.velocity
        self.angle = max(-30.0, min(self.velocity * 3.0, 90.0))
        if self._flap_cooldown > 0:
            self._flap_cooldown -= 1

    def get_rect(self) -> pygame.Rect:
        """
        Return a margin-shrunk hitbox.

        The sprite has transparent padding around the bird shape; using the
        full bounding box would result in phantom collisions. HITBOX_MARGIN
        trims each edge so collisions only register on the visible body.
        """
        m = HITBOX_MARGIN
        return pygame.Rect(
            self.x + m,
            int(self.y) + m,
            self.width - m * 2,
            self.height - m * 2,
        )

    def draw(self, surface: pygame.Surface) -> None:
        rotated = pygame.transform.rotate(self.sprite, -self.angle)
        rect = rotated.get_rect(
            center=(self.x + self.width // 2, int(self.y) + self.height // 2)
        )
        surface.blit(rotated, rect.topleft)


# ─────────────────────────────────────────────────────────────────────────────
# Pipe
# ─────────────────────────────────────────────────────────────────────────────

class Pipe:
    """
    A vertically positioned pair of pipe obstacles with a navigable gap.

    The gap is centred on `gap_y`. The top pipe hangs down from above; the
    bottom pipe rises from below. Both share the same x-position and velocity.
    """

    def __init__(
        self,
        x: int,
        gap_y: int,
        top_sprite: pygame.Surface,
        bottom_sprite: pygame.Surface,
        velocity: float,
    ) -> None:
        self.x: float = float(x)
        self.gap_y: int = gap_y
        self._top = top_sprite
        self._bottom = bottom_sprite
        self.velocity = velocity
        self.width: int = top_sprite.get_width()
        self.height: int = top_sprite.get_height()
        self.passed: bool = False  # Set True once the bird has cleared this pipe

    # ── Public interface ─────────────────────────────────────────────────────

    def update(self) -> None:
        """Move the pipe left by one velocity step."""
        self.x += self.velocity

    def get_top_rect(self) -> pygame.Rect:
        top_y = self.gap_y - PIPE_GAP // 2 - self.height
        return pygame.Rect(int(self.x), top_y, self.width, self.height)

    def get_bottom_rect(self) -> pygame.Rect:
        bottom_y = self.gap_y + PIPE_GAP // 2
        return pygame.Rect(int(self.x), bottom_y, self.width, self.height)

    def is_off_screen(self) -> bool:
        """True once the pipe has fully exited the left edge of the screen."""
        return self.x + self.width < 0

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._top, self.get_top_rect().topleft)
        surface.blit(self._bottom, self.get_bottom_rect().topleft)


# ─────────────────────────────────────────────────────────────────────────────
# Particle
# ─────────────────────────────────────────────────────────────────────────────

class Particle:
    """
    A single debris particle ejected radially from the bird on death.

    Lifetime fades both alpha and radius for a natural dissolve effect.
    """

    _COLORS = [
        (255, 200, 0),
        (255, 240, 60),
        (255, 140, 0),
        (255, 255, 200),
        (255, 255, 255),
    ]

    def __init__(self, x: float, y: float) -> None:
        angle = random.uniform(0.0, 360.0)
        speed = random.uniform(2.0, 7.0)
        self.x: float = x
        self.y: float = y
        self.vx: float = math.cos(math.radians(angle)) * speed
        self.vy: float = math.sin(math.radians(angle)) * speed - 2.0  # Slight upward bias
        self.max_lifetime: int = random.randint(25, 50)
        self.lifetime: int = self.max_lifetime
        self.color = random.choice(self._COLORS)
        self.radius: int = random.randint(3, 6)

    def update(self) -> None:
        self.vy += 0.35  # Particle-specific gravity
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    @property
    def is_dead(self) -> bool:
        return self.lifetime <= 0

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.lifetime / self.max_lifetime
        alpha = int(255 * progress)
        r = max(1, int(self.radius * progress))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (r, r), r)
        surface.blit(surf, (int(self.x) - r, int(self.y) - r))
