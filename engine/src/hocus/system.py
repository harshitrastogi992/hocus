"""Start-up checks shown to the user before the main window."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

SYSTEM = platform.system()
OBS_DOWNLOAD = "https://obsproject.com/download"
MAC_CAMERA_SETTINGS = "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"
WINDOWS_CAMERA_SETTINGS = "ms-settings:privacy-webcam"
OBS_MAC_EXTENSION = "com.obsproject.obs-studio.mac-camera-extension"
OBS_WINDOWS_CLSID = r"CLSID\{A3FCE0F5-3493-419F-958A-ABA1250EC20B}"


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    state: str          # "ok", "warn" or "fail"
    detail: str
    required: bool = True
    action_label: str | None = None
    action_url: str | None = None


def camera_settings_url() -> str | None:
    return {"Darwin": MAC_CAMERA_SETTINGS, "Windows": WINDOWS_CAMERA_SETTINGS}.get(SYSTEM)


def check_os() -> Check:
    if SYSTEM == "Darwin":
        version = platform.mac_ver()[0] or "0"
        major = int(version.split(".")[0])
        ok = major >= 12
        return Check("os", "System", "ok" if ok else "fail",
                     f"macOS {version} on {platform.machine()}" if ok
                     else f"macOS {version} is too old. Hocus needs macOS 12 or later.")
    if SYSTEM == "Windows":
        release = platform.release()
        ok = release in ("10", "11") and platform.machine().endswith("64")
        return Check("os", "System", "ok" if ok else "fail",
                     f"Windows {release} ({platform.machine()})" if ok
                     else "Hocus needs 64-bit Windows 10 or 11.")
    return Check("os", "System", "warn", f"{SYSTEM} is not officially supported yet.")


def _obs_mac() -> tuple[bool, bool]:
    installed = Path("/Applications/OBS.app").exists()
    try:
        listing = subprocess.run(["systemextensionsctl", "list"], capture_output=True,
                                 text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return installed, False
    active = any(OBS_MAC_EXTENSION in line and "[activated enabled]" in line
                 for line in listing.splitlines())
    return installed or active, active


def _obs_windows() -> tuple[bool, bool]:
    try:
        import winreg

        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, OBS_WINDOWS_CLSID))
        return True, True
    except OSError:
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        return (program_files / "obs-studio").exists(), False


def check_obs() -> Check:
    installed, driver = {"Darwin": _obs_mac, "Windows": _obs_windows}.get(
        SYSTEM, lambda: (False, False))()
    label = "OBS Virtual Camera"
    if driver:
        return Check("obs", label, "ok", "Ready. Meeting apps can receive Hocus video.",
                     required=False)
    if installed:
        return Check("obs", label, "warn",
                     "OBS is installed but its virtual camera is not set up. Open OBS, click "
                     "Start Virtual Camera once, allow the system extension if asked, then quit "
                     "OBS.", required=False)
    return Check("obs", label, "warn",
                 "Not installed. Needed only to send Hocus video to Teams, Zoom or Meet.",
                 required=False, action_label="Get OBS Studio", action_url=OBS_DOWNLOAD)


def run_checks() -> dict:
    return {
        "items": [asdict(check) for check in (check_os(), check_obs())],
        "camera_settings_url": camera_settings_url(),
        "can_install_obs": obs_installer() is not None,
        "platform": SYSTEM,
    }


def obs_installer() -> list[str] | None:
    """Command that installs OBS Studio silently, or None if no package manager is found."""
    if SYSTEM == "Darwin":
        brew = next((p for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew")
                     if Path(p).exists()), None)
        return [brew, "install", "--cask", "obs"] if brew else None
    if SYSTEM == "Windows":
        return ["winget", "install", "--id", "OBSProject.OBSStudio", "-e", "--silent",
                "--accept-package-agreements", "--accept-source-agreements"]
    return None


def install_obs() -> tuple[bool, str]:
    command = obs_installer()
    if command is None:
        return False, "No package manager found. Download OBS Studio from obsproject.com."
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"The OBS installer could not run: {error}"
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        return False, "OBS install failed. " + " ".join(tail)
    return True, "OBS Studio installed."


def open_obs() -> tuple[bool, str]:
    try:
        if SYSTEM == "Darwin":
            subprocess.Popen(["open", "-a", "OBS"])
        elif SYSTEM == "Windows":
            program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            obs_dir = program_files / "obs-studio" / "bin" / "64bit"
            subprocess.Popen([str(obs_dir / "obs64.exe")], cwd=obs_dir)
        else:
            return False, "Open OBS Studio from your applications menu."
    except OSError as error:
        return False, f"OBS could not be opened: {error}"
    return True, "OBS is opening."
