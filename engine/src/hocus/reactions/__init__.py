from __future__ import annotations

from .base import Reaction
from .confetti import Confetti
from .hearts import Hearts
from .raincloud import RainCloud

REACTION_TYPES: tuple[type[Reaction], ...] = (Confetti, Hearts, RainCloud)


def create_reactions() -> dict[str, Reaction]:
    return {reaction_type.id: reaction_type() for reaction_type in REACTION_TYPES}


__all__ = ["Reaction", "REACTION_TYPES", "create_reactions"]
