from __future__ import annotations

from collections import deque

import cv2
import numpy as np

from ..compositing import blend_into, composite, person_box
from .base import Direction, Effect, Scene
from .smoke import SMOKE_SECONDS, puff

SUMMON_SECONDS = 0.9
DISMISS_SECONDS = 0.8
SPREAD = 0.85          # clone offset as a share of the person's width
SCALE = 0.85
LAGS = (4, 8)          # frames each clone trails behind you
SHADOW = np.array((1.0, 0.86, 0.80), dtype=np.float32)   # BGR multiplier: cooler, darker


def _ease_out(x: float) -> float:
    x = float(np.clip(x, 0.0, 1.0))
    return 1.0 - (1.0 - x) ** 3


class Clones(Effect):
    """Two shadow clones step out either side of you and copy your moves a beat late."""

    id = "clones"
    name = "Clones"
    description = "Two shadow clones pop out beside you and copy your moves a beat late."
    default_gesture = "finger_cross"
    kind = "toggle"
    active_label = "Clones out"
    out_seconds = SUMMON_SECONDS
    in_seconds = DISMISS_SECONDS

    def __init__(self) -> None:
        self._history: deque[tuple[np.ndarray, np.ndarray]] = deque(maxlen=max(LAGS) + 1)
        self._seed = 0
        self._box: tuple[int, int, int, int] | None = None

    def begin(self, scene: Scene, direction: Direction) -> None:
        self._seed = int(np.random.default_rng().integers(1 << 30))
        if direction is Direction.OUT:
            self._history.clear()

    def _remember(self, scene: Scene) -> None:
        if self._history and self._history[-1][0].shape != scene.frame.shape:
            self._history.clear()
        self._history.append((scene.frame, (scene.mask * 255).astype(np.uint8)))
        self._box = person_box(scene.mask, threshold=0.3) or self._box

    def _draw_clones(self, scene: Scene, reach: float, opacity: float) -> np.ndarray:
        output = scene.background.copy()
        box = self._box
        if box is None or opacity <= 0.0:
            return composite(scene.frame, output, scene.mask)
        left, top, right, bottom = box
        height, width = scene.mask.shape
        offset = (right - left) * SPREAD * reach
        for side, lag in zip((-1, 1), LAGS, strict=True):
            frame, mask = self._history[max(0, len(self._history) - 1 - lag)]
            crop = np.s_[top:bottom, left:right]
            w, h = max(2, int((right - left) * SCALE)), max(2, int((bottom - top) * SCALE))
            body = cv2.resize(frame[crop], (w, h), interpolation=cv2.INTER_AREA)
            alpha = cv2.resize(mask[crop], (w, h), interpolation=cv2.INTER_AREA)
            centre = np.clip((left + right) / 2 + side * offset, w * 0.4, width - w * 0.4)
            x1 = int(centre - w / 2)
            y1 = bottom - h
            dx1, dy1 = max(0, x1), max(0, y1)
            dx2, dy2 = min(width, x1 + w), min(height, y1 + h)
            if dx1 >= dx2 or dy1 >= dy2:
                continue
            part = np.s_[dy1 - y1:dy2 - y1, dx1 - x1:dx2 - x1]
            shaded = np.clip(body[part] * SHADOW, 0, 255).astype(np.uint8)
            blend_into(output[dy1:dy2, dx1:dx2], shaded,
                       alpha[part].astype(np.float32) / 255.0 * opacity)
        return composite(scene.frame, output, scene.mask)

    def _puffs(self, output: np.ndarray, progress: float) -> None:
        if self._box is None:
            return
        left, top, right, bottom = self._box
        size = min(right - left, bottom - top) * 0.32
        y = top + (bottom - top) * 0.45
        for side in (-1, 1):
            w = (right - left) * SCALE
            x = np.clip((left + right) / 2 + side * (right - left) * SPREAD, w * 0.4,
                        output.shape[1] - w * 0.4)
            puff(output, (x, y), size, progress * SMOKE_SECONDS, self._seed + side)

    def render(self, scene: Scene, direction: Direction, t: float) -> np.ndarray:
        self._remember(scene)
        if direction is Direction.OUT:
            output = self._draw_clones(scene, _ease_out(t / 0.45), min(1.0, t / 0.2))
            self._puffs(output, t / SUMMON_SECONDS)
        else:
            output = self._draw_clones(scene, 1.0, max(0.0, 1.0 - t / 0.2))
            self._puffs(output, t / DISMISS_SECONDS)
        return output

    def render_hidden(self, scene: Scene, t: float) -> np.ndarray:
        self._remember(scene)
        return self._draw_clones(scene, 1.0, 1.0)
