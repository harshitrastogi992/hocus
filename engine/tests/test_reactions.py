import numpy as np
import pytest

from hands import heart_hands
from hocus.reactions import create_reactions
from hocus.vision.observation import Observation


@pytest.fixture
def stage():
    output = np.full((360, 640, 3), 120, np.uint8)
    mask = np.zeros((360, 640), np.float32)
    mask[90:, 260:380] = 1.0
    return output, mask


@pytest.mark.parametrize("reaction", create_reactions().values(), ids=lambda r: r.id)
def test_reaction_plays_and_finishes(reaction, stage):
    output, mask = stage
    reaction.begin(output.shape[:2], None)
    middle = reaction.render(output, mask, True, reaction.seconds * 0.4)
    end = reaction.render(output, mask, True, reaction.seconds)
    assert middle.shape == output.shape and middle.dtype == np.uint8
    assert np.abs(middle.astype(int) - output).mean() > 0.5, "visible while playing"
    assert np.abs(end.astype(int) - output).mean() < 1.0, "gone at the end"


def test_confetti_stays_behind_the_person(stage):
    output, mask = stage
    confetti = create_reactions()["confetti"]
    confetti.begin(output.shape[:2], None)
    confetti._pieces["front"][:] = False
    frames = [confetti.render(output, mask, True, t) for t in np.linspace(0.2, 2.0, 10)]
    person = mask > 0.5
    assert all(np.array_equal(f[person], output[person]) for f in frames)
    assert any(np.abs(f[~person].astype(int) - output[~person]).mean() > 0.5 for f in frames)


def test_hearts_start_at_the_hands():
    hearts = create_reactions()["hearts"]
    hearts.begin((480, 640), Observation(list(heart_hands())))
    x, y = hearts._origin
    assert abs(x - 320) < 30 and 250 < y < 400


def test_rain_cloud_follows_the_head(stage):
    output, mask = stage
    cloud = create_reactions()["raincloud"]
    cloud.begin(output.shape[:2], None)
    for t in np.linspace(0, 1.0, 12):
        cloud.render(output, mask, True, float(t))
    assert abs(cloud._anchor[0] - 320) < 5
    moved = np.roll(mask, 150, axis=1)
    for t in np.linspace(1.0, 2.0, 12):
        cloud.render(output, moved, True, float(t))
    assert abs(cloud._anchor[0] - 470) < 10
