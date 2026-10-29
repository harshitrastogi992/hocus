"""Freeze the Python engine into the single-file sidecar the desktop app bundles.

Usage (from the repo root, with the engine virtualenv):
    engine/.venv/bin/python scripts/build_engine.py

Writes app/src-tauri/binaries/hocus-engine-<target-triple>[.exe], the name Tauri
expects for `bundle.externalBin`. Vision models are downloaded and bundled so the
packaged app works offline from first launch.
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
OUT = ROOT / "app" / "src-tauri" / "binaries"
WORK = ROOT / "build" / "engine"


def target_triple() -> str:
    output = subprocess.run(["rustc", "-vV"], check=True, capture_output=True, text=True).stdout
    return next(line.split(": ")[1] for line in output.splitlines() if line.startswith("host: "))


def main() -> int:
    sys.path.insert(0, str(ENGINE / "src"))
    from hocus.vision.models import ensure_all

    models = WORK / "models"
    ensure_all(models)

    separator = ";" if platform.system() == "Windows" else ":"
    subprocess.run([
        sys.executable, "-m", "PyInstaller", str(ROOT / "scripts" / "engine_entry.py"),
        "--name", "hocus-engine", "--onefile", "--noconfirm", "--clean",
        "--distpath", str(WORK / "dist"), "--workpath", str(WORK / "work"),
        "--specpath", str(WORK),
        "--collect-data", "mediapipe", "--collect-binaries", "mediapipe",
        "--add-data", f"{models}{separator}models",
        "--paths", str(ENGINE / "src"),
    ], check=True)

    suffix = ".exe" if platform.system() == "Windows" else ""
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"hocus-engine-{target_triple()}{suffix}"
    shutil.copy2(WORK / "dist" / f"hocus-engine{suffix}", target)
    print(f"Sidecar written to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
