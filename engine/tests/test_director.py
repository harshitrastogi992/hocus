from hocus.director import Director, Phase
from hocus.effects import Direction, create_effects


def director():
    d = Director(create_effects())
    d.bind({"v_sign": "stardust", "palms_together": "switcheroo", "forehead_tap": "blink"})
    return d


def run(d, gesture, start, end, step=0.05):
    transitions, t = [], start
    while t <= end + 1e-9:
        if (result := d.update({gesture} if gesture else set(), t)) is not None:
            transitions.append(result)
        t += step
    return transitions


def test_leave_and_return_with_the_same_gesture():
    d = director()
    [leave] = run(d, "v_sign", 0.0, 0.3)
    assert (leave.effect, leave.direction) == ("stardust", Direction.OUT)
    assert run(d, "v_sign", 0.35, 3.0) == []  # still holding: no instant return
    assert d.phase is Phase.HIDDEN
    run(d, None, 3.05, 3.5)
    [back] = run(d, "v_sign", 3.55, 3.9)
    assert back.direction is Direction.IN
    run(d, None, 3.95, 6.0)
    assert d.phase is Phase.PRESENT and d.effect_id is None


def test_another_gesture_does_not_bring_you_back():
    d = director()
    run(d, "palms_together", 0.0, 0.5)
    run(d, None, 0.55, 2.0)
    assert d.phase is Phase.HIDDEN
    assert run(d, "v_sign", 2.05, 3.0) == []
    assert d.phase is Phase.HIDDEN


def test_long_hold_reports_progress_and_resets_when_broken():
    d = director()
    run(d, "forehead_tap", 0.0, 0.5)
    gesture, progress = d.hold
    assert gesture == "forehead_tap" and 0.4 < progress < 0.6
    run(d, None, 0.55, 1.0)
    assert d.hold is None and d.phase is Phase.PRESENT
    [leave] = run(d, "forehead_tap", 1.05, 2.2)
    assert leave.effect == "blink"


def test_unbound_gestures_are_ignored():
    d = Director(create_effects())
    d.bind({"palms_together": "switcheroo"})
    assert run(d, "v_sign", 0.0, 1.0) == []


def test_manual_toggle():
    d = director()
    d.request("blink")
    assert d.update(set(), 0.0).effect == "blink"
    d.request()  # ignored mid-transition
    assert d.update(set(), 0.1) is None
    run(d, None, 0.15, 2.0)
    d.request()
    assert d.update(set(), 2.1).direction is Direction.IN


def test_reaction_gestures_cue_without_changing_the_phase():
    d = director()
    d.bind({**d.bindings, "thumbs_up": "confetti"})
    t, cues = 0.0, []
    while t < 0.6:
        d.update({"thumbs_up"}, t)
        cues += d.cues
        t += 0.05
    assert cues == ["confetti"] and d.phase is Phase.PRESENT
    assert d.watching(with_background=False) == {"thumbs_up"}


def test_reactions_also_play_while_hidden():
    d = director()
    d.bind({**d.bindings, "thumbs_up": "confetti"})
    run(d, "v_sign", 0.0, 0.3)
    run(d, None, 0.35, 3.0)
    assert d.phase is Phase.HIDDEN
    d.update({"thumbs_up"}, 3.05)
    assert d.update({"thumbs_up"}, 3.4) is None and d.cues == ["confetti"]


def test_vanish_button_prefers_a_vanishing_effect():
    d = Director(create_effects())
    d.bind({"finger_cross": "clones", "v_sign": "stardust"})
    d.request()
    assert d.update(set(), 0.0).effect == "stardust"
