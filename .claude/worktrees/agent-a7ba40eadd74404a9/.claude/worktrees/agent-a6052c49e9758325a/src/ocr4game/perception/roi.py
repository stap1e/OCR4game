"""相对 ROI（0~1）与绝对像素区域。"""

from __future__ import annotations

import numpy as np


def relative_roi_to_pixels(
    frame: np.ndarray,
    roi: list[float],
) -> tuple[int, int, int, int]:
    """roi: [x0, y0, x1, y1] 相对全图比例。"""
    h, w = frame.shape[:2]
    x0 = int(roi[0] * w)
    y0 = int(roi[1] * h)
    x1 = int(roi[2] * w)
    y1 = int(roi[3] * h)
    x0 = max(0, min(x0, w - 1))
    y0 = max(0, min(y0, h - 1))
    x1 = max(x0 + 1, min(x1, w))
    y1 = max(y0 + 1, min(y1, h))
    return x0, y0, x1, y1


def crop_roi(frame: np.ndarray, roi: list[float]) -> np.ndarray:
    x0, y0, x1, y1 = relative_roi_to_pixels(frame, roi)
    return frame[y0:y1, x0:x1].copy()


def roi_offset(roi: list[float], frame_shape: tuple[int, int]) -> tuple[int, int]:
    h, w = frame_shape
    return int(roi[0] * w), int(roi[1] * h)
