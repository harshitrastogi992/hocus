from __future__ import annotations

import math

import cv2
import numpy as np

SMOKE_SECONDS = 1.1
SMOKE_COLOUR = (232, 234, 238)


def puff(output: np.ndarray, centre: tuple[float, float], size: float, t: float,
           seed: int) -> None:
    if t >= SMOKE_SECONDS:
        return
    rng = np.random.default_rng(seed)
    count = 26
    angle = rng.uniform(0, 2 * np.pi, count)
    speed = rng.uniform(0.6, 1.4, count) * size
    radius = rng.uniform(0.10, 0.22, count) * size
    spread = 1.0 - math.exp(-t * 5.0)
    xs = centre[0] + np.cos(angle) * speed * spread
    ys = centre[1] + np.sin(angle) * speed * spread * 0.6 - t * size * 0.25
    radii = radius * (1.0 + t * 1.6)
    opacity = min(1.0, t / 0.06) * max(0.0, 1.0 - max(0.0, t - 0.25) / (SMOKE_SECONDS - 0.25))

    margin = int(size * 2.2)
    cx, cy = int(centre[0]), int(centre[1])
    left, top = max(0, cx - margin), max(0, cy - margin)
    right, bottom = min(output.shape[1], cx + margin), min(output.shape[0], cy + margin)
    if left >= right or top >= bottom or opacity <= 0:
        return
    full = (right - left, bottom - top)
    density = np.zeros(((bottom - top) // 2 + 1, (right - left) // 2 + 1), dtype=np.float32)
    for x, y, r in zip(xs, ys, radii, strict=True):
        cv2.circle(density, ((int(x) - left) // 2, (int(y) - top) // 2), max(1, int(r) // 2),
                   1.0, -1, cv2.LINE_AA)
    density = cv2.GaussianBlur(density, (0, 0), max(1.0, size * 0.025))
    shade = 1.0 - 0.18 * cv2.GaussianBlur(density, (0, 0), max(1.0, size * 0.06))
    density = cv2.resize(density, full, interpolation=cv2.INTER_LINEAR)
    shade = cv2.resize(shade, full, interpolation=cv2.INTER_LINEAR)
    alpha = np.clip(density * 0.95, 0, 1) * opacity
    smoke = np.empty((bottom - top, right - left, 3), dtype=np.float32)
    smoke[:] = SMOKE_COLOUR
    smoke *= np.clip(shade, 0.7, 1.0)[:, :, None]
    region = output[top:bottom, left:right]
    region[:] = np.clip(smoke * alpha[:, :, None] + region * (1 - alpha[:, :, None]),
                        0, 255).astype(np.uint8)
