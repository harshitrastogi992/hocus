"""Synthetic hand landmarks for tests, in pixels on a 640 x 480 frame."""

import numpy as np

from hocus.vision.observation import Face, Hand


def _finger(base, direction, length):
    direction = np.asarray(direction, np.float32)
    direction /= np.linalg.norm(direction)
    return [np.asarray(base, np.float32) + direction * length * f for f in (0, 0.4, 0.7, 1.0)]


def _folded(base):
    base = np.asarray(base, np.float32)
    return [base, base + (0, 8), base + (0, 14), base + (0, 10)]


def two_finger_hand(tip_x=320.0, tip_y=120.0, spread=0.0, length=80.0):
    """Index and middle straight towards (tip_x, tip_y); ring and pinky folded."""
    wrist = np.array((tip_x, tip_y + length + 90), np.float32)
    index_base, middle_base = wrist + (-14, -80), wrist + (4, -84)
    ring_base, pinky_base = wrist + (20, -78), wrist + (34, -70)
    index_dir = np.array((-spread * 2, -1), np.float32)
    middle_dir = np.array((spread * 2, -1), np.float32)
    points = [wrist, wrist + (-30, -20), wrist + (-40, -40), wrist + (-44, -55), wrist + (-40, -62)]
    points += _finger(index_base, index_dir, length)
    points += _finger(middle_base, middle_dir, length)
    points += _folded(ring_base) + _folded(pinky_base)
    return Hand(np.array(points, np.float32))


def open_hand(centre_x, upward=True):
    """Flat open hand, fingers pointing up (or down)."""
    sign = -1 if upward else 1
    wrist = np.array((centre_x, 336.0), np.float32)
    points = [wrist] + [wrist + (sign * -10 * i, sign * 18 * i) for i in range(1, 5)]
    for offset in (-29, -10, 10, 29):
        base = wrist + (offset, sign * 82)
        points += _finger(base, (0, sign), 96)
    return Hand(np.array(points, np.float32))


FACE = Face(np.array((320.0, 120.0), np.float32), 160.0)


def thumb_hand(up=True, x=320.0):
    """Sideways fist with the thumb pointing up (or down)."""
    points = np.array([
        (0, 40), (10, 20), (18, -5), (20, -30), (22, -55),
        (30, 0), (55, 0), (55, 15), (40, 15),
        (32, 18), (57, 18), (57, 33), (42, 33),
        (32, 34), (55, 34), (55, 48), (40, 48),
        (28, 50), (48, 50), (48, 62), (36, 62),
    ], np.float32)
    if not up:
        points[:, 1] *= -1
    return Hand(points + (x, 300))


def index_up_hand(tip_x=320.0, tip_y=120.0):
    """Index straight up; middle, ring and pinky folded."""
    points = two_finger_hand(tip_x, tip_y).points.copy()
    middle_base = points[9]
    points[9:13] = _folded(middle_base)
    return Hand(points)


def heart_hands():
    """Two hands forming a heart around (320, 330)."""
    def side(sign):
        local = np.array([
            (70, 120), (55, 110), (40, 100), (22, 90), (6, 82),
            (75, 40), (60, 15), (35, 0), (6, 0),
            (85, 50), (72, 25), (50, 12), (28, 12),
            (92, 62), (80, 40), (62, 30), (45, 30),
            (95, 75), (86, 56), (72, 48), (60, 48),
        ], np.float32)
        local[:, 0] *= sign
        return Hand(local + (320, 260))
    return side(-1), side(1)


def crossed_hands():
    """Two pointing hands whose index fingers cross in a plus sign."""
    upright = two_finger_hand(tip_x=320, tip_y=200, spread=0.0)
    centre = upright.points[[5, 8]].mean(axis=0)
    rotation = np.array([[0, -1], [1, 0]], np.float32)
    sideways = (upright.points - centre) @ rotation.T + centre
    return upright, Hand(sideways.astype(np.float32))
