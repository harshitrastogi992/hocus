from __future__ import annotations

import cv2
import numpy as np

from ..compositing import add_glow, composite
from .base import Reaction, fade

SECONDS = 3.4
PIECES_PER_POPPER = 210
GRAVITY = 0.75         # frame heights per second squared
FRONT_SHARE = 0.3
PALETTE = np.array([
    (68, 181, 245), (96, 110, 250), (150, 214, 110), (235, 178, 80),
    (225, 120, 170), (240, 240, 240), (170, 130, 255), (80, 220, 250),
], dtype=np.float32)   # BGR
FLASH = np.array((200, 240, 255), dtype=np.float32)


class Confetti(Reaction):
    """Two party poppers fire from the bottom corners and confetti flutters down behind you."""

    id = "confetti"
    name = "Confetti"
    description = "Party poppers fire from both corners and confetti flutters down behind you."
    default_gesture = "thumbs_up"
    seconds = SECONDS

    def __init__(self) -> None:
        self._pieces: dict[str, np.ndarray] | None = None

    def begin(self, shape, observation) -> None:
        height, width = shape
        rng = np.random.default_rng()
        count = PIECES_PER_POPPER * 2
        side = np.repeat([-1.0, 1.0], PIECES_PER_POPPER)
        angle = np.radians(rng.uniform(4, 48, count))     # from vertical, leaning inwards
        speed = rng.uniform(1.6, 3.9, count) * height
        unit = height / 720.0
        self._pieces = {
            "origin": np.stack((np.where(side < 0, width * 0.03, width * 0.97),
                                np.full(count, height * 1.02)), axis=1),
            "velocity": np.stack((-side * np.sin(angle) * speed, -np.cos(angle) * speed), axis=1),
            "delay": rng.uniform(0.0, 0.14, count),
            "colour": PALETTE[rng.integers(0, len(PALETTE), count)],
            "size": np.stack((rng.uniform(8, 13, count), rng.uniform(14, 24, count)), 1) * unit,
            "drag": rng.uniform(2.2, 4.0, count),
            "spin": rng.uniform(-9, 9, count),
            "flip": rng.uniform(6, 16, count),
            "phase": rng.uniform(0, 2 * np.pi, count),
            "front": rng.random(count) < FRONT_SHARE,
            "height": np.array(float(height)),
        }

    def _positions(self, t: float) -> tuple[np.ndarray, np.ndarray]:
        p = self._pieces
        age = np.maximum(0.0, t - p["delay"])
        drag = p["drag"][:, None]
        decay = 1.0 - np.exp(-drag * age[:, None])
        fall = GRAVITY * float(p["height"]) / drag[:, 0]
        terminal = np.stack((np.zeros_like(fall), fall), axis=1)
        position = p["origin"] + (p["velocity"] - terminal) / drag * decay + terminal * age[:, None]
        position[:, 0] += np.sin(p["phase"] + age * 3.0) * 0.02 * float(p["height"]) * decay[:, 0]
        return position, age

    def _draw(self, layer: np.ndarray, which: np.ndarray, position: np.ndarray,
              age: np.ndarray) -> None:
        p = self._pieces
        height, width = layer.shape[:2]
        for i in np.nonzero(which & (age > 0))[0]:
            x, y = position[i]
            if not (-20 < x < width + 20 and -20 < y < height + 20):
                continue
            w, h = p["size"][i]
            theta = p["phase"][i] + p["spin"][i] * age[i]
            turn = np.cos(p["phase"][i] * 2 + p["flip"][i] * age[i])
            c, s = np.cos(theta), np.sin(theta)
            half_w, half_h = w * 0.5 * max(0.15, abs(turn)), h * 0.5
            corners = np.array([(-half_w, -half_h), (half_w, -half_h), (half_w, half_h),
                                (-half_w, half_h)]) @ np.array([[c, s], [-s, c]]) + (x, y)
            colour = p["colour"][i] * (0.55 + 0.45 * abs(turn))
            cv2.fillConvexPoly(layer, np.round(corners).astype(np.int32),
                               tuple(float(v) for v in colour), cv2.LINE_AA)

    def render(self, output, mask, person_visible, t):
        if self._pieces is None:
            self.begin(output.shape[:2], None)
        position, age = self._positions(t)
        front = self._pieces["front"]
        back = output.copy()
        self._draw(back, ~front, position, age)
        if t < 0.18:
            self._flash(back, 1.0 - t / 0.18)
        layer = self.behind(output, back, mask, person_visible)
        self._draw(layer, front, position, age)
        opacity = fade(t, SECONDS, 0.01, 0.7)
        if opacity < 1.0:
            layer = composite(layer, output, np.full(mask.shape, opacity, np.float32))
        return layer

    def _flash(self, layer: np.ndarray, strength: float) -> None:
        height, width = layer.shape[:2]
        radius = int(height * 0.16)
        for x in (int(width * 0.03), int(width * 0.97)):
            left, right = max(0, x - radius), min(width, x + radius)
            top = max(0, height - radius)
            region = layer[top:, left:right]
            ys, xs = np.mgrid[top:height, left:right].astype(np.float32)
            glow = np.clip(1.0 - np.hypot(xs - x, ys - height) / radius, 0, 1) ** 2 * strength
            add_glow(region, np.broadcast_to(FLASH, region.shape), glow)
