from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from ..compositing import composite


class Direction(StrEnum):
    OUT = "out"
    IN = "in"


@dataclass
class Scene:
    frame: np.ndarray        # live camera frame, BGR uint8
    background: np.ndarray   # what is seen when the person is gone, BGR uint8
    mask: np.ndarray         # person probability, float32 in [0, 1]


class Effect(ABC):
    """A way to leave the frame and come back, or, for ``kind = "toggle"``, a mode that is
    switched on and off while you stay in view.

    ``render`` is called with the time since the transition started. Effects may keep
    per-transition state, set up in ``begin``; only one transition runs at a time.
    """

    id: str
    name: str
    description: str
    default_gesture: str
    kind = "vanish"
    active_label = "Hidden"
    out_seconds: float
    in_seconds: float

    def begin(self, scene: Scene, direction: Direction) -> None:  # noqa: B027
        """Called once on the first frame of a transition."""

    @abstractmethod
    def render(self, scene: Scene, direction: Direction, t: float) -> np.ndarray:
        """Frame for time ``t`` (seconds) into the transition."""

    def render_hidden(self, scene: Scene, t: float) -> np.ndarray:
        """Frame while the person is away; ``t`` is seconds since they vanished."""
        return scene.background.copy()

    @staticmethod
    def person(scene: Scene, alpha: np.ndarray | float = 1.0) -> np.ndarray:
        return composite(scene.frame, scene.background, scene.mask * alpha)
