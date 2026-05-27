"""感知层统一入口：模板 + OCR。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ocr4game.config import GameProfile, OcrAnchorConfig, TemplateAnchorConfig
from ocr4game.perception.ocr import OcrEngine, OcrHit
from ocr4game.perception.template import MatchResult, TemplateMatcher
from ocr4game.resources import game_assets_dir


@dataclass
class PerceptionResult:
    found: bool
    kind: str  # template | ocr
    confidence: float
    center: tuple[int, int]
    detail: str = ""


class Perception:
    def __init__(self, profile: GameProfile) -> None:
        self._profile = profile
        self._template = TemplateMatcher()
        self._ocr = OcrEngine()

    def evaluate_anchor(self, frame: np.ndarray, anchor_name: str) -> PerceptionResult:
        anchor = self._profile.anchors.get(anchor_name)
        if not anchor:
            return PerceptionResult(False, "unknown", 0.0, (0, 0), f"未定义锚点: {anchor_name}")

        if isinstance(anchor, TemplateAnchorConfig):
            path = game_assets_dir(self._profile) / anchor.image
            m: MatchResult = self._template.match(
                frame, path, threshold=anchor.threshold, roi=anchor.roi
            )
            return PerceptionResult(
                m.found,
                "template",
                m.confidence,
                m.center,
                str(path.name),
            )

        if isinstance(anchor, OcrAnchorConfig):
            hit: OcrHit | None = self._ocr.find_text(
                frame,
                anchor.expect,
                roi=anchor.roi,
                min_confidence=anchor.min_confidence,
            )
            if hit:
                return PerceptionResult(
                    True, "ocr", hit.confidence, hit.center, hit.text
                )
            return PerceptionResult(False, "ocr", 0.0, (0, 0))

        return PerceptionResult(False, "unknown", 0.0, (0, 0), f"未知类型: {anchor.type}")

    def template_visible(self, frame: np.ndarray, anchor_name: str) -> bool:
        return self.evaluate_anchor(frame, anchor_name).found
