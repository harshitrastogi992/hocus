from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..compositing import composite
from ..vision.observation import Observation


class Reaction(ABC):
    """A short overlay played once over whatever is on screen. You stay in view.

    Reactions need no background, so they also work before a room is captured.
    ``mask`` is the person matte; ``person_visible`` says whether the person is drawn in
    ``output`` where the matte is, so a reaction can play behind them.
    """

    id: str
    name: str
    description: str
    default_gesture: str
    seconds: float
    kind = "reaction"
    active_label = ""

    def begin(self, shape: tuple[int, int], observation: Observation | None) -> None:  # noqa: B027
        """Called once when the reaction is triggered. ``shape`` is (height, width)."""

    @abstractmethod
    def render(self, output: np.ndarray, mask: np.ndarray, person_visible: bool,
               t: float) -> np.ndarray:
        """Frame for time ``t`` (seconds) into the reaction."""

    @staticmethod
    def behind(output: np.ndarray, layer: np.ndarray, mask: np.ndarray,
               person_visible: bool) -> np.ndarray:
        """Keep the person from ``output`` in front of ``layer``."""
        return composite(output, layer, mask) if person_visible else layer


def fade(t: float, total: float, fade_in: float = 0.15, fade_out: float = 0.6) -> float:
    return float(np.clip(min(t / fade_in, (total - t) / fade_out), 0.0, 1.0))
