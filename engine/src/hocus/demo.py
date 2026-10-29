"""A drawn placeholder person that stands in for the camera, for screenshots and demos.

The figure is drawn on a pure green key, so the matte comes from the colour alone and
stays exact through mirroring and resizing.
"""

from __future__ import annotations

import math
import time

import cv2
import numpy as np

from .vision.observation import Observation

KEY = np.array((0, 255, 0), dtype=np.float32)
SKIN = (128, 160, 206)
HAIR = (44, 46, 58)
SHIRT = (118, 88, 44)
COLLAR = (150, 118, 70)


def draw_person(width: int, height: int, t: float) -> np.ndarray:
    """A faceless, softly lit head-and-shoulders figure, gently swaying, on the green key."""
    frame = np.empty((height, width, 3), np.uint8)
    frame[:] = KEY.astype(np.uint8)
    figure = np.zeros((height, width), np.uint8)
    cx = width * 0.5 + math.sin(t * 0.9) * width * 0.012
    bob = math.sin(t * 1.7) * height * 0.005
    tilt = math.sin(t * 0.6) * 3.0
    w, h = width, height

    def ellipse(centre, axes, colour, angle=0.0, start=0, end=360):
        centre = (int(centre[0]), int(centre[1]))
        axes = (int(axes[0]), int(axes[1]))
        cv2.ellipse(frame, centre, axes, angle, start, end, colour, -1, cv2.LINE_AA)
        cv2.ellipse(figure, centre, axes, angle, start, end, 255, -1, cv2.LINE_AA)

    def polygon(points, colour):
        points = np.round(np.array(points)).astype(np.int32)
        cv2.fillPoly(frame, [points], colour, cv2.LINE_AA)
        cv2.fillPoly(figure, [points], 255, cv2.LINE_AA)

    head = (cx, h * 0.37 + bob)
    polygon([(cx - w * 0.030, h * 0.48), (cx + w * 0.030, h * 0.48),
             (cx + w * 0.034, h * 0.68), (cx - w * 0.034, h * 0.68)], SKIN)
    ellipse((cx, h * 0.80), (w * 0.215, h * 0.17), SHIRT)
    polygon([(cx - w * 0.215, h * 0.80), (cx + w * 0.215, h * 0.80),
             (cx + w * 0.225, h), (cx - w * 0.225, h)], SHIRT)
    polygon([(cx - w * 0.048, h * 0.635), (cx + w * 0.048, h * 0.635), (cx, h * 0.745)], COLLAR)
    polygon([(cx - w * 0.036, h * 0.635), (cx + w * 0.036, h * 0.635), (cx, h * 0.72)], SKIN)
    for side in (-1, 1):
        ellipse((head[0] + side * w * 0.071, head[1] + h * 0.015), (w * 0.013, h * 0.04), SKIN)
    ellipse(head, (w * 0.073, h * 0.155), SKIN, tilt)
    ellipse((head[0], head[1] - h * 0.02), (w * 0.078, h * 0.15), HAIR, tilt, 180, 360)
    ellipse((head[0] + w * 0.025, head[1] - h * 0.11), (w * 0.062, h * 0.05), HAIR, tilt + 14)

    light = np.zeros((height // 8, width // 8), np.float32)
    cv2.circle(light, (int((cx - w * 0.08) / 8), int(h * 0.35 / 8)), int(h * 0.45 / 8), 1.0, -1)
    light = cv2.resize(cv2.GaussianBlur(light, (0, 0), h / 40), (width, height))
    shade = (0.78 + 0.32 * light)[:, :, None]
    inside = figure > 0
    frame[inside] = np.clip(frame[inside] * shade[inside], 0, 255).astype(np.uint8)
    return frame


def key_mask(frame: np.ndarray) -> np.ndarray:
    distance = np.abs(frame.astype(np.float32) - KEY).sum(axis=2)
    return np.clip((distance - 40.0) / 120.0, 0.0, 1.0)


class DemoCamera:
    """Behaves like an opened ``cv2.VideoCapture`` for the engine."""

    def __init__(self, width: int, height: int, fps: int) -> None:
        self.width, self.height, self.interval = width, height, 1.0 / fps
        self.started = time.perf_counter()
        self.last = 0.0

    def read(self) -> tuple[bool, np.ndarray]:
        wait = self.last + self.interval - time.perf_counter()
        if wait > 0:
            time.sleep(wait)
        self.last = time.perf_counter()
        return True, draw_person(self.width, self.height, self.last - self.started)

    def release(self) -> None:
        pass


def open_demo_camera(index: int, width: int, height: int, fps: int) -> DemoCamera:
    return DemoCamera(width, height, fps)


class DemoVision:
    def observe(self, frame: np.ndarray, timestamp: int, with_face: bool) -> Observation:
        return Observation()

    def segment(self, frame: np.ndarray, timestamp: int, smooth: bool = True) -> np.ndarray:
        return key_mask(frame)

    def close(self) -> None:
        pass
