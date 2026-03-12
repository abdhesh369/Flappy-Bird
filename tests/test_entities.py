"""
Unit tests for Bird and Pipe entities.

The SDL display and audio drivers are swapped for dummy drivers so these
tests run in headless CI environments without a physical screen or speakers.
"""
import os
import sys

# Force headless SDL before pygame initialises.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pygame

pygame.init()

from src.entities import Bird, Pipe
from src.constants import (
    GRAVITY,
    FLAP_STRENGTH,
    MAX_FALL_VELOCITY,
    MAX_RISE_VELOCITY,
    FLAP_COOLDOWN_FRAMES,
    HITBOX_MARGIN,
    PIPE_GAP,
)

# ── Shared fixtures ───────────────────────────────────────────────────────────

BIRD_SPRITE = pygame.Surface((34, 34), pygame.SRCALPHA)
PIPE_SPRITE = pygame.Surface((52, 400), pygame.SRCALPHA)


def make_bird(x: int = 80, y: int = 300) -> Bird:
    return Bird(x, y, BIRD_SPRITE)


def make_pipe(x: int = 500, gap_y: int = 350, velocity: float = -3.0) -> Pipe:
    return Pipe(x, gap_y, PIPE_SPRITE, PIPE_SPRITE, velocity)


# ── Bird tests ────────────────────────────────────────────────────────────────

class TestBirdInitialState:
    def test_velocity_starts_at_zero(self):
        assert make_bird().velocity == 0.0

    def test_angle_starts_at_zero(self):
        assert make_bird().angle == 0.0

    def test_position_stored_correctly(self):
        bird = make_bird(x=10, y=20)
        assert bird.x == 10
        assert bird.y == 20.0


class TestBirdFlap:
    def test_flap_sets_velocity_to_flap_strength(self):
        bird = make_bird()
        bird.flap()
        assert bird.velocity == FLAP_STRENGTH

    def test_first_flap_is_accepted(self):
        assert make_bird().flap() is True

    def test_second_flap_in_cooldown_is_rejected(self):
        bird = make_bird()
        bird.flap()
        assert bird.flap() is False

    def test_flap_accepted_after_cooldown_expires(self):
        bird = make_bird()
        bird.flap()
        for _ in range(FLAP_COOLDOWN_FRAMES):
            bird.update()
        assert bird.flap() is True


class TestBirdPhysics:
    def test_gravity_increases_velocity_each_frame(self):
        bird = make_bird()
        bird.update()
        assert bird.velocity == pytest.approx(GRAVITY)

    def test_gravity_accumulates_over_multiple_frames(self):
        bird = make_bird()
        for _ in range(5):
            bird.update()
        assert bird.velocity == pytest.approx(GRAVITY * 5)

    def test_velocity_clamped_at_max_fall(self):
        bird = make_bird()
        bird.velocity = 9999.0
        bird.update()
        assert bird.velocity <= MAX_FALL_VELOCITY

    def test_velocity_clamped_at_max_rise(self):
        bird = make_bird()
        bird.velocity = -9999.0
        bird.update()
        assert bird.velocity >= MAX_RISE_VELOCITY

    def test_y_position_increases_when_velocity_positive(self):
        bird = make_bird(y=300)
        bird.velocity = 5.0
        initial_y = bird.y
        bird.update()
        assert bird.y > initial_y

    def test_y_position_decreases_when_velocity_negative(self):
        bird = make_bird(y=300)
        bird.velocity = -5.0
        initial_y = bird.y
        bird.update()
        assert bird.y < initial_y


class TestBirdHitbox:
    def test_hitbox_is_smaller_than_sprite_by_margin(self):
        bird = make_bird()
        rect = bird.get_rect()
        assert rect.width == bird.width - HITBOX_MARGIN * 2
        assert rect.height == bird.height - HITBOX_MARGIN * 2

    def test_hitbox_x_is_offset_by_margin(self):
        bird = make_bird(x=100)
        rect = bird.get_rect()
        assert rect.x == bird.x + HITBOX_MARGIN

    def test_hitbox_y_is_offset_by_margin(self):
        bird = make_bird(y=200)
        rect = bird.get_rect()
        assert rect.y == int(bird.y) + HITBOX_MARGIN


# ── Pipe tests ────────────────────────────────────────────────────────────────

class TestPipeMovement:
    def test_pipe_moves_left_by_velocity_each_frame(self):
        pipe = make_pipe(x=500, velocity=-3.0)
        pipe.update()
        assert pipe.x == pytest.approx(497.0)

    def test_pipe_is_not_off_screen_when_visible(self):
        assert make_pipe(x=300).is_off_screen() is False

    def test_pipe_is_off_screen_past_left_edge(self):
        pipe = make_pipe(x=-(52 + 1))  # x + width < 0
        assert pipe.is_off_screen() is True

    def test_pipe_at_zero_is_not_off_screen(self):
        assert make_pipe(x=0).is_off_screen() is False


class TestPipeCollisionGeometry:
    def test_top_rect_bottom_aligns_with_gap_top_edge(self):
        pipe = make_pipe(gap_y=350)
        top_rect = pipe.get_top_rect()
        expected_bottom = 350 - PIPE_GAP // 2
        assert top_rect.bottom == expected_bottom

    def test_bottom_rect_top_aligns_with_gap_bottom_edge(self):
        pipe = make_pipe(gap_y=350)
        bottom_rect = pipe.get_bottom_rect()
        expected_top = 350 + PIPE_GAP // 2
        assert bottom_rect.top == expected_top

    def test_gap_between_rects_equals_pipe_gap(self):
        pipe = make_pipe(gap_y=350)
        gap = pipe.get_bottom_rect().top - pipe.get_top_rect().bottom
        assert gap == PIPE_GAP

    def test_rects_do_not_overlap(self):
        pipe = make_pipe(gap_y=350)
        assert not pipe.get_top_rect().colliderect(pipe.get_bottom_rect())


class TestPipePassed:
    def test_passed_starts_false(self):
        assert make_pipe().passed is False

    def test_passed_can_be_set_externally(self):
        pipe = make_pipe()
        pipe.passed = True
        assert pipe.passed is True
