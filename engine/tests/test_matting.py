import cv2
import numpy as np

from hocus.vision.matting import drop_stray_blobs, refine


def scene():
    frame = np.full((180, 320, 3), 230, np.uint8)
    frame[40:, 120:200] = 40
    truth = np.zeros((180, 320), np.float32)
    truth[40:, 120:200] = 1.0
    return frame, truth


def test_refinement_snaps_a_blurry_mask_to_the_real_edge():
    frame, truth = scene()
    coarse = cv2.GaussianBlur(truth, (0, 0), 8) * 0.9
    refined = refine(frame, coarse)
    assert np.abs(refined - truth).mean() < np.abs(coarse - truth).mean() * 0.5
    assert refined[100, 160] > 0.95 and refined[100, 40] < 0.05


def test_small_detached_fragments_are_dropped():
    _, truth = scene()
    noisy = truth.copy()
    noisy[10:16, 20:26] = 1.0
    cleaned = drop_stray_blobs(noisy)
    assert cleaned[12, 22] == 0 and cleaned[100, 160] == 1.0
