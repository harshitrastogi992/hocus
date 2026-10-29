from __future__ import annotations

import cv2
import numpy as np

from ..compositing import add_glow, person_box
from .base import Direction, Effect, Scene

SWEEP_START = 0.10
SWEEP_SECONDS = 1.00
EDGE = 0.05
PARTICLES = 2600
MAX_LIFE = 0.55
EMBER = np.array((60, 185, 255), dtype=np.float32)   # BGR amber
WHITE_HOT = np.array((225, 245, 255), dtype=np.float32)


def _noise(height: int, width: int, rng: np.random.Generator) -> np.ndarray:
    coarse = cv2.resize(rng.random((max(2, height // 40), max(2, width // 40))).astype(np.float32),
                        (width, height), interpolation=cv2.INTER_CUBIC)
    fine = cv2.resize(rng.random((max(2, height // 8), max(2, width // 8))).astype(np.float32),
                      (width, height), interpolation=cv2.INTER_LINEAR)
    return np.clip(coarse * 0.7 + fine * 0.3, 0.0, 1.0)


class Stardust(Effect):
    """The body burns away top to bottom into drifting amber sparks."""

    id = "stardust"
    name = "Stardust"
    description = "Burn away into drifting sparks, top to bottom. Sparks gather back to return."
    default_gesture = "v_sign"
    out_seconds = SWEEP_START + SWEEP_SECONDS + MAX_LIFE
    in_seconds = out_seconds

    def __init__(self) -> None:
        self._release: np.ndarray | None = None
        self._particles: dict[str, np.ndarray] | None = None

    def begin(self, scene: Scene, direction: Direction) -> None:
        height, width = scene.mask.shape
        rng = np.random.default_rng()
        box = person_box(scene.mask) or (0, 0, width, height)
        top, bottom = box[1], max(box[1] + 1, box[3])
        rows = np.clip((np.arange(height, dtype=np.float32) - top) / (bottom - top), 0.0, 1.0)
        field = rows[:, None] * 0.65 + _noise(height, width, rng) * 0.35
        self._release = SWEEP_START + field * SWEEP_SECONDS

        ys, xs = np.nonzero(scene.mask > 0.5)
        if len(xs) == 0:
            self._particles = None
            return
        pick = rng.choice(len(xs), size=min(PARTICLES, len(xs)), replace=False)
        ys, xs = ys[pick], xs[pick]
        unit = height / 720.0
        drift = 1.0 if rng.random() < 0.5 else -1.0
        self._particles = {
            "origin": np.stack((xs, ys), axis=1).astype(np.float32),
            "colour": scene.frame[ys, xs].astype(np.float32),
            "release": self._release[ys, xs],
            "velocity": np.stack((drift * rng.uniform(40, 260, len(xs)),
                                  -rng.uniform(80, 320, len(xs))), axis=1) * unit,
            "life": rng.uniform(0.30, MAX_LIFE, len(xs)),
            "phase": rng.uniform(0, 2 * np.pi, len(xs)),
            "unit": np.array(unit),
        }

    def render(self, scene: Scene, direction: Direction, t: float) -> np.ndarray:
        if self._release is None or self._release.shape != scene.mask.shape:
            self.begin(scene, direction)
        clock = t if direction is Direction.OUT else self.out_seconds - t
        burnt = np.clip((clock - (self._release - EDGE)) / (2 * EDGE), 0.0, 1.0)
        output = self.person(scene, 1.0 - burnt)
        box = person_box(scene.mask, threshold=0.2, pad=12)
        if box is not None:
            left, top, right, bottom = box
            area = np.s_[top:bottom, left:right]
            edge = scene.mask[area] * np.clip(
                1.0 - np.abs(clock - self._release[area]) / EDGE, 0.0, 1.0)
            if edge.max() > 0.01:
                glow = np.clip(cv2.GaussianBlur(edge, (0, 0), 2.5) * 1.6, 0, 1)
                add_glow(output[area], np.broadcast_to(EMBER, output[area].shape), glow)
        self._draw_particles(output, clock)
        return output

    def _draw_particles(self, output: np.ndarray, clock: float) -> None:
        p = self._particles
        if p is None:
            return
        age = clock - p["release"]
        live = (age > 0) & (age < p["life"])
        if not live.any():
            return
        age = age[live]
        unit = float(p["unit"])
        position = p["origin"][live] + p["velocity"][live] * age[:, None]
        position[:, 0] += np.sin(p["phase"][live] + age * 9.0) * 14.0 * unit
        position[:, 1] -= 120.0 * unit * age * age
        fade = (1.0 - age / p["life"][live])[:, None]
        heat = np.clip(1.0 - age * 4.0, 0.0, 1.0)[:, None]
        colour = (p["colour"][live] * 0.35 + EMBER * 0.65) * (1 - heat) + WHITE_HOT * heat

        height, width = output.shape[:2]
        xs, ys = np.round(position[:, 0]).astype(int), np.round(position[:, 1]).astype(int)
        inside = (xs >= 0) & (xs < width - 1) & (ys >= 0) & (ys < height - 1)
        if not inside.any():
            return
        xs, ys, fade, colour = xs[inside], ys[inside], fade[inside], colour[inside]
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            under = output[ys + dy, xs + dx].astype(np.float32)
            output[ys + dy, xs + dx] = np.clip(colour * fade + under * (1 - fade), 0, 255)

        left, right = max(0, xs.min() - 16), min(width, xs.max() + 17)
        top, bottom = max(0, ys.min() - 16), min(height, ys.max() + 17)
        small = np.zeros(((bottom - top) // 4 + 1, (right - left) // 4 + 1), np.float32)
        np.maximum.at(small, ((ys - top) // 4, (xs - left) // 4), fade[:, 0])
        halo = cv2.resize(cv2.GaussianBlur(small, (0, 0), 1.0), (right - left, bottom - top),
                          interpolation=cv2.INTER_LINEAR)
        region = output[top:bottom, left:right]
        add_glow(region, np.broadcast_to(EMBER, region.shape), np.clip(halo * 0.9, 0, 1))
