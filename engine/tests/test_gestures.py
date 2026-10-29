import numpy as np

from hands import (
    FACE,
    crossed_hands,
    heart_hands,
    index_up_hand,
    open_hand,
    thumb_hand,
    two_finger_hand,
)
from hocus.gestures import catalog, shapes
from hocus.gestures.hold import HoldTimer
from hocus.vision.observation import Face, Hand, Observation

ALL = set(catalog.GESTURES)


def test_v_sign_needs_spread_fingers():
    assert shapes.is_v_sign(two_finger_hand(spread=0.3))
    assert not shapes.is_v_sign(two_finger_hand(spread=0.0))


def test_forehead_tap_needs_fingers_together_on_the_forehead():
    assert shapes.is_forehead_tap(two_finger_hand(), FACE)
    assert not shapes.is_forehead_tap(two_finger_hand(spread=0.3), FACE)
    assert not shapes.is_forehead_tap(two_finger_hand(tip_x=560, tip_y=300), FACE)


def test_palms_together():
    assert shapes.are_palms_together(open_hand(296), open_hand(344))
    assert not shapes.are_palms_together(open_hand(296), open_hand(560))
    assert not shapes.are_palms_together(open_hand(296), open_hand(344, upward=False))


def test_one_hand_reported_twice_is_not_two_hands():
    hand = open_hand(300)
    assert not shapes.are_palms_together(hand, Hand(hand.points + 1.5))


def test_fists_are_not_palms_together():
    def fist(x):
        points = open_hand(x).points.copy()
        for tip, joint in ((8, 6), (12, 10), (16, 14), (20, 18)):
            points[tip] = points[joint] + (0, 6)
            points[tip - 1] = points[joint] + (0, 3)
        return Hand(points)
    assert not shapes.are_palms_together(fist(296), fist(344))


def test_catalogue_priorities():
    assert catalog.detect(Observation([two_finger_hand()], FACE), ALL) == {"forehead_tap"}
    # A V made at the forehead is ignored rather than read as a V sign.
    assert catalog.detect(Observation([two_finger_hand(spread=0.3)], FACE), ALL) == set()
    away = two_finger_hand(tip_x=560, tip_y=300, spread=0.3)
    assert catalog.detect(Observation([away], FACE), ALL) == {"v_sign"}
    assert catalog.detect(Observation([away], None), ALL) == {"v_sign"}
    both = Observation([open_hand(296), open_hand(344)], FACE)
    assert catalog.detect(both, ALL) == {"palms_together"}


def test_only_wanted_gestures_are_reported():
    away = two_finger_hand(tip_x=560, tip_y=300, spread=0.3)
    assert catalog.detect(Observation([away]), {"palms_together"}) == set()


def test_hold_timer_counts_and_survives_short_dropouts():
    timer = HoldTimer(1.0, grace=0.2)
    assert timer.update(True, 0.0) == 1e-3
    assert np.isclose(timer.update(True, 0.5), 0.5)
    assert np.isclose(timer.update(False, 0.6), 0.6)
    assert timer.update(True, 1.0) == 1.0
    assert timer.update(True, 1.1) is None


def test_hold_timer_restarts_after_a_long_break():
    timer = HoldTimer(1.0, grace=0.2)
    timer.update(True, 0.0)
    timer.update(True, 0.8)
    assert timer.update(False, 1.2) is None
    assert np.isclose(timer.update(True, 1.3), 1e-3)


def test_hold_timer_needs_release_after_disarm():
    timer = HoldTimer(0.0, grace=0.1)
    timer.disarm()
    assert timer.update(True, 0.0) is None
    assert timer.update(True, 2.0) is None
    assert timer.update(False, 2.05) is None
    assert timer.update(True, 2.08) is None  # dropout shorter than grace is not a release
    assert timer.update(False, 2.3) is None
    assert timer.update(True, 2.4) == 1.0


def test_thumbs_up_and_down():
    assert shapes.thumb_direction(thumb_hand()) == "up"
    assert shapes.thumb_direction(thumb_hand(up=False)) == "down"
    assert shapes.thumb_direction(open_hand(320)) is None
    assert shapes.thumb_direction(two_finger_hand()) is None


def test_one_hand_shapes_do_not_overlap():
    hands = {"thumb": thumb_hand(), "index": index_up_hand(), "open": open_hand(320),
             "v": two_finger_hand(spread=0.3), "pair": two_finger_hand()}
    found = {name: catalog.detect(Observation([hand]), ALL) for name, hand in hands.items()}
    assert found == {"thumb": {"thumbs_up"}, "index": {"index_up"}, "open": {"open_palm"},
                     "v": {"v_sign"}, "pair": set()}


def test_two_hand_shapes():
    assert catalog.detect(Observation(list(heart_hands())), ALL) == {"heart_hands"}
    assert catalog.detect(Observation(list(crossed_hands())), ALL) == {"finger_cross"}
    assert not shapes.is_heart(open_hand(296), open_hand(344))
    assert not shapes.are_fingers_crossed(two_finger_hand(200), two_finger_hand(440))


def test_thumb_at_the_chin_is_ignored():
    face = Face(np.array((330.0, 150.0), np.float32), 120.0)
    assert catalog.detect(Observation([thumb_hand(x=300)], face), ALL) == set()
    assert catalog.detect(Observation([thumb_hand(x=40)], face), ALL) == {"thumbs_up"}


def test_thumb_next_to_the_other_hand_is_ignored():
    near = Observation([thumb_hand(x=300), thumb_hand(x=360)])
    apart = Observation([thumb_hand(x=100), thumb_hand(x=520)])
    assert catalog.detect(near, ALL) == set()
    assert catalog.detect(apart, ALL) == {"thumbs_up"}
