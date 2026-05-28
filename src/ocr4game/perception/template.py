"""OpenCV 模板匹配。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ocr4game.perception.roi import crop_roi, roi_offset


@dataclass
class MatchResult:
    found: bool
    confidence: float
    center: tuple[int, int]  # 全图坐标
    top_left: tuple[int, int]


class TemplateMatcher:
    def match(
        self,
        frame: np.ndarray,
        template_path: Path,
        *,
        threshold: float = 0.85,
        roi: list[float] | None = None,
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

        th, tw = template.shape[:2]
        sh, sw = search.shape[:2]
        if th > sh or tw > sw:
            return MatchResult(False, 0.0, (0, 0), (0, 0))

        res = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        confidence = float(max_val)
        found = confidence >= threshold

        x, y = max_loc
        center = (ox + x + tw // 2, oy + y + th // 2)
        top_left = (ox + x, oy + y)
        return MatchResult(found, confidence, center, top_left)

    def confidence(
        self,
        frame: np.ndarray,
        template_path: Path,
        *,
        roi: list[float] | None = None,
    ) -> MatchResult:
        """返回匹配结果，不因 threshold 过滤（threshold=0）。"""
        return self.match(frame, template_path, threshold=0.0, roi=roi)
