from __future__ import annotations

import math

import cv2
import numpy as np

from ..compositing import blend_into, person_box
from .base import Direction, Effect, Scene

LINES_FULL_AT = 0.30
SQUASH_START = 0.45
VANISH_AT = 0.70
LINGER_SECONDS = 0.45
TOTAL_SECONDS = VANISH_AT + LINGER_SECONDS
INK = (38, 26, 20)
LINE = (255, 250, 238)


def _speed_lines(height: int, width: int, t: float) -> tuple[np.ndarray, np.ndarray]:
    """Vertical comic strokes scrolling upwards: white cores with dark ink edges."""
    rng = np.random.default_rng(4242)
    layer = np.zeros((height, width, 3), dtype=np.uint8)
    alpha = np.zeros((height, width), dtype=np.float32)
    unit = max(1, round(width / 180))
    for _ in range(max(14, width // 8)):
        x = int(rng.uniform(0, width))
        length = rng.uniform(0.25, 0.85) * height
        speed = rng.uniform(1.4, 3.0) * height
        offset = rng.uniform(0, height + length)
        core = int(rng.integers(1, 4)) * unit
        ink_only = rng.random() < 0.3
        head = (offset - t * speed) % (height + length) - length
        top, bottom = int(head), int(head + length)
        if ink_only:
            cv2.line(layer, (x, top), (x, bottom), INK, core, cv2.LINE_AA)
        else:
            cv2.line(layer, (x, top), (x, bottom), INK, core + 2 * unit, cv2.LINE_AA)
            cv2.line(layer, (x, top), (x, bottom), LINE, core, cv2.LINE_AA)
        cv2.line(alpha, (x, top), (x, bottom), 1.0, core + (0 if ink_only else 2 * unit),
                 cv2.LINE_AA)
    return layer, alpha


def render_blink(frame: np.ndarray, background: np.ndarray, mask: np.ndarray,
                 t: float) -> np.ndarray:
    """Speed lines build over the body, it squeezes into a beam and flashes out."""
    t = float(np.clip(t, 0.0, TOTAL_SECONDS))
    output = background.copy()
    box = person_box(mask, threshold=0.25, pad=max(8, mask.shape[1] // 60))
    if box is None:
        if t < VANISH_AT:
            blend_into(output, frame, mask)
        return output
    left, top, right, bottom = box
    area = np.s_[top:bottom, left:right]
    region_mask = mask[area]
    height, width = region_mask.shape

    if t < VANISH_AT:
        squash = 0.0
        if t > SQUASH_START:
            progress = (t - SQUASH_START) / (VANISH_AT - SQUASH_START)
            squash = progress * progress * (3.0 - 2.0 * progress)
        scale_x = max(0.02, 1.0 - squash)
        scale_y = 1.0 + squash * 0.12
        cx, cy = width * 0.5, height * 0.5
        matrix = np.float32([[scale_x, 0, cx * (1 - scale_x)], [0, scale_y, cy * (1 - scale_y)]])
        person = cv2.warpAffine(frame[area], matrix, (width, height), flags=cv2.INTER_LINEAR)
        person_alpha = cv2.warpAffine(region_mask, matrix, (width, height),
                                      flags=cv2.INTER_LINEAR)
        blend_into(output[area], person, person_alpha)

    intensity = min(1.0, t / LINES_FULL_AT) * (1.0 - max(0.0, t - VANISH_AT) / LINGER_SECONDS)
    if intensity > 0.01:
        lines, line_alpha = _speed_lines(height, width, t)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        reach = cv2.GaussianBlur(cv2.dilate(region_mask, kernel), (0, 0), 3.0)
        blend_into(output[area], lines, line_alpha * reach * intensity)

    flash = math.exp(-((t - VANISH_AT) / 0.07) ** 2)
    if flash > 0.02:
        beam = np.zeros((height, width), dtype=np.float32)
        cv2.line(beam, (width // 2, 0), (width // 2, height - 1), 1.0, max(2, width // 40),
                 cv2.LINE_AA)
        beam = np.clip(cv2.GaussianBlur(beam, (0, 0), max(2.0, width / 50)) * 2.5, 0, 1)
        white = np.full((height, width, 3), (255, 248, 230), dtype=np.uint8)
        blend_into(output[area], white, beam * flash)
    return output


class Blink(Effect):
    """Comic-book teleport: speed lines, a squeeze into a beam of light, gone."""

    id = "blink"
    name = "Blink"
    description = "Teleport out in a flash of comic speed lines. The same move beams you back."
    default_gesture = "forehead_tap"
    out_seconds = TOTAL_SECONDS
    in_seconds = TOTAL_SECONDS

    def render(self, scene: Scene, direction: Direction, t: float) -> np.ndarray:
        clock = t if direction is Direction.OUT else TOTAL_SECONDS - t
        return render_blink(scene.frame, scene.background, scene.mask, clock)
