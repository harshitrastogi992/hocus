from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision.observation import Observation
from . import shapes


@dataclass(frozen=True)
class GestureSpec:
    id: str
    label: str
    hint: str
    hold_seconds: float
    needs_face: bool = False   # run face detection while this gesture is watched


GESTURES: dict[str, GestureSpec] = {spec.id: spec for spec in (
    GestureSpec("v_sign", "V sign", "Index and middle finger up and apart", 0.15),
    GestureSpec("palms_together", "Palms together", "Both open hands pressed together", 0.25),
    GestureSpec("forehead_tap", "Forehead tap",
                "Index and middle finger together, touching your forehead", 1.0,
                needs_face=True),
    GestureSpec("open_palm", "Open palm", "One flat hand raised, fingers pointing up", 1.0),
    GestureSpec("finger_cross", "Crossed fingers",
                "Index fingers of both hands crossed in a plus sign", 0.25),
    GestureSpec("index_up", "Finger up", "Index finger pointing up, other fingers folded", 0.8),
    GestureSpec("thumbs_up", "Thumbs up", "Fist with the thumb pointing up, away from your face",
                0.3, needs_face=True),
    GestureSpec("thumbs_down", "Thumbs down", "Fist with the thumb pointing down", 0.3,
                needs_face=True),
    GestureSpec("heart_hands", "Heart hands",
                "Both hands make a heart: index tips touch at the top, thumbs at the bottom", 0.3),
)}

TWO_HANDED = (
    ("palms_together", shapes.are_palms_together),
    ("heart_hands", shapes.is_heart),
    ("finger_cross", shapes.are_fingers_crossed),
)


def detect(observation: Observation, wanted: set[str]) -> set[str]:
    """Return the wanted gestures visible in this observation.

    Two-handed gestures take priority over one-hand shapes. A V sign or raised finger
    made at the forehead is ignored so the forehead tap cannot double as either, and
    a thumb is ignored next to the other hand, where a half-formed heart looks like one,
    or next to the face, where a fist resting on the chin looks like one.
    """
    found: set[str] = set()
    hands = observation.hands
    if len(hands) >= 2:
        for gesture, test in TWO_HANDED:
            if gesture in wanted and test(*hands[:2]):
                return {gesture}
    face = observation.face
    for i, hand in enumerate(hands):
        if "forehead_tap" in wanted and face is not None and shapes.is_forehead_tap(hand, face):
            found.add("forehead_tap")
            continue
        at_forehead = shapes.near_forehead(hand, face)
        if "v_sign" in wanted and not at_forehead and shapes.is_v_sign(hand):
            found.add("v_sign")
        elif "index_up" in wanted and not at_forehead and shapes.is_index_up(hand):
            found.add("index_up")
        elif "open_palm" in wanted and shapes.is_open_palm(hand):
            found.add("open_palm")
        elif ({"thumbs_up", "thumbs_down"} & wanted and not _hand_nearby(hands, i)
              and not shapes.near_face(hand, face)):
            direction = shapes.thumb_direction(hand)
            if direction and f"thumbs_{direction}" in wanted:
                found.add(f"thumbs_{direction}")
    return found


def _hand_nearby(hands: list, index: int) -> bool:
    hand = hands[index]
    return any(np.linalg.norm(other.palm_centre - hand.palm_centre) < hand.size * 2.5
               for j, other in enumerate(hands) if j != index)
