from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# MediaPipe hand landmark indices.
WRIST = 0
THUMB_TIP = 4
INDEX = (5, 6, 7, 8)
MIDDLE = (9, 10, 11, 12)
RING = (13, 14, 15, 16)
PINKY = (17, 18, 19, 20)
FINGERS = (INDEX, MIDDLE, RING, PINKY)


@dataclass(frozen=True)
class Hand:
    points: np.ndarray  # (21, 2) in pixels

    @property
    def size(self) -> float:
        """Palm size: the larger of palm width and wrist-to-middle-knuckle length."""
        p = self.points
        return max(float(np.linalg.norm(p[5] - p[17])), float(np.linalg.norm(p[0] - p[9])))

    @property
    def palm_centre(self) -> np.ndarray:
        return self.points[[0, 5, 9, 13, 17]].mean(axis=0)


@dataclass(frozen=True)
class Face:
    forehead: np.ndarray  # (2,) in pixels
    width: float


@dataclass(frozen=True)
class Observation:
    hands: list[Hand] = field(default_factory=list)
    face: Face | None = None


def hand_from_landmarks(landmarks, width: int, height: int) -> Hand | None:
    if len(landmarks) != 21:
        return None
    points = np.array([(p.x * width, p.y * height) for p in landmarks], dtype=np.float32)
    if not np.isfinite(points).all():
        return None
    return Hand(points)


# Face Mesh indices: mid-forehead and the two face edges at ear height.
_FOREHEAD = 151
_FACE_EDGES = (234, 454)


def face_from_landmarks(landmarks, width: int, height: int) -> Face | None:
    if len(landmarks) <= max(_FOREHEAD, *_FACE_EDGES):
        return None
    left, right = (landmarks[i] for i in _FACE_EDGES)
    face_width = float(np.hypot((left.x - right.x) * width, (left.y - right.y) * height))
    if not np.isfinite(face_width) or face_width < 20.0:
        return None
    top = landmarks[_FOREHEAD]
    return Face(np.array((top.x * width, top.y * height), dtype=np.float32), face_width)
