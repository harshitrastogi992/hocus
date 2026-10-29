# Architecture

Hocus is two processes on the user's machine.

| Process | Language | Job |
|---|---|---|
| Desktop shell (`app/`) | Rust (Tauri 2) + React | Window, UI, starts and stops the engine, file dialogs, opening links |
| Engine (`engine/`) | Python 3.13 | Camera, MediaPipe vision, gestures, effects, virtual camera output |

The UI talks to the engine over a WebSocket on `127.0.0.1`, protected by a random token the shell generates at each launch and passes to the engine through the `HOCUS_TOKEN` environment variable. See [protocol.md](protocol.md).

## Why a Python engine

MediaPipe's hand, face and segmentation models, OpenCV, and `pyvirtualcam` (the OBS Virtual Camera bridge) have no equal in Rust or the browser. Keeping all video work in one Python process also keeps frames out of the UI process: the UI receives a small JPEG preview, while full-resolution frames go straight from the engine to the virtual camera.

In development the shell runs `engine/.venv/bin/python -m hocus serve`. In a release build it runs a single-file PyInstaller binary bundled as a Tauri sidecar (`scripts/build_engine.py`). The engine quits when its stdin closes, so it never outlives the app.

## Frame pipeline

```
camera ──► mirror ──► hands (+ face) every 50 ms ──► gesture catalogue ──► director
                 │                                                            │
                 └──► segmentation ──► matting ──► effect.render(...) ◄───────┘
                                                        │
                                       ┌────────────────┴───────────────┐
                                  virtual camera                  JPEG preview → UI
```

- **Vision** (`vision/detector.py`): MediaPipe tasks in VIDEO mode. Hands are detected at 640 px wide. The face landmarker loads only when a face-based gesture is in use.
- **Matting** (`vision/matting.py`): the square selfie segmenter gives a coarse person map. It is smoothed over time, firmed up, snapped to real edges with a fast guided filter, and stripped of detached fragments (chair edges, objects). About 6 ms at 720p.
- **Gestures** (`gestures/`): `shapes.py` has scale-invariant hand-shape tests. `catalog.py` lists the gestures, their hold times and priorities. `hold.py` counts how long a gesture is held and requires a release before it can count again.
- **Director** (`director.py`): the state machine `present → leaving → hidden → returning → present`. You return with the gesture you left with.
- **Effects** (`effects/`): each effect renders its own `out` and `in` transitions and what is shown while hidden.
- **Backgrounds**: a captured empty room (median of 1.5 s of frames, rejected if a person is visible), a built-in backdrop generated in code, or a user image.

## Settings

`settings.py` validates every change before it is saved to the user config folder (`~/Library/Application Support/Hocus/settings.json` on macOS, `%LOCALAPPDATA%\Hocus\settings.json` on Windows). The rule that two enabled effects cannot share a gesture is enforced here, and the UI mirrors it so clashing choices are greyed out.

## Start-up checks

On connect the engine sends a `checks` report: OS version and whether the OBS Virtual Camera driver is installed and active (`systemextensionsctl` on macOS, the DirectShow CLSID in the registry on Windows). The engine status also reports its start-up stage (models, camera, running). The UI shows these on the start-up screen and offers fixes: open camera privacy settings, install OBS with Homebrew or winget, or open OBS to activate its driver.
