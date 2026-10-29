"""Render the README gallery and hero animation with the placeholder person.

Runs the real engine pipeline (director, effects, reactions, compositing) on frames
from hocus.demo, so the images match what the app shows.

Usage: engine/.venv/bin/python scripts/render_readme_media.py [output_dir]
"""

import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from hocus.demo import DemoVision, draw_person
from hocus.engine import Engine
from hocus.settings import SettingsStore

WIDTH, HEIGHT = 1280, 720
STEP = 1 / 30

# effect id -> (backdrop, seconds after triggering at which to take the still)
STILLS = {
    "stardust": ("night", 0.5),
    "switcheroo": ("studio", 0.55),
    "blink": ("night", 0.42),
    "cloak": ("night", 0.55),
    "clones": ("studio", 2.0),
    "spotlight": ("studio", 1.5),
    "confetti": ("night", 1.0),
    "hearts": ("night", 1.1),
    "raincloud": ("studio", 1.7),
}


def make_engine(backdrop: str, folder: Path) -> Engine:
    store = SettingsStore(folder / f"{backdrop}.json")
    store.update({"background": {"mode": "preset", "preset": backdrop}})
    engine = Engine(store, lambda message: None, lambda frame: None, vision_factory=DemoVision)
    engine.settings = store.current
    engine.vision = DemoVision()
    return engine


def advance(engine: Engine, start: float, end: float) -> np.ndarray:
    t, output = start, None
    while t <= end + 1e-9:
        output = engine._process(draw_person(WIDTH, HEIGHT, t), t)
        t += STEP
    return output


def trigger(engine: Engine, effect_id: str) -> None:
    engine.toggle(effect_id)
    engine._commands.get_nowait()()


def render_stills(out: Path, folder: Path) -> None:
    for effect_id, (backdrop, at) in STILLS.items():
        engine = make_engine(backdrop, folder)
        advance(engine, 0.0, 0.5)
        trigger(engine, effect_id)
        frame = advance(engine, 0.5 + STEP, 0.5 + at)
        small = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / f"{effect_id}.jpg"), small, (cv2.IMWRITE_JPEG_QUALITY, 84))
        print(f"{effect_id}.jpg")


def render_hero(out: Path, folder: Path) -> None:
    engine = make_engine("night", folder)
    timeline = {0.6: "stardust", 3.2: "stardust", 5.2: "confetti"}
    frames, t, fps = [], 0.0, 12
    while t < 8.4:
        for at, effect_id in timeline.items():
            if at <= t < at + 1 / fps:
                trigger(engine, effect_id)
        frame = advance(engine, t, t + 1 / fps - STEP)
        rgb = cv2.cvtColor(cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA),
                           cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(rgb).quantize(colors=128, method=Image.Quantize.MEDIANCUT))
        t += 1 / fps
    frames[0].save(out / "hero.gif", save_all=True, append_images=frames[1:],
                   duration=int(1000 / fps), loop=0, optimize=True)
    print("hero.gif", round((out / "hero.gif").stat().st_size / 1e6, 2), "MB")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/images")
    (out / "effects").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        render_stills(out / "effects", Path(folder))
        render_hero(out, Path(folder))


if __name__ == "__main__":
    main()
