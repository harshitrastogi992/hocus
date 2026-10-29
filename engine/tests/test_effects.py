import numpy as np
import pytest

from hocus import backgrounds
from hocus.compositing import composite, cover_fit, person_box, person_coverage
from hocus.effects import Direction, Scene, create_effects


@pytest.fixture
def scene():
    frame = np.full((180, 320, 3), 200, np.uint8)
    background = np.full_like(frame, 20)
    mask = np.zeros((180, 320), np.float32)
    mask[40:180, 120:200] = 1.0
    return Scene(frame, background, mask)


EFFECTS = create_effects().values()
VANISH = [e for e in EFFECTS if e.kind == "vanish"]
TOGGLES = [e for e in EFFECTS if e.kind == "toggle"]


@pytest.mark.parametrize("effect", VANISH, ids=lambda e: e.id)
def test_effect_leaves_then_returns(effect, scene):
    effect.begin(scene, Direction.OUT)
    start = effect.render(scene, Direction.OUT, 0.0)
    end = effect.render(scene, Direction.OUT, effect.out_seconds)
    assert start.shape == scene.frame.shape and start.dtype == np.uint8
    person = (slice(100, 140), slice(140, 180))
    assert start[person].mean() > 120, "person visible at the start"
    assert end[person].mean() < 120, "person gone at the end"
    effect.begin(scene, Direction.IN)
    back = effect.render(scene, Direction.IN, effect.in_seconds)
    assert back[person].mean() > 120, "person visible after returning"


@pytest.mark.parametrize("effect", TOGGLES, ids=lambda e: e.id)
def test_toggle_keeps_you_in_view_and_changes_the_scene(effect, scene):
    plain = composite(scene.frame, scene.background, scene.mask)
    effect.begin(scene, Direction.OUT)
    for t in np.linspace(0, effect.out_seconds, 6):
        effect.render(scene, Direction.OUT, float(t))
    on = effect.render_hidden(scene, 0.5)
    person = (slice(100, 140), slice(140, 180))
    assert on[person].mean() > 120, "person still visible"
    assert np.abs(on.astype(int) - plain).mean() > 2, "mode visibly changes the picture"
    effect.begin(scene, Direction.IN)
    off = effect.render(scene, Direction.IN, effect.in_seconds)
    assert np.abs(off.astype(int) - plain).mean() < 2, "back to normal when switched off"


def test_clones_appear_beside_you(scene):
    effect = create_effects()["clones"]
    effect.begin(scene, Direction.OUT)
    effect.render(scene, Direction.OUT, effect.out_seconds)
    on = effect.render_hidden(scene, 0.5)
    left, right = on[120, 60:110], on[120, 210:260]
    assert left.mean() > 60 and right.mean() > 60, "a clone stands on each side"


def test_cloak_leaves_a_ripple_not_a_person(scene):
    effect = create_effects()["cloak"]
    hidden = effect.render_hidden(scene, 0.4)
    assert hidden[100:140, 140:180].mean() < 60
    edge = hidden[100:140, 115:125]
    assert edge.mean() > scene.background.mean(), "a shimmer marks the outline"


def test_switcheroo_leaves_a_duck_while_hidden(scene):
    effect = create_effects()["switcheroo"]
    effect.begin(scene, Direction.OUT)
    hidden = effect.render_hidden(scene, 1.0)
    assert np.any(hidden != scene.background)


def test_compositing_helpers(scene):
    out = composite(scene.frame, scene.background, scene.mask)
    assert out[100, 160, 0] == 200 and out[10, 10, 0] == 20
    assert person_box(scene.mask) == (120, 40, 200, 180)
    assert person_coverage(scene.mask) == pytest.approx(80 * 140 / (320 * 180))
    assert cover_fit(np.zeros((100, 400, 3), np.uint8), 320, 180).shape == (180, 320, 3)


@pytest.mark.parametrize("name", list(backgrounds.PRESETS))
def test_presets_render(name):
    image = backgrounds.preset(name, 320, 180)
    assert image.shape == (180, 320, 3) and image.std() > 0
