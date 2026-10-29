import numpy as np

from hands import open_hand, thumb_hand
from hocus import backgrounds
from hocus.director import Phase
from hocus.engine import Engine
from hocus.settings import SettingsStore
from hocus.vision.observation import Observation


class FakeVision:
    def __init__(self):
        self.hands = []

    def observe(self, frame, timestamp, with_face):
        return Observation(list(self.hands), None)

    def segment(self, frame, timestamp, smooth=True):
        mask = np.zeros(frame.shape[:2], np.float32)
        mask[40:, 120:200] = 1.0
        return mask


def make_engine(tmp_path, **patch):
    store = SettingsStore(tmp_path / "settings.json")
    store.update({"background": {"mode": "preset"}, **patch})
    events = []
    engine = Engine(store, events.append, lambda frame: None)
    engine.settings = store.current
    engine.vision = FakeVision()
    return engine, events


def frames(engine, start, end, step=0.05):
    frame = np.full((180, 320, 3), 200, np.uint8)
    t, out = start, None
    while t <= end + 1e-9:
        out = engine._process(frame, t)
        t += step
    return out


def test_palms_together_swaps_you_for_a_duck_and_back(tmp_path):
    engine, events = make_engine(tmp_path)
    engine.vision.hands = [open_hand(296), open_hand(344)]
    frames(engine, 0.0, 0.5)
    assert events == [{"type": "effect", "effect": "switcheroo", "direction": "out"}]
    engine.vision.hands = []
    hidden = frames(engine, 0.55, 2.0)
    assert engine.director.phase is Phase.HIDDEN
    expected = backgrounds.preset(engine.settings["background"]["preset"], 320, 180)
    assert np.array_equal(hidden[60, 160], expected[60, 160]), "person replaced"
    engine.vision.hands = [open_hand(296), open_hand(344)]
    frames(engine, 2.05, 2.5)
    assert events[-1]["direction"] == "in"


def test_room_mode_waits_for_a_captured_room(tmp_path):
    engine, events = make_engine(tmp_path, background={"mode": "room"})
    engine.vision.hands = [open_hand(296), open_hand(344)]
    out = frames(engine, 0.0, 1.0)
    assert events == [] and engine.director.phase is Phase.PRESENT
    assert out[0, 0, 0] == 200  # raw camera frame passes straight through


def test_room_capture_rejects_a_plate_with_someone_in_it(tmp_path):
    engine, events = make_engine(tmp_path, background={"mode": "room"})
    engine._start_plate()
    frames(engine, engine._plate_job["started"], engine._plate_job["started"] + 5.0)
    assert engine._plate is None
    assert events[-1]["level"] == "error"


def test_disabling_the_active_effect_resets_the_scene(tmp_path):
    engine, _ = make_engine(tmp_path)
    engine.director.request("blink")
    frames(engine, 0.0, 0.1)
    settings = engine.store.update({"effects": {"blink": {"enabled": False}}})
    engine._apply(settings, initial=True)
    assert engine.director.phase is Phase.PRESENT


def test_thumbs_up_plays_confetti_even_before_the_room_is_captured(tmp_path):
    engine, events = make_engine(tmp_path, background={"mode": "room"})
    engine.vision.hands = [thumb_hand()]
    out = frames(engine, 0.0, 0.6)
    assert {"type": "effect", "effect": "confetti", "direction": "out"} in events
    assert engine.director.phase is Phase.PRESENT
    assert np.abs(out.astype(int) - 200).mean() > 0.5, "confetti drawn"
    engine.vision.hands = []
    frames(engine, 0.65, 4.5)
    assert engine._playing == {}


def test_try_button_plays_a_reaction(tmp_path):
    engine, events = make_engine(tmp_path)
    engine.toggle("hearts")
    engine._commands.get_nowait()()
    frames(engine, 0.0, 0.1)
    assert events[-1]["effect"] == "hearts" and "hearts" in engine._playing


def test_disabled_reaction_does_not_play(tmp_path):
    engine, events = make_engine(tmp_path, effects={"confetti": {"enabled": False}})
    engine.vision.hands = [thumb_hand()]
    frames(engine, 0.0, 0.6)
    assert events == []


def test_demo_person_is_matted_exactly():
    from hocus.demo import DemoVision, draw_person

    frame = draw_person(320, 180, 0.0)
    mask = DemoVision().segment(frame, 0)
    assert mask[150, 160] == 1.0 and mask[10, 10] == 0.0
