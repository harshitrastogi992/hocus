from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from ..compositing import add_glow, composite
from .base import Direction, Effect, Scene

SWEEP_SECONDS = 0.9
SETTLE_SECONDS = 0.3
BAND = 0.08
BEND = 26.0            # refraction strength in pixels at 720p
SHIMMER = np.array((255, 236, 196), dtype=np.float32)   # BGR icy blue-white


@lru_cache(maxsize=4)
def _grid(height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    return xs, ys


def ghost(scene: Scene, t: float) -> np.ndarray:
    """The background seen through a body of moving glass: bent at the edges, with a rim."""
    height, width = scene.mask.shape
    size = (max(2, width // 4), max(2, height // 4))
    small = cv2.GaussianBlur(cv2.resize(scene.mask, size, interpolation=cv2.INTER_AREA),
                             (0, 0), max(1.0, width / 260))
    gx = cv2.Sobel(small, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(small, cv2.CV_32F, 0, 1, ksize=3)
    xs, ys = _grid(height, width)
    strength = BEND * height / 720.0
    ripple = np.sin(ys[::4, ::4] * 0.09 + t * 7.0) * 0.12 * small
    map_x = xs + cv2.resize(gx * strength + ripple * strength, (width, height))
    map_y = ys + cv2.resize(gy * strength, (width, height))
    bent = cv2.remap(scene.background, map_x, map_y, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)
    output = composite(bent, scene.background, np.clip(scene.mask * 1.4, 0, 1))

    rim = np.clip(small * (1.0 - small) * 4.0, 0, 1)
    flicker = 0.55 + 0.45 * np.sin(xs[::4, ::4] * 0.05 + ys[::4, ::4] * 0.03 - t * 9.0)
    rim = cv2.resize(rim * flicker * 0.45, (width, height), interpolation=cv2.INTER_LINEAR)
    add_glow(output, np.broadcast_to(SHIMMER, output.shape), rim)
    return output


class Cloak(Effect):
    """An invisibility cloak: a shimmer sweeps down and leaves only a ripple of glass."""

    id = "cloak"
    name = "Cloak"
    description = "Turn invisible under a shimmering cloak. Only a faint ripple gives you away."
    default_gesture = "open_palm"
    out_seconds = SWEEP_SECONDS + SETTLE_SECONDS
    in_seconds = SWEEP_SECONDS

    def render(self, scene: Scene, direction: Direction, t: float) -> np.ndarray:
        clock = min(t, SWEEP_SECONDS) if direction is Direction.OUT else SWEEP_SECONDS - t
        height = scene.mask.shape[0]
        rows = np.linspace(0.0, 1.0, height, dtype=np.float32)
        front = clock / SWEEP_SECONDS * (1.0 + 2 * BAND) - BAND
        covered = np.clip((front - rows) / BAND + 0.5, 0.0, 1.0)[:, None]
        output = composite(scene.frame, ghost(scene, t), scene.mask * (1.0 - covered))
        band = np.clip(1.0 - np.abs(rows - front) / BAND, 0.0, 1.0)[:, None] * scene.mask
        if band.max() > 0.01:
            add_glow(output, np.broadcast_to(SHIMMER, output.shape), np.clip(band * 0.9, 0, 1))
        return output

    def render_hidden(self, scene: Scene, t: float) -> np.ndarray:
        return ghost(scene, t)
