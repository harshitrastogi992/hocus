"""Built-in backgrounds, generated in code so the repo ships no third-party images."""

from __future__ import annotations

import base64
from collections.abc import Callable
from functools import lru_cache

import cv2
import numpy as np

from .compositing import cover_fit


def _vignette(height: int, width: int, strength: float) -> np.ndarray:
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    distance = np.hypot((xs / width - 0.5) * 1.6, (ys / height - 0.45) * 1.9)
    return np.clip(1.0 - distance * strength, 0.0, 1.0)


def _studio(height: int, width: int) -> np.ndarray:
    light = _vignette(height, width, 0.55)[:, :, None]
    wall = np.array((96, 92, 88), np.float32) + np.array((88, 86, 84), np.float32) * light
    image = wall.copy()
    floor = int(height * 0.74)
    image[floor:] *= 0.78
    image[floor:floor + max(2, height // 200)] *= 0.85
    return np.clip(image, 0, 255).astype(np.uint8)


def _night(height: int, width: int) -> np.ndarray:
    rng = np.random.default_rng(7)
    sky = np.zeros((height, width, 3), np.float32)
    rows = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    sky[:] = (np.array((58, 30, 18), np.float32) * (1 - rows)[:, :, None]
              + np.array((92, 56, 34), np.float32) * rows[:, :, None])
    bokeh = np.zeros((height, width), np.float32)
    for _ in range(38):
        x, y = int(rng.uniform(0, width)), int(rng.uniform(height * 0.15, height * 0.9))
        cv2.circle(bokeh, (x, y), int(rng.uniform(0.01, 0.04) * width), rng.uniform(0.08, 0.3), -1,
                   cv2.LINE_AA)
    bokeh = cv2.GaussianBlur(bokeh, (0, 0), width / 260)[:, :, None]
    sky += bokeh * np.array((90, 160, 240), np.float32)
    return np.clip(sky, 0, 255).astype(np.uint8)


def _paper(height: int, width: int) -> np.ndarray:
    rng = np.random.default_rng(11)
    base = np.empty((height, width, 3), np.float32)
    base[:] = (222, 234, 240)
    grain = cv2.GaussianBlur(rng.normal(0, 1, (height, width)).astype(np.float32), (0, 0), 1.2)
    base += grain[:, :, None] * 5.0
    base *= (0.86 + 0.14 * _vignette(height, width, 0.6))[:, :, None]
    return np.clip(base, 0, 255).astype(np.uint8)


PRESETS: dict[str, tuple[str, Callable[[int, int], np.ndarray]]] = {
    "studio": ("Studio", _studio),
    "night": ("Night city", _night),
    "paper": ("Paper", _paper),
}


@lru_cache(maxsize=8)
def preset(name: str, width: int, height: int) -> np.ndarray:
    return PRESETS[name][1](height, width)


@lru_cache(maxsize=4)
def image_file(path: str, width: int, height: int) -> np.ndarray | None:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    return None if image is None else cover_fit(image, width, height)


@lru_cache(maxsize=8)
def preset_thumbnail(name: str) -> str:
    ok, encoded = cv2.imencode(".jpg", preset(name, 320, 180), (cv2.IMWRITE_JPEG_QUALITY, 82))
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode() if ok else ""
