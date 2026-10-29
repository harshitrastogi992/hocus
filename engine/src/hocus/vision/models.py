from __future__ import annotations

import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..paths import models_dir

_BASE = "https://storage.googleapis.com/mediapipe-models"


@dataclass(frozen=True)
class ModelSpec:
    filename: str
    url: str


# The square model separates people from furniture better than the landscape variant,
# which tends to include office chairs.
SEGMENTER = ModelSpec(
    "selfie_segmenter.tflite",
    f"{_BASE}/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite",
)
HANDS = ModelSpec(
    "hand_landmarker.task",
    f"{_BASE}/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
)
FACE = ModelSpec(
    "face_landmarker.task",
    f"{_BASE}/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
)
ALL_MODELS = (SEGMENTER, HANDS, FACE)


def ensure_model(spec: ModelSpec, directory: Path | None = None) -> Path:
    directory = directory or models_dir()
    target = directory / spec.filename
    if target.is_file() and target.stat().st_size > 0:
        return target
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, delete=False, suffix=".part") as partial:
        with urllib.request.urlopen(spec.url, timeout=60) as response:
            shutil.copyfileobj(response, partial)
    Path(partial.name).replace(target)
    return target


def ensure_all(directory: Path | None = None) -> dict[str, Path]:
    return {spec.filename: ensure_model(spec, directory) for spec in ALL_MODELS}
