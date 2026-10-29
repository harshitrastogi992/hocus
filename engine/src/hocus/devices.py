from __future__ import annotations

import platform

import cv2
import numpy as np

SYSTEM = platform.system()


def open_camera(index: int, width: int, height: int, fps: int) -> cv2.VideoCapture | None:
    backend = {"Darwin": cv2.CAP_AVFOUNDATION, "Windows": cv2.CAP_DSHOW}.get(SYSTEM, cv2.CAP_ANY)
    capture = cv2.VideoCapture(index, backend)
    if not capture.isOpened():
        capture.release()
        return None
    if SYSTEM == "Windows":
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_FPS, fps)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


class VirtualCamera:
    """Sends frames to the OBS Virtual Camera so meeting apps can pick up the output."""

    def __init__(self) -> None:
        self._camera = None
        self.device: str | None = None
        self.error: str | None = None

    @property
    def active(self) -> bool:
        return self._camera is not None

    def open(self, width: int, height: int, fps: int) -> None:
        self.close()
        try:
            import pyvirtualcam

            self._camera = pyvirtualcam.Camera(
                width=width, height=height, fps=fps, fmt=pyvirtualcam.PixelFormat.BGR,
                backend="obs" if SYSTEM == "Darwin" else None)
            self.device, self.error = self._camera.device, None
        except (ImportError, RuntimeError, OSError, ValueError) as error:
            self._camera = None
            self.error = (
                "OBS Virtual Camera not available. Install OBS Studio 30 or later, start it "
                "once and click 'Start Virtual Camera', then stop it and quit OBS. "
                f"Details: {error}")

    def send(self, frame: np.ndarray) -> None:
        if self._camera is None:
            return
        if (frame.shape[1], frame.shape[0]) != (self._camera.width, self._camera.height):
            frame = cv2.resize(frame, (self._camera.width, self._camera.height))
        self._camera.send(frame)

    def close(self) -> None:
        if self._camera is not None:
            self._camera.close()
        self._camera, self.device = None, None
