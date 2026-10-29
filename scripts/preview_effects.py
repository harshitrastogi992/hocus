"""Render each effect on a synthetic person and report time per frame.

Usage: engine/.venv/bin/python scripts/preview_effects.py [output_dir]
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np

from hocus import backgrounds
from hocus.effects import Direction, Scene, create_effects
from hocus.reactions import create_reactions

WIDTH, HEIGHT = 1280, 720


def synthetic_scene() -> Scene:
    background = backgrounds.preset("night", WIDTH, HEIGHT)
    mask = np.zeros((HEIGHT, WIDTH), np.float32)
    cv2.ellipse(mask, (640, 260), (90, 115), 0, 0, 360, 1, -1)
    cv2.rectangle(mask, (470, 360), (810, 720), 1, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 3)
    frame = background.copy()
    frame[mask > 0.5] = (70, 110, 190)
    return Scene(frame, background, mask)


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("effect-previews")
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = synthetic_scene()
    for effect in create_effects().values():
        tiles = []
        for direction, total in ((Direction.OUT, effect.out_seconds),
                                 (Direction.IN, effect.in_seconds)):
            effect.begin(scene, direction)
            times = np.linspace(0, total, 24)
            start = time.perf_counter()
            for i, t in enumerate(times):
                frame = effect.render(scene, direction, float(t))
                if direction is Direction.OUT and i in (3, 8, 13, 18):
                    tiles.append(cv2.resize(frame, (480, 270)))
            per_frame = (time.perf_counter() - start) / len(times) * 1000
            print(f"{effect.id:<11} {direction.value:<3} {per_frame:5.1f} ms/frame")
        start = time.perf_counter()
        for t in np.linspace(0, 1, 24):
            hidden = effect.render_hidden(scene, float(t))
        per_frame = (time.perf_counter() - start) / 24 * 1000
        print(f"{effect.id:<11} on  {per_frame:5.1f} ms/frame")
        tiles.append(cv2.resize(hidden, (480, 270)))
        cv2.imwrite(str(out_dir / f"{effect.id}.jpg"), np.hstack(tiles))
    on_stage = scene.frame.copy()
    for reaction in create_reactions().values():
        reaction.begin(on_stage.shape[:2], None)
        times = np.linspace(0, reaction.seconds, 30)
        tiles = []
        start = time.perf_counter()
        for i, t in enumerate(times):
            frame = reaction.render(on_stage, scene.mask, True, float(t))
            if i in (2, 6, 11, 18, 24):
                tiles.append(cv2.resize(frame, (480, 270)))
        per_frame = (time.perf_counter() - start) / len(times) * 1000
        print(f"{reaction.id:<11} --- {per_frame:5.1f} ms/frame")
        cv2.imwrite(str(out_dir / f"{reaction.id}.jpg"), np.hstack(tiles))


if __name__ == "__main__":
    main()
