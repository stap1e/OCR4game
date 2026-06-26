"""感知层统一入口：模板 + OCR。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ocr4game.config import GameProfile, OcrAnchorConfig, TemplateAnchorConfig
from ocr4game.perception.content import AnchorObservation, GameContentSnapshot, TextDetection
from ocr4game.perception.extractor import ContentExtractor
from ocr4game.perception.ocr import OcrEngine, OcrHit
from ocr4game.perception.screen_state import ScreenStateRecognizer
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
        self._screen_state = ScreenStateRecognizer()
        self._content_extractor = ContentExtractor()

    def evaluate_anchor(self, frame: np.ndarray, anchor_name: str) -> PerceptionResult:
        anchor = self._profile.anchors.get(anchor_name)
        if not anchor:
            return PerceptionResult(False, "unknown", 0.0, (0, 0), f"未定义锚点: {anchor_name}")

        if isinstance(anchor, TemplateAnchorConfig):
            path = game_assets_dir(self._profile) / anchor.image
            m: MatchResult = self._template.match(
                frame,
                path,
                threshold=anchor.threshold,
                roi=anchor.roi,
                scales=anchor.scales,
                match_mode=anchor.match_mode,
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

    def read_texts(self, frame: np.ndarray, *, roi: list[float] | None = None) -> list[OcrHit]:
        return self._ocr.read(frame, roi=roi)

    def recognize_screen_state(self, frame: np.ndarray):
        return self._screen_state.recognize(frame, self._profile, self)

    def extract_content(self, frame: np.ndarray, *, screen_state=None) -> tuple[dict[str, object], list[str]]:
        return self._content_extractor.extract(frame, self._profile, self, screen_state=screen_state)

    def snapshot(self, frame: np.ndarray, *, image_path: str | None = None) -> GameContentSnapshot:
        warnings: list[str] = []
        texts: list[TextDetection] = []
        try:
            texts = [
                TextDetection(hit.text, bbox=hit.bbox, score=hit.confidence)
                for hit in self.read_texts(frame)
            ]
        except Exception as exc:
            warnings.append(f"OCR unavailable: {exc}")

        anchors: list[AnchorObservation] = []
        for name, anchor in sorted(self._profile.anchors.items()):
            try:
                result = self.evaluate_anchor(frame, name)
                anchors.append(
                    AnchorObservation(
                        name=name,
                        visible=result.found,
                        score=result.confidence,
                        anchor_type=getattr(anchor, "type", result.kind),
                    )
                )
            except Exception as exc:
                warnings.append(f"anchor {name}: {exc}")
                anchors.append(
                    AnchorObservation(
                        name=name,
                        visible=False,
                        anchor_type=getattr(anchor, "type", None),
                    )
                )

        screen_state = self.recognize_screen_state(frame)
        extracted, extractor_warnings = self.extract_content(frame, screen_state=screen_state)
        warnings.extend(extractor_warnings)
        return GameContentSnapshot(
            game_id=self._profile.game_id,
            image_path=image_path,
            screen_state=screen_state,
            anchors=anchors,
            texts=texts,
            extracted=extracted,
            warnings=warnings,
        )
