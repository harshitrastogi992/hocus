from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from . import models
from .matting import refine
from .observation import Observation, face_from_landmarks, hand_from_landmarks

HAND_INPUT_WIDTH = 640
MASK_SMOOTHING = 0.6


class Vision:
    """Owns the MediaPipe tasks. All calls must come from one thread."""

    def __init__(self) -> None:
        base = mp_python.BaseOptions
        mode = vision.RunningMode.VIDEO
        self._segmenter = vision.ImageSegmenter.create_from_options(
            vision.ImageSegmenterOptions(
                base_options=base(model_asset_path=str(models.ensure_model(models.SEGMENTER))),
                running_mode=mode, output_confidence_masks=True, output_category_mask=False,
            ))
        self._hands = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=base(model_asset_path=str(models.ensure_model(models.HANDS))),
                running_mode=mode, num_hands=2,
                min_hand_detection_confidence=0.5, min_tracking_confidence=0.5,
            ))
        self._face_options = vision.FaceLandmarkerOptions(
            base_options=base(model_asset_path=str(models.ensure_model(models.FACE))),
            running_mode=mode, num_faces=1,
        )
        self._face: vision.FaceLandmarker | None = None
        self._last_ts = {"segment": -1, "hands": -1, "face": -1}
        self._mask: np.ndarray | None = None

    def _timestamp(self, task: str, timestamp_ms: int) -> int:
        stamp = max(timestamp_ms, self._last_ts[task] + 1)
        self._last_ts[task] = stamp
        return stamp

    def segment(self, frame_bgr: np.ndarray, timestamp_ms: int,
                smooth: bool = True) -> np.ndarray:
        """Person matte in [0, 1]. The raw model output is smoothed over time to reduce
        edge flicker, then refined against the frame's own edges."""
        image = mp.Image(image_format=mp.ImageFormat.SRGB,
                         data=cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        result = self._segmenter.segment_for_video(image, self._timestamp("segment", timestamp_ms))
        mask = result.confidence_masks[0].numpy_view().astype(np.float32)
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        height, width = frame_bgr.shape[:2]
        if mask.shape != (height, width):
            mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_LINEAR)
        if smooth:
            if self._mask is not None and self._mask.shape == mask.shape:
                mask = cv2.addWeighted(mask, MASK_SMOOTHING, self._mask, 1 - MASK_SMOOTHING, 0)
            self._mask = mask
        return refine(frame_bgr, np.clip(mask, 0.0, 1.0))

    def observe(self, frame_bgr: np.ndarray, timestamp_ms: int, with_face: bool) -> Observation:
        height, width = frame_bgr.shape[:2]
        scale = min(1.0, HAND_INPUT_WIDTH / width)
        small = cv2.resize(frame_bgr, None, fx=scale, fy=scale) if scale < 1.0 else frame_bgr
        image = mp.Image(image_format=mp.ImageFormat.SRGB,
                         data=cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        hand_result = self._hands.detect_for_video(image, self._timestamp("hands", timestamp_ms))
        hands = [hand for landmarks in hand_result.hand_landmarks
                 if (hand := hand_from_landmarks(landmarks, width, height)) is not None]
        face = None
        if with_face:
            if self._face is None:
                self._face = vision.FaceLandmarker.create_from_options(self._face_options)
            face_result = self._face.detect_for_video(image, self._timestamp("face", timestamp_ms))
            if face_result.face_landmarks:
                face = face_from_landmarks(face_result.face_landmarks[0], width, height)
        return Observation(hands, face)

    def close(self) -> None:
        for task in (self._segmenter, self._hands, self._face):
            if task is not None:
                task.close()
