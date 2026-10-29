"""Turns a coarse person probability map into a clean, edge-aware matte."""

from __future__ import annotations

import cv2
import numpy as np

GUIDE_SCALE = 4
GUIDE_RADIUS = 12
GUIDE_EPS = 2e-3
MIN_BLOB_SHARE = 0.04


def smoothstep(values: np.ndarray, low: float, high: float) -> np.ndarray:
    x = np.clip((values - low) / (high - low), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def guided_filter(guide_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fast guided filter (He et al.): snaps the matte to edges in the camera image.

    Runs at 1/GUIDE_SCALE resolution and upsamples the linear coefficients, which keeps
    edge detail while costing a few milliseconds at 720p.
    """
    height, width = mask.shape
    guide = cv2.cvtColor(guide_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    size = (max(1, width // GUIDE_SCALE), max(1, height // GUIDE_SCALE))
    small_guide = cv2.resize(guide, size, interpolation=cv2.INTER_AREA)
    small_mask = cv2.resize(mask, size, interpolation=cv2.INTER_AREA)
    radius = max(1, GUIDE_RADIUS // GUIDE_SCALE)

    def box(values: np.ndarray) -> np.ndarray:
        return cv2.boxFilter(values, -1, (2 * radius + 1, 2 * radius + 1))

    mean_guide, mean_mask = box(small_guide), box(small_mask)
    covariance = box(small_guide * small_mask) - mean_guide * mean_mask
    variance = box(small_guide * small_guide) - mean_guide * mean_guide
    a = covariance / (variance + GUIDE_EPS)
    b = mean_mask - a * mean_guide
    a = cv2.resize(box(a), (width, height), interpolation=cv2.INTER_LINEAR)
    b = cv2.resize(box(b), (width, height), interpolation=cv2.INTER_LINEAR)
    return np.clip(a * guide + b, 0.0, 1.0)


def drop_stray_blobs(mask: np.ndarray) -> np.ndarray:
    """Remove detached fragments much smaller than the main person, such as chair edges."""
    height, width = mask.shape
    size = (max(1, width // 4), max(1, height // 4))
    small = cv2.resize(mask, size, interpolation=cv2.INTER_AREA)
    count, labels, stats, _ = cv2.connectedComponentsWithStats((small > 0.5).astype(np.uint8))
    if count <= 2:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    keep = np.zeros(count, dtype=np.float32)
    keep[1:] = areas >= areas.max() * MIN_BLOB_SHARE
    keep_mask = cv2.resize(keep[labels], (width, height), interpolation=cv2.INTER_LINEAR)
    keep_mask = cv2.dilate(keep_mask, np.ones((9, 9), np.uint8))
    return mask * keep_mask


def refine(frame_bgr: np.ndarray, coarse: np.ndarray) -> np.ndarray:
    """Coarse model output -> matte with firm interior, clean background and soft true edges."""
    firm = smoothstep(coarse, 0.2, 0.8)
    snapped = guided_filter(frame_bgr, firm)
    return drop_stray_blobs(smoothstep(snapped, 0.3, 0.7)).astype(np.float32)
