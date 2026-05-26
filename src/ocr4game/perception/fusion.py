"""感知层统一入口：模板 + OCR。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ocr4game.config import GameProfile
from ocr4game.perception.ocr import OcrEngine, OcrHit
from ocr4game.perception.template import MatchResult, TemplateMatcher


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

        kind = anchor.get("type", "template")
        roi = anchor.get("roi")

        if kind == "template":
            image = anchor.get("image", "")
            path = self._profile.assets_dir() / image
            threshold = float(anchor.get("threshold", 0.85))
            m: MatchResult = self._template.match(
                frame, path, threshold=threshold, roi=roi
            )
            return PerceptionResult(
                m.found,
                "template",
                m.confidence,
                m.center,
                str(path.name),
            )

        if kind == "ocr":
            expect = anchor.get("expect", [])
            min_conf = float(anchor.get("min_confidence", 0.5))
            hit: OcrHit | None = self._ocr.find_text(
                frame, expect, roi=roi, min_confidence=min_conf
            )
            if hit:
                return PerceptionResult(
                    True, "ocr", hit.confidence, hit.center, hit.text
                )
            return PerceptionResult(False, "ocr", 0.0, (0, 0))

        return PerceptionResult(False, "unknown", 0.0, (0, 0), f"未知类型: {kind}")

    def template_visible(self, frame: np.ndarray, anchor_name: str) -> bool:
        return self.evaluate_anchor(frame, anchor_name).found
