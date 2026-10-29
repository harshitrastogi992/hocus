from __future__ import annotations

import cv2
import numpy as np


def composite(foreground: np.ndarray, background: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    alpha = np.ascontiguousarray(alpha, dtype=np.float32)
    if foreground.dtype != np.uint8:
        foreground = np.clip(foreground, 0, 255).astype(np.uint8)
    foreground = np.ascontiguousarray(foreground)
    return cv2.blendLinear(foreground, np.ascontiguousarray(background), alpha, 1.0 - alpha)


def blend_into(destination: np.ndarray, source: np.ndarray, alpha: np.ndarray) -> None:
    destination[:] = composite(source, destination, alpha)


def add_glow(destination: np.ndarray, colour_layer: np.ndarray, strength: np.ndarray) -> None:
    """Additive light: brightens without darkening anything."""
    lit = destination.astype(np.float32) + colour_layer.astype(np.float32) * strength[:, :, None]
    destination[:] = np.clip(lit, 0, 255).astype(np.uint8)


def person_box(mask: np.ndarray, threshold: float = 0.4,
               pad: int = 0) -> tuple[int, int, int, int] | None:
    """Bounding box (left, top, right, bottom) of the largest person blob."""
    binary = (mask > threshold).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary)
    if count <= 1:
        return None
    x, y, w, h, _ = stats[1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))]
    height, width = mask.shape
    return max(0, x - pad), max(0, y - pad), min(width, x + w + pad), min(height, y + h + pad)


def person_coverage(mask: np.ndarray, threshold: float = 0.5) -> float:
    """Share of the frame covered by the largest person blob."""
    binary = (mask > threshold).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary)
    if count <= 1:
        return 0.0
    return float(stats[1:, cv2.CC_STAT_AREA].max()) / mask.size


def cover_fit(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """Scale to fill width x height, cropping the overflow around the centre."""
    scale = max(width / image.shape[1], height / image.shape[0])
    resized = cv2.resize(image, (max(width, round(image.shape[1] * scale)),
                                 max(height, round(image.shape[0] * scale))),
                         interpolation=cv2.INTER_AREA)
    top = (resized.shape[0] - height) // 2
    left = (resized.shape[1] - width) // 2
    return resized[top:top + height, left:left + width].copy()
