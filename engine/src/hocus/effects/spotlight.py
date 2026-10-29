from __future__ import annotations

import cv2
import numpy as np

from ..compositing import person_box
from .base import Direction, Effect, Scene

FADE_SECONDS = 0.5
DIM = 0.22
WARM = np.array((0.86, 0.97, 1.10), dtype=np.float32)   # BGR multiplier inside the light
FOLLOW = 0.25


class Spotlight(Effect):
    """The room dims and a warm stage light follows you."""

    id = "spotlight"
    name = "Spotlight"
    description = "Dim the room and step into a warm stage light that follows you around."
    default_gesture = "index_up"
    kind = "toggle"
    active_label = "Spotlight on"
    out_seconds = FADE_SECONDS
    in_seconds = FADE_SECONDS

    def __init__(self) -> None:
        self._centre: np.ndarray | None = None

    def _light(self, scene: Scene) -> np.ndarray:
        height, width = scene.mask.shape
        box = person_box(scene.mask, threshold=0.3)
        if box is not None:
            left, top, right, bottom = box
            target = np.array(((left + right) / 2, top + (bottom - top) * 0.35,
                               max(right - left, height * 0.35)), dtype=np.float32)
        else:
            target = np.array((width / 2, height * 0.45, height * 0.5), dtype=np.float32)
        if self._centre is None:
            self._centre = target
        self._centre = self._centre + (target - self._centre) * FOLLOW
        x, y, span = self._centre

        scale = 8
        small = np.zeros((height // scale + 1, width // scale + 1), np.float32)
        cv2.ellipse(small, (int(x / scale), int(y / scale)),
                    (int(span * 0.55 / scale), int(span * 0.8 / scale)), 0, 0, 360, 1.0, -1)
        top_width = max(2, int(span * 0.18 / scale))
        beam = np.array([(int(x / scale) - top_width, 0), (int(x / scale) + top_width, 0),
                         (int((x + span * 0.6) / scale), int(y / scale)),
                         (int((x - span * 0.6) / scale), int(y / scale))], np.int32)
        cone = np.zeros_like(small)
        cv2.fillConvexPoly(cone, beam, 0.22)
        small = np.maximum(small, cone)
        small = cv2.GaussianBlur(small, (0, 0), max(1.0, span / scale * 0.25))
        return cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)

    def _lit(self, scene: Scene, amount: float) -> np.ndarray:
        base = self.person(scene)
        if amount <= 0.0:
            return base
        light = self._light(scene)
        brightness = 1.0 + (DIM + (1.0 - DIM) * light - 1.0) * amount
        gain = cv2.merge([brightness * (1.0 + (w - 1.0) * light * amount) for w in WARM])
        return cv2.multiply(base, gain, dtype=cv2.CV_8U)

    def begin(self, scene: Scene, direction: Direction) -> None:
        if direction is Direction.OUT:
            self._centre = None

    def render(self, scene: Scene, direction: Direction, t: float) -> np.ndarray:
        progress = min(1.0, t / FADE_SECONDS)
        return self._lit(scene, progress if direction is Direction.OUT else 1.0 - progress)

    def render_hidden(self, scene: Scene, t: float) -> np.ndarray:
        return self._lit(scene, 1.0)
