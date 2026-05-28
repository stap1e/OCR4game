"""模板阈值标定逻辑。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ocr4game.config import GameProfile, TemplateAnchorConfig
from ocr4game.perception.template import TemplateMatcher
from ocr4game.resources import game_assets_dir


@dataclass(frozen=True)
class ThresholdReport:
    anchor: str
    confidence: float
    current_threshold: float
    suggested_threshold: float
    center: tuple[int, int]
    template_path: Path


def suggest_threshold(confidence: float, *, margin: float = 0.03) -> float:
    value = confidence - margin
    return round(max(0.5, min(0.99, value)), 2)


def sweep_lines(confidence: float, *, levels: list[float] | None = None) -> list[str]:
    if levels is None:
        levels = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.95]
    return [
        f"  {level:.2f}: {'match' if confidence >= level else 'miss'}"
        for level in levels
    ]


def evaluate_template_anchor(
    profile: GameProfile,
    anchor_name: str,
    frame: np.ndarray,
    *,
    margin: float = 0.03,
) -> ThresholdReport:
    anchor = profile.anchors.get(anchor_name)
    if anchor is None:
        raise KeyError(f"未定义锚点: {anchor_name}")
    if not isinstance(anchor, TemplateAnchorConfig):
        raise TypeError(f"锚点 {anchor_name} 不是 template 类型")

    template_path = game_assets_dir(profile) / anchor.image
    matcher = TemplateMatcher()
    result = matcher.confidence(frame, template_path, roi=anchor.roi)
    suggested = suggest_threshold(result.confidence, margin=margin)

    return ThresholdReport(
        anchor=anchor_name,
        confidence=result.confidence,
        current_threshold=anchor.threshold,
        suggested_threshold=suggested,
        center=result.center,
        template_path=template_path,
    )


def list_template_anchors(profile: GameProfile) -> list[str]:
    return [
        name
        for name, anchor in profile.anchors.items()
        if isinstance(anchor, TemplateAnchorConfig)
    ]
