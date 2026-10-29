from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from .base import Reaction, fade

SECONDS = 3.0
COUNT = 26
SPAWN_SECONDS = 1.5
COLOURS = ((92, 70, 240), (130, 110, 255), (170, 150, 255), (90, 60, 205))   # BGR reds and pinks


@lru_cache(maxsize=64)
def heart_sprite(size: int, colour: tuple[int, int, int]) -> np.ndarray:
    """A glossy heart, BGRA, ``size`` pixels wide."""
    scale = 4
    big = size * scale
    t = np.linspace(0, 2 * np.pi, 120)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    points = np.stack(((x / 34 + 0.5) * big, ((y + 17) / 34 + 0.03) * big), axis=1)
    sprite = np.zeros((big, big, 4), np.uint8)
    dark = tuple(int(c * 0.72) for c in colour)
    cv2.fillPoly(sprite, [np.round(points).astype(np.int32)], (*dark, 255), cv2.LINE_AA)
    inner = (points - big / 2) * 0.88 + big / 2 - (0, big * 0.02)
    cv2.fillPoly(sprite, [np.round(inner).astype(np.int32)], (*colour, 255), cv2.LINE_AA)
    cv2.ellipse(sprite, (int(big * 0.32), int(big * 0.30)), (int(big * 0.09), int(big * 0.05)),
                -35, 0, 360, (255, 255, 255, 200), -1, cv2.LINE_AA)
    return cv2.resize(sprite, (size, size), interpolation=cv2.INTER_AREA)


def paste(output: np.ndarray, sprite: np.ndarray, centre: tuple[float, float],
          opacity: float) -> None:
    h, w = sprite.shape[:2]
    x1, y1 = int(centre[0] - w / 2), int(centre[1] - h / 2)
    left, top = max(0, x1), max(0, y1)
    right, bottom = min(output.shape[1], x1 + w), min(output.shape[0], y1 + h)
    if left >= right or top >= bottom or opacity <= 0:
        return
    part = sprite[top - y1:bottom - y1, left - x1:right - x1]
    alpha = part[:, :, 3:4].astype(np.float32) / 255.0 * opacity
    region = output[top:bottom, left:right]
    region[:] = (part[:, :, :3] * alpha + region * (1 - alpha)).astype(np.uint8)


class Hearts(Reaction):
    """Hearts pop out of your hands and float up."""

    id = "hearts"
    name = "Hearts"
    description = "A heart pops out of your hands and more float up around you."
    default_gesture = "heart_hands"
    seconds = SECONDS

    def __init__(self) -> None:
        self._origin = (0.0, 0.0)
        self._hearts: dict[str, np.ndarray] | None = None
        self._unit = 1.0

    def begin(self, shape, observation) -> None:
        height, width = shape
        hands = observation.hands if observation else []
        if hands:
            tips = np.concatenate([hand.points[[4, 8]] for hand in hands[:2]])
            self._origin = tuple(float(v) for v in tips.mean(axis=0))
        else:
            self._origin = (width / 2, height * 0.62)
        rng = np.random.default_rng()
        self._unit = height / 720.0
        self._hearts = {
            "start": np.sort(rng.uniform(0.1, SPAWN_SECONDS, COUNT)),
            "dx": rng.uniform(-0.28, 0.28, COUNT) * height,
            "rise": rng.uniform(0.30, 0.55, COUNT) * height,
            "sway": rng.uniform(0.015, 0.04, COUNT) * height,
            "phase": rng.uniform(0, 2 * np.pi, COUNT),
            "size": rng.uniform(26, 62, COUNT),
            "life": rng.uniform(1.2, 1.7, COUNT),
            "colour": rng.integers(0, len(COLOURS), COUNT),
        }

    def render(self, output, mask, person_visible, t):
        if self._hearts is None:
            self.begin(output.shape[:2], None)
        output = output.copy()
        ox, oy = self._origin
        h = self._hearts
        for i in range(COUNT):
            age = t - h["start"][i]
            if not 0 <= age < h["life"][i]:
                continue
            grow = min(1.0, age / 0.25)
            size = int(h["size"][i] * self._unit * (0.4 + 0.6 * grow))
            x = (ox + h["dx"][i] * min(1.0, age / 0.6)
                 + np.sin(h["phase"][i] + age * 4) * h["sway"][i])
            y = oy - h["rise"][i] * age
            opacity = min(1.0, (h["life"][i] - age) / 0.4)
            paste(output, heart_sprite(max(6, size), COLOURS[h["colour"][i]]), (x, y), opacity)
        if t < 0.9:
            pop = min(1.0, t / 0.12)
            scale = 1.0 + 0.25 * np.sin(min(1.0, t / 0.35) * np.pi)
            size = int(110 * self._unit * pop * scale)
            paste(output, heart_sprite(max(6, size), COLOURS[0]), (ox, oy - 20 * self._unit),
                  fade(t, 0.9, 0.05, 0.35))
        return output
