from __future__ import annotations

from .base import Direction, Effect, Scene
from .blink import Blink
from .cloak import Cloak
from .clones import Clones
from .spotlight import Spotlight
from .stardust import Stardust
from .switcheroo import Switcheroo

EFFECT_TYPES: tuple[type[Effect], ...] = (Stardust, Switcheroo, Blink, Cloak, Clones, Spotlight)


def create_effects() -> dict[str, Effect]:
    return {effect_type.id: effect_type() for effect_type in EFFECT_TYPES}


__all__ = ["Direction", "Effect", "Scene", "EFFECT_TYPES", "create_effects"]
