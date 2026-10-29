from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

from . import backgrounds
from .compositing import composite, person_coverage
from .devices import VirtualCamera, open_camera
from .director import Director, Phase
from .effects import Direction, Scene, create_effects
from .gestures import catalog
from .reactions import create_reactions
from .settings import SettingsStore

log = logging.getLogger(__name__)

PREVIEW_WIDTH = 960
PREVIEW_QUALITY = 78
DETECT_INTERVAL = 1 / 20
STATUS_INTERVAL = 1 / 8
PLATE_COUNTDOWN = 3.0
PLATE_SAMPLE_SECONDS = 1.5
PLATE_PERSON_LIMIT = 0.03

Emit = Callable[[dict[str, Any]], None]
Publish = Callable[[bytes], None]


class Engine:
    """Camera -> vision -> director -> effects -> preview and virtual camera.

    Runs on its own thread. Other threads interact only through ``submit`` and
    ``status``.
    """

    def __init__(self, store: SettingsStore, emit: Emit, publish: Publish,
                 vision_factory: Callable[[], Any] | None = None,
                 camera_factory: Callable[..., Any] = open_camera) -> None:
        self.store = store
        self.emit = emit
        self.publish = publish
        self.effects = create_effects()
        self.reactions = create_reactions()
        self.director = Director(self.effects)
        self.virtual = VirtualCamera()
        self._vision_factory = vision_factory
        self._camera_factory = camera_factory
        self._commands: queue.Queue[Callable[[], None]] = queue.Queue()
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._status: dict[str, Any] = {}
        self._capture: cv2.VideoCapture | None = None
        self._camera_error: str | None = None
        self._plate: np.ndarray | None = None
        self._plate_job: dict[str, Any] | None = None
        self._detected: set[str] = set()
        self._observation = None
        self._playing: dict[str, float] = {}
        self._cued: list[str] = []
        self._last_detect = 0.0
        self._mask: np.ndarray | None = None
        self._fps = 0.0
        self._stage = "loading_models"
        self._apply(store.current, initial=True)

    # Public, thread-safe API -------------------------------------------------

    def start(self) -> None:
        self._running.set()
        self._thread = threading.Thread(target=self._run, name="hocus-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def submit(self, command: Callable[[], None]) -> None:
        self._commands.put(command)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def update_settings(self, patch: dict[str, Any]) -> None:
        settings = self.store.update(patch)
        self.submit(lambda: self._apply(settings))

    def capture_plate(self) -> None:
        self.submit(self._start_plate)

    def toggle(self, effect_id: str | None) -> None:
        if effect_id in self.reactions:
            self.submit(lambda: self._cued.append(effect_id))
        else:
            self.submit(lambda: self.director.request(effect_id))

    # Engine thread -----------------------------------------------------------

    def _apply(self, settings: dict[str, Any], initial: bool = False) -> None:
        self.settings = settings
        self.director.bind({effect["gesture"]: effect_id
                            for effect_id, effect in settings["effects"].items()
                            if effect["enabled"]})
        director = self.director
        if director.effect_id and director.effect_id not in director.bindings.values():
            director.reset()
        if initial:
            return
        camera_key = (settings["camera_index"], tuple(settings["resolution"]), settings["fps"])
        if camera_key != getattr(self, "_camera_key", None):
            self._open_camera()
        if settings["virtual_camera"] != self.virtual.active or (
                self.virtual.active and camera_key != self._virtual_key):
            self._open_virtual()

    def _open_camera(self) -> None:
        if self._capture is not None:
            self._capture.release()
        s = self.settings
        self._camera_key = (s["camera_index"], tuple(s["resolution"]), s["fps"])
        self._camera_attempt = time.perf_counter()
        self._capture = self._camera_factory(s["camera_index"], *s["resolution"], s["fps"])
        self._camera_error = None if self._capture else (
            f"Camera {s['camera_index']} could not be opened. Check that no other app is "
            "using it and that Hocus has camera permission.")
        self._plate = None
        self._mask = None

    def _open_virtual(self) -> None:
        s = self.settings
        self._virtual_key = (s["camera_index"], tuple(s["resolution"]), s["fps"])
        if s["virtual_camera"]:
            self.virtual.open(*s["resolution"], s["fps"])
            if self.virtual.error:
                self.emit({"type": "notice", "level": "error", "message": self.virtual.error})
        else:
            self.virtual.close()
            self.virtual.error = None

    def _start_plate(self) -> None:
        self._plate_job = {"started": time.perf_counter(), "frames": []}

    def _run(self) -> None:
        self._publish_status()
        try:
            self.vision = (self._vision_factory or _default_vision)()
        except Exception as error:  # noqa: BLE001 - surfaced to the UI, then the thread ends
            log.exception("Vision models failed to load")
            self._stage = "failed"
            self._publish_status()
            self.emit({"type": "notice", "level": "error",
                       "message": f"Vision models failed to load: {error}"})
            return
        self._stage = "opening_camera"
        self._publish_status()
        self._open_camera()
        self._stage = "running"
        self._open_virtual()
        last_status = 0.0
        frame_times: list[float] = []
        try:
            while self._running.is_set():
                while not self._commands.empty():
                    self._commands.get_nowait()()
                frame = self._read()
                if frame is None:
                    self._publish_status(force=time.perf_counter() - last_status > 1.0)
                    last_status = time.perf_counter()
                    time.sleep(0.5)
                    continue
                output = self._process(frame, time.perf_counter())
                self.virtual.send(output)
                self._publish_preview(output)
                now = time.perf_counter()
                frame_times = [t for t in frame_times if now - t < 1.0] + [now]
                self._fps = len(frame_times)
                if now - last_status >= STATUS_INTERVAL:
                    self._publish_status()
                    last_status = now
        finally:
            if self._capture is not None:
                self._capture.release()
            self.virtual.close()
            self.vision.close()

    def _read(self) -> np.ndarray | None:
        if self._capture is None:
            if time.perf_counter() - self._camera_attempt > 3.0:
                self._open_camera()
            return None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._camera_error = "The camera stopped sending frames."
            return None
        self._camera_error = None
        return cv2.flip(frame, 1) if self.settings["mirror"] else frame

    def _background(self, frame: np.ndarray) -> np.ndarray | None:
        height, width = frame.shape[:2]
        background = self.settings["background"]
        if background["mode"] == "preset":
            return backgrounds.preset(background["preset"], width, height)
        if background["mode"] == "image":
            return backgrounds.image_file(background["image"], width, height)
        if self._plate is not None and self._plate.shape == frame.shape:
            return self._plate
        return None

    def _process(self, frame: np.ndarray, now: float) -> np.ndarray:
        timestamp = int(now * 1000)
        if self._plate_job is not None:
            return self._collect_plate(frame, now, timestamp)

        background = self._background(frame)
        director = self.director
        watching = director.watching(with_background=background is not None)
        if watching and now - self._last_detect >= DETECT_INTERVAL:
            self._last_detect = now
            with_face = any(catalog.GESTURES[g].needs_face for g in watching)
            self._observation = self.vision.observe(frame, timestamp, with_face)
            self._detected = catalog.detect(self._observation, watching)
        elif not watching:
            self._detected = set()
        transition = director.update(self._detected, now)
        if transition is not None:
            effect = self.effects[transition.effect]
            self.emit({"type": "effect", "effect": effect.id,
                       "direction": transition.direction.value})
        for reaction_id in [*director.cues, *self._cued]:
            if reaction_id in director.bindings.values():
                self.reactions[reaction_id].begin(frame.shape[:2], self._observation)
                self._playing[reaction_id] = now
                self.emit({"type": "effect", "effect": reaction_id, "direction": "out"})
        self._cued.clear()
        self._playing = {r: start for r, start in self._playing.items()
                         if now - start < self.reactions[r].seconds}

        needs_mask = bool(self._playing) or background is not None and (
            director.phase is not Phase.PRESENT or self.settings["background"]["mode"] != "room")
        if not needs_mask:
            return frame
        mask = self.vision.segment(frame, timestamp)
        output = self._stage_frame(frame, background, mask, transition, now)
        effect = director.effect
        person_visible = director.phase is Phase.PRESENT or (
            director.phase is Phase.HIDDEN and effect is not None and effect.kind == "toggle")
        for reaction_id, start in self._playing.items():
            output = self.reactions[reaction_id].render(output, mask, person_visible, now - start)
        return output

    def _stage_frame(self, frame: np.ndarray, background: np.ndarray | None, mask: np.ndarray,
                     transition, now: float) -> np.ndarray:
        if background is None:
            return frame
        director = self.director
        scene = Scene(frame, background, mask)
        effect = director.effect
        age = now - director.started
        if director.phase is Phase.PRESENT or effect is None:
            if self.settings["background"]["mode"] == "room":
                return frame
            return composite(frame, background, mask)
        if transition is not None:
            effect.begin(scene, transition.direction)
        if director.phase is Phase.LEAVING:
            return effect.render(scene, Direction.OUT, age)
        if director.phase is Phase.RETURNING:
            return effect.render(scene, Direction.IN, age)
        return effect.render_hidden(scene, age)

    def _collect_plate(self, frame: np.ndarray, now: float, timestamp: int) -> np.ndarray:
        job = self._plate_job
        elapsed = now - job["started"]
        if elapsed >= PLATE_COUNTDOWN:
            job["frames"].append(frame.copy())
        if elapsed < PLATE_COUNTDOWN + PLATE_SAMPLE_SECONDS:
            return frame
        self._plate_job = None
        plate = np.median(np.stack(job["frames"][-24:]), axis=0).astype(np.uint8)
        coverage = person_coverage(self.vision.segment(plate, timestamp, smooth=False))
        if coverage > PLATE_PERSON_LIMIT:
            self.emit({"type": "notice", "level": "error",
                       "message": "Someone was still in frame. Step fully out of view and "
                                  "capture the room again."})
            return frame
        self._plate = plate
        self.director.reset()
        self.emit({"type": "notice", "level": "info", "message": "Room captured."})
        return frame

    def _publish_preview(self, frame: np.ndarray) -> None:
        scale = PREVIEW_WIDTH / frame.shape[1]
        small = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) \
            if scale < 1 else frame
        ok, encoded = cv2.imencode(".jpg", small, (cv2.IMWRITE_JPEG_QUALITY, PREVIEW_QUALITY))
        if ok:
            self.publish(encoded.tobytes())

    def _publish_status(self, force: bool = True) -> None:
        director = self.director
        job = self._plate_job
        if job is not None:
            plate = "capturing"
        elif self.settings["background"]["mode"] != "room" or self._plate is not None:
            plate = "ready"
        else:
            plate = "missing"
        status = {
            "stage": self._stage,
            "phase": director.phase.value,
            "effect": director.effect_id,
            "reactions": sorted(self._playing),
            "hold": {"gesture": director.hold[0], "progress": round(director.hold[1], 3)}
            if director.hold else None,
            "background_ready": plate == "ready",
            "plate": plate,
            "plate_countdown": max(0.0, round(PLATE_COUNTDOWN - (time.perf_counter()
                                                                 - job["started"]), 1))
            if job else None,
            "camera": {"ok": self._camera_error is None and self._capture is not None,
                       "error": self._camera_error},
            "virtual_camera": {"active": self.virtual.active, "device": self.virtual.device,
                               "error": self.virtual.error},
            "fps": self._fps,
        }
        with self._lock:
            changed = status != self._status
            self._status = status
        if changed or force:
            self.emit({"type": "status", **status})


def _default_vision():
    from .vision.detector import Vision

    return Vision()
