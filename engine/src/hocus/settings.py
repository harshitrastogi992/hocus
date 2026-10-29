from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .backgrounds import PRESETS
from .effects import EFFECT_TYPES
from .gestures.catalog import GESTURES
from .reactions import REACTION_TYPES

RESOLUTIONS = ((640, 480), (1280, 720), (1920, 1080))
BACKGROUND_MODES = ("room", "preset", "image")
ALL_TYPES = (*EFFECT_TYPES, *REACTION_TYPES)


class SettingsError(ValueError):
    pass


def defaults() -> dict[str, Any]:
    return {
        "camera_index": 0,
        "resolution": [1280, 720],
        "fps": 30,
        "mirror": True,
        "virtual_camera": False,
        "background": {"mode": "room", "preset": next(iter(PRESETS)), "image": None},
        "effects": {effect.id: {"enabled": True, "gesture": effect.default_gesture}
                    for effect in ALL_TYPES},
    }


def merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def gesture_owners(settings: dict[str, Any]) -> dict[str, list[str]]:
    """Enabled effects grouped by the gesture that triggers them."""
    owners: dict[str, list[str]] = {}
    for effect_id, effect in settings["effects"].items():
        if effect["enabled"]:
            owners.setdefault(effect["gesture"], []).append(effect_id)
    return owners


def validate(settings: dict[str, Any]) -> dict[str, Any]:
    known = {effect.id: effect for effect in ALL_TYPES}
    if set(settings.get("effects", {})) - set(known):
        raise SettingsError("Unknown effect in settings")
    for effect in settings["effects"].values():
        if effect.get("gesture") not in GESTURES:
            raise SettingsError(f"Unknown gesture: {effect.get('gesture')}")
        if not isinstance(effect.get("enabled"), bool):
            raise SettingsError("Effect 'enabled' must be true or false")
    for gesture, effect_ids in gesture_owners(settings).items():
        if len(effect_ids) > 1:
            names = " and ".join(known[i].name for i in effect_ids)
            raise SettingsError(
                f"{names} both use {GESTURES[gesture].label}. "
                "Turn one off or give it a different gesture.")
    if tuple(settings["resolution"]) not in RESOLUTIONS:
        raise SettingsError(f"Unsupported resolution: {settings['resolution']}")
    if not isinstance(settings["camera_index"], int) or not 0 <= settings["camera_index"] < 10:
        raise SettingsError("Camera index must be between 0 and 9")
    if settings["fps"] not in (15, 24, 30):
        raise SettingsError("Frame rate must be 15, 24 or 30")
    background = settings["background"]
    if background["mode"] not in BACKGROUND_MODES:
        raise SettingsError(f"Unknown background mode: {background['mode']}")
    if background["preset"] not in PRESETS:
        raise SettingsError(f"Unknown background preset: {background['preset']}")
    if background["mode"] == "image" and not (
            background["image"] and Path(background["image"]).is_file()):
        raise SettingsError("Choose an image file for the background")
    return settings


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.current = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            stored = json.loads(self.path.read_text())
            # Keep known keys only, so settings from an older version still load.
            base = defaults()
            stored["effects"] = {k: v for k, v in stored.get("effects", {}).items()
                                 if k in base["effects"]}
            settings = merge(base, {k: v for k, v in stored.items() if k in base})
            # Effects added since the file was written start off if their default gesture
            # is already taken.
            taken = {e["gesture"] for k, e in stored["effects"].items() if e.get("enabled")}
            for effect_id in set(base["effects"]) - set(stored["effects"]):
                if base["effects"][effect_id]["gesture"] in taken:
                    settings["effects"][effect_id]["enabled"] = False
            return validate(settings)
        except (OSError, ValueError, KeyError, TypeError):
            return defaults()

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        candidate = validate(merge(self.current, patch))
        self.current = candidate
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(candidate, indent=2))
        return candidate
