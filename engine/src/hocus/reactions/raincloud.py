from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from ..compositing import composite, person_box
from .base import Reaction, fade
from .hearts import paste

SECONDS = 4.0
DROPS = 70
RAIN_FROM = 0.35
BOLT_AT = 1.7
GLOOM = 0.45
FOLLOW = 0.3
RAIN = (235, 205, 170)       # BGR pale blue
BOLT = (170, 245, 255)


@lru_cache(maxsize=16)
def cloud_sprite(width: int) -> np.ndarray:
    """A grumpy grey storm cloud, BGRA."""
    height = int(width * 0.6)
    sprite = np.zeros((height, width, 4), np.uint8)
    puffs = ((0.30, 0.55, 0.22), (0.50, 0.40, 0.28), (0.72, 0.55, 0.21), (0.18, 0.70, 0.15),
             (0.84, 0.70, 0.14), (0.50, 0.68, 0.24))
    for colour, grow, drop in (((70, 70, 78), 1.06, 0.0), ((128, 126, 132), 1.0, 0.0),
                               ((150, 148, 154), 0.82, -0.05)):
        for x, y, r in puffs:
            cv2.circle(sprite, (int(x * width), int((y + drop) * height)), int(r * width * grow),
                       (*colour, 255), -1, cv2.LINE_AA)
    sprite[int(height * 0.86):] = 0
    cv2.rectangle(sprite, (int(width * 0.1), int(height * 0.70)),
                  (int(width * 0.9), int(height * 0.86)), (110, 108, 116, 255), -1, cv2.LINE_AA)
    return sprite


class RainCloud(Reaction):
    """A small storm cloud parks over your head and rains on you, with one thunderclap."""

    id = "raincloud"
    name = "Rain cloud"
    description = "A little storm cloud follows your head and rains on you. One thunderclap."
    default_gesture = "thumbs_down"
    seconds = SECONDS

    def __init__(self) -> None:
        self._anchor: np.ndarray | None = None
        self._drops: dict[str, np.ndarray] | None = None

    def begin(self, shape, observation) -> None:
        rng = np.random.default_rng()
        self._anchor = None
        self._drops = {"x": rng.uniform(-0.38, 0.38, DROPS), "phase": rng.random(DROPS),
                       "speed": rng.uniform(1.3, 1.8, DROPS)}

    def _head(self, mask: np.ndarray) -> np.ndarray:
        height, width = mask.shape
        box = person_box(mask, threshold=0.4)
        if box is None:
            target = np.array((width / 2, height * 0.3), np.float32)
        else:
            left, top, right, bottom = box
            band = mask[top:top + max(2, int(height * 0.12)), left:right]
            weights = band.sum(axis=0)
            x = left + float((weights * np.arange(len(weights))).sum() / max(1e-6, weights.sum()))
            target = np.array((x, top), np.float32)
        if self._anchor is not None:
            target = self._anchor + (target - self._anchor) * FOLLOW
        self._anchor = target
        return self._anchor

    def render(self, output, mask, person_visible, t):
        if self._drops is None:
            self.begin(output.shape[:2], None)
        height, width = mask.shape
        strength = fade(t, SECONDS, 0.4, 0.6)
        result = self._gloom(output, strength)

        head_x, head_top = self._head(mask)
        cloud_w = int(height * 0.34)
        cloud_h = int(cloud_w * 0.6)
        enter = 1.0 - (1.0 - min(1.0, t / 0.4)) ** 3
        leave = max(0.0, t - (SECONDS - 0.5)) / 0.5
        rest_y = max(cloud_h * 0.62, head_top - cloud_h * 0.85)
        cloud_y = rest_y - (1.0 - enter + leave) * height * 0.4
        bottom = cloud_y + cloud_h * 0.3

        if t > RAIN_FROM and leave < 1.0:
            rain = result.copy()
            fall = max(40.0, head_top + height * 0.35 - bottom)
            d = self._drops
            length = height * 0.035
            ys = bottom + ((d["phase"] + (t - RAIN_FROM) * d["speed"] * height / fall) % 1.0) * fall
            xs = head_x + d["x"] * cloud_w
            for x, y in zip(xs, ys, strict=True):
                cv2.line(rain, (int(x), int(y)), (int(x - length * 0.15), int(y + length)), RAIN,
                         max(1, height // 360), cv2.LINE_AA)
            result = composite(rain, result, np.full(mask.shape, 0.75 * (1 - leave), np.float32))

        flash = np.exp(-((t - BOLT_AT) / 0.05) ** 2)
        if flash > 0.05:
            self._bolt(result, (head_x, bottom), height, flash)
        paste(result, cloud_sprite(cloud_w), (head_x, cloud_y), 1.0 - leave)
        return result

    @staticmethod
    def _gloom(output: np.ndarray, strength: float) -> np.ndarray:
        if strength <= 0.0:
            return output.copy()
        grey = cv2.cvtColor(cv2.cvtColor(output, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        cool = cv2.convertScaleAbs(grey, alpha=0.8)
        cool[:, :, 0] = cv2.add(cool[:, :, 0], 18)
        return cv2.addWeighted(output, 1.0 - GLOOM * strength, cool, GLOOM * strength, 0)

    @staticmethod
    def _bolt(output: np.ndarray, start: tuple[float, float], height: int, strength: float) -> None:
        x, y = start
        rng = np.random.default_rng(7)
        points = [(x, y)]
        for _ in range(5):
            x += rng.uniform(-0.03, 0.03) * height
            y += height * 0.045
            points.append((x, y))
        line = np.round(points).astype(np.int32)
        overlay = output.copy()
        cv2.polylines(overlay, [line], False, BOLT, max(2, height // 160), cv2.LINE_AA)
        cv2.addWeighted(overlay, strength, output, 1.0 - strength, 0, dst=output)
        cv2.convertScaleAbs(output, dst=output, alpha=1.0 + 0.2 * strength)
