"""Hand-shape tests on landmark geometry, all scale-invariant."""

from __future__ import annotations

import numpy as np

from ..vision.observation import FINGERS, INDEX, MIDDLE, PINKY, RING, THUMB_TIP, Face, Hand


def finger_length(points: np.ndarray, finger: tuple[int, ...]) -> float:
    return float(np.linalg.norm(np.diff(points[list(finger)], axis=0), axis=1).sum())


def is_straight(points: np.ndarray, finger: tuple[int, ...], ratio: float = 0.80) -> bool:
    length = finger_length(points, finger)
    return length > 8.0 and np.linalg.norm(points[finger[3]] - points[finger[0]]) >= length * ratio


def is_extended(points: np.ndarray, finger: tuple[int, ...]) -> bool:
    """The tip sits clearly further from the wrist than the middle joint."""
    wrist = points[0]
    tip, middle_joint = points[finger[3]], points[finger[1]]
    return np.linalg.norm(tip - wrist) > np.linalg.norm(middle_joint - wrist) * 1.15


def is_folded(points: np.ndarray, finger: tuple[int, ...], reference: float) -> bool:
    return np.linalg.norm(points[finger[3]] - points[finger[0]]) <= reference * 0.60


def _two_finger_pose(hand: Hand) -> tuple[float, float] | None:
    """For index and middle straight with ring and pinky folded, return (gap, length)."""
    p = hand.points
    if not (is_straight(p, INDEX) and is_straight(p, MIDDLE)):
        return None
    reference = min(finger_length(p, INDEX), finger_length(p, MIDDLE))
    if not (is_folded(p, RING, reference) and is_folded(p, PINKY, reference)):
        return None
    return float(np.linalg.norm(p[INDEX[3]] - p[MIDDLE[3]])), reference


def is_v_sign(hand: Hand) -> bool:
    pose = _two_finger_pose(hand)
    if pose is None:
        return False
    gap, length = pose
    p = hand.points
    a, b = p[INDEX[3]] - p[INDEX[0]], p[MIDDLE[3]] - p[MIDDLE[0]]
    cosine = float(np.dot(a, b) / max(1e-6, np.linalg.norm(a) * np.linalg.norm(b)))
    return gap >= length * 0.45 and cosine < np.cos(np.radians(12))


def is_forehead_tap(hand: Hand, face: Face) -> bool:
    pose = _two_finger_pose(hand)
    if pose is None:
        return False
    gap, length = pose
    if gap > length * 0.42:
        return False
    p = hand.points
    tips = (p[INDEX[3]] + p[MIDDLE[3]]) * 0.5
    pads = (p[INDEX[2]] + p[MIDDLE[2]]) * 0.5
    reach = face.width * 0.45
    return min(np.linalg.norm(tips - face.forehead), np.linalg.norm(pads - face.forehead)) <= reach


def near_forehead(hand: Hand, face: Face | None) -> bool:
    if face is None:
        return False
    return np.linalg.norm(hand.points[[8, 12]].mean(axis=0) - face.forehead) <= face.width * 0.9


def near_face(hand: Hand, face: Face | None) -> bool:
    """The hand is around the face: forehead down to the chin."""
    if face is None:
        return False
    chin = face.forehead + (0.0, face.width * 1.1)
    centre = hand.palm_centre
    reach = face.width * 0.75
    return min(np.linalg.norm(centre - face.forehead), np.linalg.norm(centre - chin),
               np.linalg.norm(centre - (face.forehead + chin) / 2)) <= reach


def open_fingers(hand: Hand) -> int:
    return sum(is_extended(hand.points, finger) for finger in FINGERS)


def are_palms_together(first: Hand, second: Hand) -> bool:
    """Two distinct, open, similarly oriented hands whose palms nearly touch."""
    sizes = first.size, second.size
    if min(sizes) < 8.0 or max(sizes) > min(sizes) * 2.2:
        return False
    size = sum(sizes) * 0.5
    # Two reports of the same hand overlap point for point; real hands are mirrored.
    if float(np.linalg.norm(first.points - second.points, axis=1).mean()) < size * 0.3:
        return False
    if open_fingers(first) < 3 or open_fingers(second) < 3:
        return False
    up_a = first.points[9] - first.points[0]
    up_b = second.points[9] - second.points[0]
    alignment = float(np.dot(up_a, up_b) / max(1e-6, np.linalg.norm(up_a) * np.linalg.norm(up_b)))
    tips_a = first.points[[8, 12, 16, 20]].mean(axis=0)
    tips_b = second.points[[8, 12, 16, 20]].mean(axis=0)
    return (alignment > 0.25
            and np.linalg.norm(first.palm_centre - second.palm_centre) < size * 1.55
            and np.linalg.norm(tips_a - tips_b) < size * 1.9)


def thumb_direction(hand: Hand) -> str | None:
    """'up' or 'down' for a fist with the thumb sticking out vertically, else None."""
    p = hand.points
    if any(is_extended(p, finger) for finger in FINGERS):
        return None
    thumb = p[THUMB_TIP] - p[2]
    length = float(np.linalg.norm(thumb))
    if length < hand.size * 0.45 or abs(thumb[1]) < length * 0.7:
        return None
    fingers_y = p[5:21, 1]
    if thumb[1] < 0 and p[THUMB_TIP][1] < fingers_y.min():
        return "up"
    if thumb[1] > 0 and p[THUMB_TIP][1] > fingers_y.max():
        return "down"
    return None


def is_open_palm(hand: Hand) -> bool:
    """All four fingers straight and pointing up."""
    p = hand.points
    if not all(is_extended(p, f) and is_straight(p, f, 0.75) for f in FINGERS):
        return False
    up = p[MIDDLE[0]] - p[0]
    return up[1] < -0.8 * float(np.linalg.norm(up))


def is_index_up(hand: Hand) -> bool:
    p = hand.points
    if not (is_extended(p, INDEX) and is_straight(p, INDEX)):
        return False
    reference = finger_length(p, INDEX)
    if not all(is_folded(p, f, reference) for f in (MIDDLE, RING, PINKY)):
        return False
    direction = p[INDEX[3]] - p[INDEX[0]]
    return direction[1] < -0.8 * float(np.linalg.norm(direction))


def is_heart(first: Hand, second: Hand) -> bool:
    """Index tips touch at the top, thumb tips touch at the bottom, with a gap between."""
    a, b = first.points, second.points
    size = (first.size + second.size) * 0.5
    if np.linalg.norm(a[THUMB_TIP] - b[THUMB_TIP]) > size * 0.6:
        return False
    if np.linalg.norm(a[INDEX[3]] - b[INDEX[3]]) > size * 0.6:
        return False
    top = (a[INDEX[3]] + b[INDEX[3]]) * 0.5
    bottom = (a[THUMB_TIP] + b[THUMB_TIP]) * 0.5
    # Pressed palms also touch at the tips; a heart keeps the index knuckles apart.
    return (top[1] < bottom[1] - size * 0.5
            and np.linalg.norm(a[INDEX[0]] - b[INDEX[0]]) > size * 0.9)


def _cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))


def segments_intersect(p1: np.ndarray, p2: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> bool:
    return (_cross(p1, p2, q1) * _cross(p1, p2, q2) < 0
            and _cross(q1, q2, p1) * _cross(q1, q2, p2) < 0)


def are_fingers_crossed(first: Hand, second: Hand) -> bool:
    """Straight index fingers of both hands crossing in a plus sign."""
    a, b = first.points, second.points
    if not (is_straight(a, INDEX, 0.75) and is_straight(b, INDEX, 0.75)):
        return False
    da, db = a[INDEX[3]] - a[INDEX[0]], b[INDEX[3]] - b[INDEX[0]]
    cosine = abs(float(np.dot(da, db))) / max(1e-6, float(np.linalg.norm(da) * np.linalg.norm(db)))
    if cosine > np.cos(np.radians(40)):
        return False
    return segments_intersect(a[INDEX[0]], a[INDEX[3]], b[INDEX[0]], b[INDEX[3]])
