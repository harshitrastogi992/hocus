from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .effects import Direction, Effect
from .gestures.catalog import GESTURES
from .gestures.hold import HoldTimer


class Phase(StrEnum):
    PRESENT = "present"
    LEAVING = "leaving"
    HIDDEN = "hidden"
    RETURNING = "returning"


@dataclass(frozen=True)
class Transition:
    effect: str
    direction: Direction


class Director:
    """Decides when to leave and come back, from held gestures or manual requests.

    You come back with the same gesture you left with. Every gesture must be released
    and made again after a transition, so a hand still raised cannot retrigger it.
    Gestures bound to an id that is not an effect are cues for one-shot reactions: they
    are collected in ``cues`` and never change the phase.
    """

    def __init__(self, effects: dict[str, Effect]) -> None:
        self.effects = effects
        self.bindings: dict[str, str] = {}
        self.timers = {g: HoldTimer(spec.hold_seconds) for g, spec in GESTURES.items()}
        self.phase = Phase.PRESENT
        self.effect_id: str | None = None
        self.started = 0.0
        self.hold: tuple[str, float] | None = None
        self._pending: Transition | None = None
        self.cues: list[str] = []

    def bind(self, bindings: dict[str, str]) -> None:
        """Map gesture id -> effect id for the enabled effects."""
        self.bindings = dict(bindings)

    @property
    def effect(self) -> Effect | None:
        return self.effects.get(self.effect_id) if self.effect_id else None

    def is_cue(self, gesture: str) -> bool:
        return self.bindings[gesture] not in self.effects

    def watching(self, with_background: bool = True) -> set[str]:
        """Gestures the caller should detect. Effects need a background; cues do not."""
        return {g for g in self.bindings if with_background or self.is_cue(g)}

    def listening_for(self) -> set[str]:
        if self.phase is Phase.PRESENT:
            return set(self.bindings)
        if self.phase is Phase.HIDDEN:
            return {g for g, e in self.bindings.items() if e == self.effect_id or self.is_cue(g)}
        return set()

    def request(self, effect_id: str | None = None) -> None:
        """Manual toggle: leave with ``effect_id`` (or the first bound effect), or return."""
        if self.phase is Phase.PRESENT:
            bound = [e for e in self.bindings.values() if e in self.effects]
            chosen = effect_id or next(
                (e for e in bound if self.effects[e].kind == "vanish"), next(iter(bound), None))
            if chosen in self.effects:
                self._pending = Transition(chosen, Direction.OUT)
        elif self.phase is Phase.HIDDEN and self.effect_id:
            self._pending = Transition(self.effect_id, Direction.IN)

    def update(self, detected: set[str], now: float) -> Transition | None:
        """Advance the state machine. Returns a transition on the frame it starts."""
        self.hold = None
        self.cues = []
        started = self._pending
        self._pending = None
        listening = self.listening_for()
        for gesture, timer in self.timers.items():
            # Timers see every detection, even mid-transition, so a release is noticed.
            progress = timer.update(gesture in detected, now)
            if progress is None or started is not None or gesture not in listening:
                continue
            if progress >= 1.0 and self.is_cue(gesture):
                self.cues.append(self.bindings[gesture])
            elif progress >= 1.0:
                direction = Direction.OUT if self.phase is Phase.PRESENT else Direction.IN
                started = Transition(self.bindings[gesture], direction)
            elif GESTURES[gesture].hold_seconds >= 0.5:
                self.hold = (gesture, progress)

        if started is not None:
            self.effect_id = started.effect
            self.phase = Phase.LEAVING if started.direction is Direction.OUT else Phase.RETURNING
            self.started = now
            self.hold = None
            for timer in self.timers.values():
                timer.disarm()
            return started

        effect = self.effect
        if self.phase is Phase.LEAVING and effect and now - self.started >= effect.out_seconds:
            self.phase, self.started = Phase.HIDDEN, now
        elif self.phase is Phase.RETURNING and effect and now - self.started >= effect.in_seconds:
            self.phase, self.effect_id = Phase.PRESENT, None
        return None

    def reset(self) -> None:
        self.phase, self.effect_id, self.hold, self._pending = Phase.PRESENT, None, None, None
        for timer in self.timers.values():
            timer.disarm()
