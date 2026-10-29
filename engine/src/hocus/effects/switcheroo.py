from __future__ import annotations

import math
from functools import lru_cache

import cv2
import numpy as np

from ..compositing import person_box
from .base import Direction, Effect, Scene
from .smoke import SMOKE_SECONDS, puff

FADE_SECONDS = 0.12
DROP_DELAY = 0.15
GRAVITY = 3.0          # frame heights per second squared
RESTITUTION = 0.35


@lru_cache(maxsize=1)
def duck_sprite() -> np.ndarray:
    """A rubber duck drawn in code, BGRA, 512 x 512."""
    size = 512
    sprite = np.zeros((size, size, 4), dtype=np.uint8)
    ink = (38, 38, 46, 255)
    yellow, shade = (40, 214, 255, 255), (20, 176, 236, 255)
    beak = (30, 128, 255, 255)

    def shape(draw) -> None:
        draw(ink, 14)
        draw(None, -1)

    def body(colour, thickness):
        cv2.ellipse(sprite, (250, 350), (190, 120), 0, 0, 360,
                    colour or yellow, thickness, cv2.LINE_AA)
        cv2.ellipse(sprite, (420, 290), (60, 40), -35, 0, 360,
                    colour or yellow, thickness, cv2.LINE_AA)

    def head(colour, thickness):
        cv2.circle(sprite, (170, 190), 105, colour or yellow, thickness, cv2.LINE_AA)

    def bill(colour, thickness):
        cv2.ellipse(sprite, (60, 210), (62, 28), 8, 0, 360, colour or beak, thickness, cv2.LINE_AA)

    for part in (body, bill, head):
        shape(part)
    cv2.ellipse(sprite, (290, 350), (105, 55), 15, 200, 340, shade, 16, cv2.LINE_AA)
    cv2.circle(sprite, (150, 170), 18, ink, -1, cv2.LINE_AA)
    cv2.circle(sprite, (144, 163), 6, (255, 255, 255, 255), -1, cv2.LINE_AA)
    cv2.ellipse(sprite, (200, 130), (40, 18), -20, 200, 320, (150, 240, 255, 255), 8, cv2.LINE_AA)
    return sprite


@lru_cache(maxsize=32)
def _sized_duck(width: int, height: int) -> np.ndarray:
    return cv2.resize(duck_sprite(), (width, height), interpolation=cv2.INTER_AREA)


def _paste(output: np.ndarray, sprite: np.ndarray | None, centre: tuple[float, float],
           height: int, opacity: float = 1.0, squash: float = 0.0) -> None:
    if opacity <= 0.0 or height < 4:
        return
    h = max(4, int(height * (1.0 - squash)))
    w = max(4, int(height * (1.0 + squash * 0.6)))
    sized = _sized_duck(w, h) if sprite is None else cv2.resize(sprite, (w, h))
    x1, y1 = int(centre[0] - w / 2), int(centre[1] + height / 2 - h)
    left, top = max(0, x1), max(0, y1)
    right, bottom = min(output.shape[1], x1 + w), min(output.shape[0], y1 + h)
    if left >= right or top >= bottom:
        return
    part = sized[top - y1:bottom - y1, left - x1:right - x1]
    alpha = part[:, :, 3:4].astype(np.float32) / 255.0 * opacity
    region = output[top:bottom, left:right]
    region[:] = np.clip(part[:, :, :3] * alpha + region * (1 - alpha), 0, 255).astype(np.uint8)


def _drop(start_y: float, floor_y: float, frame_height: int, t: float) -> tuple[float, float]:
    """Vertical position and landing squash for a dropped object that bounces once."""
    if t <= 0 or floor_y <= start_y:
        return start_y, 0.0
    g = GRAVITY * frame_height
    fall_time = math.sqrt(2 * (floor_y - start_y) / g)
    if t < fall_time:
        return start_y + 0.5 * g * t * t, 0.0
    after = t - fall_time
    bounce_speed = g * fall_time * RESTITUTION
    bounce_time = 2 * bounce_speed / g
    if after < bounce_time:
        squash = 0.22 * math.exp(-after * 30)
        return floor_y - (bounce_speed * after - 0.5 * g * after * after), squash
    return floor_y, 0.0


class Switcheroo(Effect):
    """A puff of smoke swaps you for a rubber duck that drops to the floor."""

    id = "switcheroo"
    name = "Switcheroo"
    description = "Vanish in a puff of smoke and leave a rubber duck in your seat."
    default_gesture = "palms_together"
    out_seconds = SMOKE_SECONDS
    in_seconds = 0.9

    def __init__(self) -> None:
        self._anchor: tuple[float, float, int] | None = None
        self._seed = 0

    def begin(self, scene: Scene, direction: Direction) -> None:
        self._seed = int(np.random.default_rng().integers(1 << 30))
        if direction is Direction.OUT or self._anchor is None:
            height, width = scene.mask.shape
            box = person_box(scene.mask) or (width // 3, height // 4, 2 * width // 3, height)
            size = int(np.clip((box[3] - box[1]) * 0.42, height * 0.20, height * 0.50))
            self._anchor = ((box[0] + box[2]) / 2, box[1] + (box[3] - box[1]) * 0.5, size)

    def _floor(self, height: int) -> float:
        return height - self._anchor[2] * 0.55

    def render(self, scene: Scene, direction: Direction, t: float) -> np.ndarray:
        if self._anchor is None:
            self.begin(scene, direction)
        x, y, size = self._anchor
        height = scene.frame.shape[0]
        if direction is Direction.OUT:
            output = self.person(scene, max(0.0, 1.0 - t / FADE_SECONDS))
            drop_y, squash = _drop(y, self._floor(height), height, t - DROP_DELAY)
            pop = 1.0 + 0.25 * max(0.0, 1.0 - t / 0.2)
            _paste(output, None, (x, drop_y), int(size * pop),
                   min(1.0, t / 0.08), squash)
            puff(output, (x, y), size, t, self._seed)
        else:
            output = self.person(scene, float(np.clip((t - 0.1) / 0.25, 0.0, 1.0)))
            floor = self._floor(height)
            _paste(output, None, (x, floor), size, max(0.0, 1.0 - t / 0.1))
            puff(output, (x, floor - size * 0.2), size, t, self._seed)
        return output

    def render_hidden(self, scene: Scene, t: float) -> np.ndarray:
        output = scene.background.copy()
        if self._anchor is not None:
            x, _, size = self._anchor
            _paste(output, None, (x, self._floor(output.shape[0])), size)
        return output
