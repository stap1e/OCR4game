"""OCR text matching and offline OCR-anchor diagnostics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np

from ocr4game.config import GameProfile, OcrAnchorConfig
from ocr4game.perception.ocr import OcrEngine, OcrHit

MatchMode = Literal["exact", "contains", "contains_any", "regex", "normalized_contains", "fuzzy"]

_PUNCT_TRANSLATION = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "：": ":",
        "；": ";",
        "！": "!",
        "？": "?",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "、": ",",
        " ": "",
        "\t": "",
        "\n": "",
        "\r": "",
    }
)


@dataclass(frozen=True)
class TextMatch:
    matched: bool
    text: str | None = None
    score: float | None = None
    expected: str | None = None
    mode: str = "contains"


def normalize_text(text: str) -> str:
    return str(text).lower().translate(_PUNCT_TRANSLATION)


def match_texts(
    texts: list[str],
    expected: list[str] | str,
    *,
    mode: MatchMode = "contains",
    fuzzy_threshold: float = 0.75,
) -> TextMatch:
    expected_items = [expected] if isinstance(expected, str) else list(expected)
    if not expected_items:
        return TextMatch(False, mode=mode)

    for text in texts:
        text_value = str(text)
        for exp in expected_items:
            exp_value = str(exp)
            if mode == "exact" and text_value == exp_value:
                return TextMatch(True, text_value, 1.0, exp_value, mode)
            if mode in {"contains", "contains_any"} and exp_value in text_value:
                return TextMatch(True, text_value, 1.0, exp_value, mode)
            if mode == "regex" and re.search(exp_value, text_value):
                return TextMatch(True, text_value, 1.0, exp_value, mode)
            if mode == "normalized_contains" and normalize_text(exp_value) in normalize_text(text_value):
                return TextMatch(True, text_value, 1.0, exp_value, mode)
            if mode == "fuzzy":
                ratio = SequenceMatcher(None, normalize_text(exp_value), normalize_text(text_value)).ratio()
                if ratio >= fuzzy_threshold:
                    return TextMatch(True, text_value, ratio, exp_value, mode)
    return TextMatch(False, mode=mode)


def hit_bbox(hit: OcrHit) -> tuple[int, int, int, int] | None:
    bbox = getattr(hit, "bbox", None)
    if bbox is None:
        return None
    return tuple(int(value) for value in bbox)


def evaluate_ocr_anchor(
    profile: GameProfile,
    anchor_name: str,
    anchor: OcrAnchorConfig,
    screenshots: list[Path],
    *,
    ocr_engine: OcrEngine | None = None,
) -> dict[str, Any]:
    engine = ocr_engine or OcrEngine()
    scores: list[float] = []
    hit_count = 0
    text_examples: list[str] = []
    miss_examples: list[dict[str, Any]] = []
    warning: str | None = None

    for screenshot in screenshots:
        frame = cv2.imread(str(screenshot))
        if frame is None:
            miss_examples.append(
                {
                    "image": str(screenshot),
                    "recognized_text": [],
                    "expected": list(anchor.expect),
                    "reason": "image unreadable",
                }
            )
            continue
        try:
            hits = engine.read(frame, roi=anchor.roi)
        except Exception as exc:  # pragma: no cover - exercised through CLI warning tests
            warning = f"OCR unavailable: {exc}"
            break

        candidates = [hit for hit in hits if hit.confidence >= anchor.min_confidence]
        texts = [hit.text for hit in candidates]
        match = match_texts(texts, anchor.expect, mode="normalized_contains")
        if match.matched:
            hit_count += 1
            best = next((hit for hit in candidates if hit.text == match.text), candidates[0])
            scores.append(float(best.confidence))
            if match.text and match.text not in text_examples:
                text_examples.append(match.text)
        else:
            miss_examples.append(
                {
                    "image": str(screenshot),
                    "recognized_text": texts,
                    "expected": list(anchor.expect),
                    "reason": "expected text not found",
                }
            )

    num_images = len(screenshots)
    miss_count = num_images - hit_count
    return {
        "type": "ocr",
        "anchor_type": "ocr",
        "anchor_name": anchor_name,
        "num_images": num_images,
        "hit_count": hit_count,
        "miss_count": miss_count,
        "hit_rate": hit_count / num_images if num_images else 0.0,
        "score_mean": float(np.mean(scores)) if scores else None,
        "text_examples": text_examples[:5],
        "miss_examples": miss_examples[:5],
        "warning": warning,
        "expect": list(anchor.expect),
        "min_confidence": anchor.min_confidence,
        "visible_count": hit_count,
        "missing_count": miss_count,
        "score_min": min(scores) if scores else None,
        "score_median": float(np.median(scores)) if scores else None,
        "score_p10": float(np.percentile(scores, 10)) if scores else None,
        "score_p90": float(np.percentile(scores, 90)) if scores else None,
        "recommended_threshold": None,
        "failure_examples": miss_examples[:5],
    }


__all__ = [
    "TextMatch",
    "evaluate_ocr_anchor",
    "hit_bbox",
    "match_texts",
    "normalize_text",
]
