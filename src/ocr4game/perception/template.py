"""OpenCV 模板匹配。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from ocr4game.perception.roi import crop_roi, roi_offset


@dataclass
class MatchResult:
    found: bool
    confidence: float
    center: tuple[int, int]  # 全图坐标
    top_left: tuple[int, int]


MatchMode = Literal["color", "gray", "edges"]


class TemplateMatcher:
    def match(
        self,
        frame: np.ndarray,
        template_path: Path,
        *,
        threshold: float = 0.85,
        roi: list[float] | None = None,
        scales: list[float] | None = None,
        match_mode: MatchMode = "gray",
    ) -> MatchResult:
        if not template_path.exists():
            return MatchResult(False, 0.0, (0, 0), (0, 0))

        template = cv2.imread(str(template_path))
        if template is None:
            return MatchResult(False, 0.0, (0, 0), (0, 0))

        ox, oy = 0, 0
        search = frame
        if roi:
            search = crop_roi(frame, roi)
            ox, oy = roi_offset(roi, frame.shape[:2])

        search_prepared = _prepare_image(search, match_mode)
        template_prepared = _prepare_image(template, match_mode)
        best = MatchResult(False, 0.0, (0, 0), (0, 0))

        for scale in _normalized_scales(scales):
            candidate = _resize_template(template_prepared, scale)
            th, tw = candidate.shape[:2]
            sh, sw = search_prepared.shape[:2]
            if th > sh or tw > sw:
                continue

            res = cv2.matchTemplate(search_prepared, candidate, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            confidence = float(max_val)
            if confidence <= best.confidence:
                continue

            x, y = max_loc
            best = MatchResult(
                confidence >= threshold,
                confidence,
                (ox + x + tw // 2, oy + y + th // 2),
                (ox + x, oy + y),
            )

        return best

    def confidence(
        self,
        frame: np.ndarray,
        template_path: Path,
        *,
        roi: list[float] | None = None,
        scales: list[float] | None = None,
        match_mode: MatchMode = "gray",
    ) -> MatchResult:
        """返回匹配结果，不因 threshold 过滤（threshold=0）。"""
        return self.match(
            frame,
            template_path,
            threshold=0.0,
            roi=roi,
            scales=scales,
            match_mode=match_mode,
        )


def _normalized_scales(scales: list[float] | None) -> list[float]:
    values = scales or [1.0]
    normalized = sorted(
        {float(scale) for scale in values if scale > 0},
        key=lambda x: abs(1.0 - x),
    )
    return normalized or [1.0]


def _resize_template(template: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return template
    h, w = template.shape[:2]
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    return cv2.resize(template, size, interpolation=interpolation)


def _prepare_image(image: np.ndarray, match_mode: MatchMode) -> np.ndarray:
    if match_mode == "color":
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if match_mode == "edges":
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        return cv2.Canny(gray, 50, 150)
    return cv2.equalizeHist(gray)
