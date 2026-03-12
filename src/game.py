"""
Core game orchestrator.

Owns the main loop and coordinates between the entity layer, the asset
loader, and the score persistence module.  All game-state transitions
happen here; entities remain unaware of state.
"""
from __future__ import annotations

import random
import sys
from typing import Optional

import pygame
from pygame.locals import (
    QUIT,
    KEYDOWN,
    MOUSEBUTTONDOWN,
    K_ESCAPE,
    K_SPACE,
    K_UP,
    K_RETURN,
    K_p,
)

from .constants import (
    FPS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    GROUND_Y_RATIO,
    PIPE_GAP,
    PIPE_FREQUENCY_MS,
    PIPE_FREQUENCY_MIN_MS,
    PIPE_VELOCITY_BASE,
    PIPE_VELOCITY_MIN,
    SCORE_PER_DIFFICULTY_STEP,
    GRACE_PERIOD_MS,
    SCREEN_SHAKE_FRAMES,
    SCREEN_SHAKE_INTENSITY,
    WHITE,
    BLACK,
    GOLD,
    RED_BRIGHT,
    GameState,
)
from .entities import Bird, Pipe, Particle
from .assets import AssetLoader
from .score import load_high_score, save_high_score


class Game:
    """
    Top-level game object.

    Lifecycle:
        game = Game()
        game.run()         # blocks until the window is closed

    Responsibilities:
    - Initialise pygame and create the window.
    - Load assets once via AssetLoader.
    - Drive the state machine (MENU → PLAYING ⇄ PAUSED → GAME_OVER → …).
    - Delegate rendering and physics to entity classes.
    """

    GROUND_Y: int = int(SCREEN_HEIGHT * GROUND_Y_RATIO)

    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init()

        self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._render_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Flappy Bird")

        self._clock = pygame.time.Clock()
        self._font_score = pygame.font.Font(None, 72)
        self._font_ui = pygame.font.Font(None, 48)
        self._font_small = pygame.font.Font(None, 32)

        self._assets = AssetLoader()
        self._high_score: int = load_high_score()

        # Runtime state — populated by _reset()
        self._state: GameState = GameState.MENU
        self._bird: Optional[Bird] = None
        self._pipes: list[Pipe] = []
        self._particles: list[Particle] = []
        self._score: int = 0
        self._difficulty: int = 1
        self._pipe_velocity: float = PIPE_VELOCITY_BASE
        self._pipe_frequency_ms: int = PIPE_FREQUENCY_MS
        self._last_pipe_time: int = 0
        self._grace_deadline: int = 0
        self._ground_x: float = 0.0
        self._shake_frames: int = 0
        self._bird_bob_angle: float = 0.0  # For menu idle animation

        self._reset()

    # ── Public ────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Block and run the game loop until the window is closed."""
        while True:
            self._handle_events()
            self._update()
            self._draw()
            self._clock.tick(FPS)

    # ── Private: state management ─────────────────────────────────────────────

    def _reset(self) -> None:
        """Reset all mutable state for a fresh game session."""
        self._bird = Bird(80, SCREEN_HEIGHT // 2, self._assets.sprites["bird"])
        self._pipes.clear()
        self._particles.clear()
        self._score = 0
        self._difficulty = 1
        self._pipe_velocity = PIPE_VELOCITY_BASE
        self._pipe_frequency_ms = PIPE_FREQUENCY_MS
        self._last_pipe_time = pygame.time.get_ticks()
        self._grace_deadline = pygame.time.get_ticks() + GRACE_PERIOD_MS
        self._ground_x = 0.0
        self._shake_frames = 0

    def _start_playing(self) -> None:
        self._assets.play_sound("swoosh")
        self._state = GameState.PLAYING
        self._last_pipe_time = pygame.time.get_ticks()
        self._grace_deadline = pygame.time.get_ticks() + GRACE_PERIOD_MS
        assert self._bird is not None
        self._bird.flap()
        self._assets.play_sound("wing")

    def _trigger_death(self) -> None:
        """Handle collision: spawn particles, shake screen, update high score."""
        assert self._bird is not None
        cx = self._bird.x + self._bird.width // 2
        cy = int(self._bird.y) + self._bird.height // 2
        self._particles = [Particle(cx, cy) for _ in range(20)]
        self._shake_frames = SCREEN_SHAKE_FRAMES
        self._assets.play_sound("hit")
        self._assets.play_sound("die")
        if self._score > self._high_score:
            self._high_score = self._score
            save_high_score(self._high_score)
        self._state = GameState.GAME_OVER

    # ── Private: update ───────────────────────────────────────────────────────

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == QUIT:
                self._quit()

            if event.type == KEYDOWN:
                self._on_key(event.key)

            if event.type == MOUSEBUTTONDOWN:
                self._on_action()

    def _on_key(self, key: int) -> None:
        if key == K_ESCAPE:
            if self._state == GameState.PLAYING:
                self._state = GameState.PAUSED
                self._assets.play_sound("swoosh")
            elif self._state == GameState.PAUSED:
                self._state = GameState.PLAYING
                self._assets.play_sound("swoosh")
            elif self._state == GameState.MENU:
                self._quit()
            return

        if key == K_p and self._state in (GameState.PLAYING, GameState.PAUSED):
            self._state = (
                GameState.PAUSED
                if self._state == GameState.PLAYING
                else GameState.PLAYING
            )
            self._assets.play_sound("swoosh")
            return

        if key in (K_SPACE, K_UP, K_RETURN):
            self._on_action()

    def _on_action(self) -> None:
        """Unified handler for Space / Up / Click / Enter."""
        if self._state == GameState.MENU:
            self._start_playing()
        elif self._state == GameState.PLAYING:
            assert self._bird is not None
            if self._bird.flap():
                self._assets.play_sound("wing")
        elif self._state == GameState.GAME_OVER:
            self._reset()
            self._start_playing()

    def _update(self) -> None:
        if self._state == GameState.PLAYING:
            self._update_playing()
        elif self._state == GameState.MENU:
            self._bird_bob_angle += 0.05
        # Particles keep updating in GAME_OVER for visual continuity.
        if self._state == GameState.GAME_OVER:
            self._particles = [p for p in self._particles if not p.is_dead]
            for p in self._particles:
                p.update()
        if self._shake_frames > 0:
            self._shake_frames -= 1

    def _update_playing(self) -> None:
        assert self._bird is not None

        self._bird.update()

        # Spawn pipes on a time-based interval (not frame-count, so FPS changes
        # don't affect game feel).
        now = pygame.time.get_ticks()
        if now - self._last_pipe_time > self._pipe_frequency_ms:
            self._spawn_pipe()
            self._last_pipe_time = now

        for pipe in self._pipes:
            pipe.update()
            if not pipe.passed and pipe.x + pipe.width < self._bird.x:
                pipe.passed = True
                self._score += 1
                self._assets.play_sound("point")
                self._update_difficulty()

        self._pipes = [p for p in self._pipes if not p.is_off_screen()]

        # Scroll ground — carry sub-pixel remainder to avoid stuttering.
        self._ground_x -= abs(self._pipe_velocity)
        ground_width = self._assets.sprites["ground"].get_width()
        if self._ground_x <= -ground_width:
            self._ground_x += ground_width

        # Collision — skipped during grace period.
        if now > self._grace_deadline and self._check_collision():
            self._trigger_death()

    def _spawn_pipe(self) -> None:
        margin = PIPE_GAP // 2 + 50
        gap_y = random.randint(margin, self.GROUND_Y - margin)
        self._pipes.append(
            Pipe(
                x=SCREEN_WIDTH + 50,
                gap_y=gap_y,
                top_sprite=self._assets.sprites["pipe_top"],
                bottom_sprite=self._assets.sprites["pipe_bottom"],
                velocity=self._pipe_velocity,
            )
        )

    def _check_collision(self) -> bool:
        assert self._bird is not None
        bird_rect = self._bird.get_rect()

        if int(self._bird.y) + self._bird.height >= self.GROUND_Y:
            return True
        if self._bird.y < 0:
            return True
        for pipe in self._pipes:
            if bird_rect.colliderect(pipe.get_top_rect()):
                return True
            if bird_rect.colliderect(pipe.get_bottom_rect()):
                return True
        return False

    def _update_difficulty(self) -> None:
        new_level = 1 + self._score // SCORE_PER_DIFFICULTY_STEP
        if new_level > self._difficulty:
            self._difficulty = new_level
            self._pipe_velocity = max(
                PIPE_VELOCITY_MIN,
                PIPE_VELOCITY_BASE - self._difficulty * 0.5,
            )
            self._pipe_frequency_ms = max(
                PIPE_FREQUENCY_MIN_MS,
                PIPE_FREQUENCY_MS - self._difficulty * 100,
            )

    # ── Private: rendering ────────────────────────────────────────────────────

    def _draw(self) -> None:
        surf = self._render_surface
        surf.blit(self._assets.sprites["background"], (0, 0))

        if self._state == GameState.MENU:
            self._draw_menu(surf)
        elif self._state in (GameState.PLAYING, GameState.PAUSED, GameState.GAME_OVER):
            self._draw_gameplay(surf)

        self._draw_ground(surf)

        # Screen shake — offset the render surface onto the display.
        if self._shake_frames > 0:
            ox = random.randint(-SCREEN_SHAKE_INTENSITY, SCREEN_SHAKE_INTENSITY)
            oy = random.randint(-SCREEN_SHAKE_INTENSITY, SCREEN_SHAKE_INTENSITY)
        else:
            ox, oy = 0, 0
        self._screen.blit(surf, (ox, oy))
        pygame.display.flip()

    def _draw_menu(self, surf: pygame.Surface) -> None:
        assert self._bird is not None
        import math

        # Idle bob animation for the bird.
        bob_y = int(math.sin(self._bird_bob_angle) * 8)
        self._bird.y = SCREEN_HEIGHT // 2 - 60 + bob_y
        self._bird.draw(surf)

        message = self._assets.sprites.get("message")
        if message:
            msg_rect = message.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
            surf.blit(message, msg_rect)
        else:
            self._draw_text_centered(surf, "FLAPPY BIRD", self._font_score, WHITE, SCREEN_HEIGHT // 3)
            self._draw_text_centered(surf, "Tap or SPACE to start", self._font_ui, WHITE, SCREEN_HEIGHT // 2)

        self._draw_text_centered(
            surf, f"Best: {self._high_score}", self._font_ui, GOLD, int(SCREEN_HEIGHT * 0.7)
        )

    def _draw_gameplay(self, surf: pygame.Surface) -> None:
        assert self._bird is not None
        for pipe in self._pipes:
            pipe.draw(surf)
        self._bird.draw(surf)
        for particle in self._particles:
            particle.draw(surf)
        self._draw_score(surf, self._score)

        if self._state == GameState.PAUSED:
            self._draw_paused_overlay(surf)
        elif self._state == GameState.GAME_OVER:
            self._draw_game_over_overlay(surf)

    def _draw_paused_overlay(self, surf: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surf.blit(overlay, (0, 0))
        self._draw_text_centered(surf, "PAUSED", self._font_score, WHITE, SCREEN_HEIGHT // 3)
        self._draw_text_centered(surf, "ESC / P to resume", self._font_ui, WHITE, SCREEN_HEIGHT // 2)

    def _draw_game_over_overlay(self, surf: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        self._draw_text_centered(surf, "GAME OVER", self._font_score, RED_BRIGHT, SCREEN_HEIGHT // 3)
        self._draw_text_centered(surf, f"Score: {self._score}", self._font_ui, WHITE, int(SCREEN_HEIGHT * 0.50))
        self._draw_text_centered(surf, f"Best:  {self._high_score}", self._font_ui, GOLD, int(SCREEN_HEIGHT * 0.57))
        self._draw_text_centered(surf, f"Level: {self._difficulty}", self._font_small, WHITE, int(SCREEN_HEIGHT * 0.64))
        self._draw_text_centered(surf, "SPACE / Tap to restart", self._font_ui, WHITE, int(SCREEN_HEIGHT * 0.73))

    def _draw_score(self, surf: pygame.Surface, score: int) -> None:
        digits = self._assets.digit_sprites
        if digits:
            # Render each digit as a sprite, centred at the top of the screen.
            digit_chars = str(score)
            total_w = sum(digits[int(d)].get_width() for d in digit_chars) + (len(digit_chars) - 1) * 4
            x = (SCREEN_WIDTH - total_w) // 2
            y = 20
            for ch in digit_chars:
                d_surf = digits[int(ch)]
                surf.blit(d_surf, (x, y))
                x += d_surf.get_width() + 4
        else:
            # Font fallback with drop shadow.
            text = str(score)
            shadow = self._font_score.render(text, True, BLACK)
            main = self._font_score.render(text, True, WHITE)
            rect = main.get_rect(center=(SCREEN_WIDTH // 2, 50))
            surf.blit(shadow, (rect.x + 2, rect.y + 2))
            surf.blit(main, rect)

    def _draw_ground(self, surf: pygame.Surface) -> None:
        ground = self._assets.sprites["ground"]
        gw = ground.get_width()
        x = int(self._ground_x)
        surf.blit(ground, (x, self.GROUND_Y))
        surf.blit(ground, (x + gw, self.GROUND_Y))

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_text_centered(
        surf: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple,
        y: int,
    ) -> None:
        rendered = font.render(text, True, color)
        rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, y))
        surf.blit(rendered, rect)

    @staticmethod
    def _quit() -> None:
        pygame.quit()
        sys.exit()
