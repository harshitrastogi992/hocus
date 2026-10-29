from hocus import system


def test_checks_report_os_and_optional_obs():
    report = system.run_checks()
    ids = [item["id"] for item in report["items"]]
    assert ids == ["os", "obs"]
    obs = report["items"][1]
    assert obs["required"] is False and obs["state"] in ("ok", "warn")


def test_obs_states(monkeypatch):
    for found, state, has_action in (((True, True), "ok", False),
                                     ((True, False), "warn", False),
                                     ((False, False), "warn", True)):
        monkeypatch.setattr(system, "SYSTEM", "Darwin")
        monkeypatch.setattr(system, "_obs_mac", lambda found=found: found)
        check = system.check_obs()
        assert check.state == state
        assert (check.action_url is not None) == has_action


def test_installer_reports_missing_package_manager(monkeypatch):
    monkeypatch.setattr(system, "obs_installer", lambda: None)
    ok, message = system.install_obs()
    assert not ok and "obsproject.com" in message
