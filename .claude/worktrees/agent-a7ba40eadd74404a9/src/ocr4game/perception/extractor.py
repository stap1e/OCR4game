"""Configured content extraction from game screenshots."""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from ocr4game.config import ContentFieldConfig, GameProfile
from ocr4game.perception.content import ScreenStateResult
from ocr4game.perception.ocr_eval import match_texts
from ocr4game.perception.roi import crop_roi


class ContentExtractor:
    def extract(
        self,
        frame: np.ndarray,
        profile: GameProfile,
        perception: Any,
        *,
        screen_state: ScreenStateResult | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        extracted: dict[str, Any] = {}
        warnings: list[str] = []
        current_state = screen_state.state if screen_state else None

        for extractor_name, config in profile.content_extractors.items():
            if config.when_state and current_state and config.when_state != current_state:
                continue
            values: dict[str, Any] = {}
            for field_name, field in config.fields.items():
                try:
                    values[field_name] = self._extract_field(
                        field, frame, perception, current_state=current_state
                    )
                except Exception as exc:
                    values[field_name] = None
                    warnings.append(f"{extractor_name}.{field_name}: {exc}")
            extracted[extractor_name] = values
        return extracted, warnings

    def _extract_field(
        self,
        field: ContentFieldConfig,
        frame: np.ndarray,
        perception: Any,
        *,
        current_state: str | None,
    ) -> Any:
        if field.type == "anchor_visible":
            if not field.anchor:
                raise ValueError("anchor_visible field missing anchor")
            return bool(perception.evaluate_anchor(frame, field.anchor).found)
        if field.type == "anchor_score":
            if not field.anchor:
                raise ValueError("anchor_score field missing anchor")
            return float(perception.evaluate_anchor(frame, field.anchor).confidence)
        if field.type == "screen_state":
            return current_state

        hits = _read_hits(frame, perception, field.roi)
        texts = [str(getattr(hit, "text", hit)) for hit in hits if getattr(hit, "confidence", 1.0) >= field.min_confidence]
        joined = " ".join(texts)

        if field.type == "ocr_text":
            if field.contains and not match_texts(texts, field.contains, mode="normalized_contains").matched:
                return None
            if field.contains_any and not match_texts(texts, field.contains_any, mode="normalized_contains").matched:
                return None
            return joined or None
        if field.type == "ocr_regex":
            if not field.regex:
                raise ValueError("ocr_regex field missing regex")
            match = re.search(field.regex, joined)
            if not match:
                return None
            return match.group(1) if match.groups() else match.group(0)
        if field.type == "ocr_number":
            pattern = field.regex or r"\d+"
            numbers = [int(item) for item in re.findall(pattern, joined)]
            return max(numbers) if numbers else None
        raise ValueError(f"unsupported content field type: {field.type}")


def _read_hits(frame: np.ndarray, perception: Any, roi: list[float] | None) -> list[Any]:
    target = frame
    read_roi = roi
    if roi is not None and any(float(value) > 1.0 for value in roi):
        target = _crop_absolute_or_relative(frame, roi)
        read_roi = None
    try:
        return list(perception.read_texts(target, roi=read_roi))
    except AttributeError:
        target = _crop_absolute_or_relative(frame, roi) if roi else frame
        return list(perception._ocr.read(target))  # noqa: SLF001 - compatibility with existing Perception wrapper


def _crop_absolute_or_relative(frame: np.ndarray, roi: list[float] | None) -> np.ndarray:
    if roi is None:
        return frame
    if all(0.0 <= float(value) <= 1.0 for value in roi):
        return crop_roi(frame, roi)
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = [int(value) for value in roi]
    x0 = max(0, min(x0, w - 1))
    y0 = max(0, min(y0, h - 1))
    x1 = max(x0 + 1, min(x1, w))
    y1 = max(y0 + 1, min(y1, h))
    return frame[y0:y1, x0:x1].copy()


__all__ = ["ContentExtractor"]
