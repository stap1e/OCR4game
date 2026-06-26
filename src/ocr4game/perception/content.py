"""Structured content-recognition result models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


def _json_safe(value: Any) -> Any:
    """Convert tuples and numpy scalar-like values into JSON-safe values."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return value


@dataclass
class TextDetection:
    text: str
    bbox: tuple[int, int, int, int] | None = None
    score: float | None = None
    region: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": str(self.text),
            "bbox": _json_safe(self.bbox),
            "score": _json_safe(self.score),
            "region": self.region,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class AnchorObservation:
    name: str
    visible: bool
    score: float | None = None
    bbox: tuple[int, int, int, int] | None = None
    anchor_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": str(self.name),
            "visible": bool(self.visible),
            "score": _json_safe(self.score),
            "bbox": _json_safe(self.bbox),
            "anchor_type": self.anchor_type,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class ScreenStateResult:
    state: str
    confidence: float
    matched_rules: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": str(self.state),
            "confidence": float(self.confidence),
            "matched_rules": list(self.matched_rules),
            "failed_rules": list(self.failed_rules),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class GameContentSnapshot:
    game_id: str
    image_path: str | None
    screen_state: ScreenStateResult | None
    anchors: list[AnchorObservation]
    texts: list[TextDetection]
    extracted: dict[str, Any]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": str(self.game_id),
            "image_path": self.image_path,
            "screen_state": self.screen_state.to_dict() if self.screen_state else None,
            "anchors": [anchor.to_dict() for anchor in self.anchors],
            "texts": [text.to_dict() for text in self.texts],
            "extracted": _json_safe(self.extracted),
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


__all__ = [
    "AnchorObservation",
    "GameContentSnapshot",
    "ScreenStateResult",
    "TextDetection",
]
