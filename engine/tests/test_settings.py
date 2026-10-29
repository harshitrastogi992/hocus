import json

import pytest

from hocus.settings import SettingsError, SettingsStore, defaults, gesture_owners, merge, validate


def test_defaults_are_valid_and_conflict_free():
    settings = validate(defaults())
    assert all(len(ids) == 1 for ids in gesture_owners(settings).values())


def test_two_enabled_effects_cannot_share_a_gesture():
    settings = merge(defaults(), {"effects": {"blink": {"gesture": "v_sign"}}})
    with pytest.raises(SettingsError, match="Stardust and Blink both use V sign"):
        validate(settings)
    settings["effects"]["stardust"]["enabled"] = False
    validate(settings)


def test_image_background_needs_an_existing_file(tmp_path):
    settings = merge(defaults(), {"background": {"mode": "image", "image": str(tmp_path / "x")}})
    with pytest.raises(SettingsError):
        validate(settings)


def test_store_persists_and_rejects_invalid_updates(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.update({"mirror": False})
    assert json.loads(path.read_text())["mirror"] is False
    with pytest.raises(SettingsError):
        store.update({"fps": 61})
    assert store.current["fps"] == 30
    assert SettingsStore(path).current["mirror"] is False


def test_store_survives_a_corrupt_or_outdated_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json")
    assert SettingsStore(path).current == defaults()
    path.write_text(json.dumps({"mirror": False, "effects": {"retired": {}}, "old_key": 1}))
    current = SettingsStore(path).current
    assert current["mirror"] is False and "retired" not in current["effects"]


def test_new_effects_start_off_if_their_gesture_is_taken(tmp_path):
    path = tmp_path / "settings.json"
    old = {"effects": {"blink": {"enabled": True, "gesture": "thumbs_up"}}}
    path.write_text(json.dumps(old))
    current = SettingsStore(path).current
    assert current["effects"]["blink"]["gesture"] == "thumbs_up"
    assert current["effects"]["confetti"]["enabled"] is False
    assert current["effects"]["hearts"]["enabled"] is True
