"""Helpers for extracting lightweight perception diagnostics."""

from __future__ import annotations

from typing import Any

import numpy as np

from ocr4game.config import OcrAnchorConfig, TemplateAnchorConfig
from ocr4game.perception.roi import relative_roi_to_pixels


def diagnostics_from_anchor_result(
    result: Any,
    *,
    anchor_name: str | None = None,
    anchor_config: Any = None,
    frame: np.ndarray | None = None,
) -> dict[str, Any]:
    """Return trace-friendly diagnostics from a perception result.

    The perception API intentionally exposes a small stable result object. This helper keeps
    diagnostics best-effort and backward compatible by only reading attributes that exist.
    """

    extra: dict[str, Any] = {}
    kind = getattr(result, "kind", None)
    detail = getattr(result, "detail", "")
    center = getattr(result, "center", None)
    confidence = getattr(result, "confidence", None)

    data: dict[str, Any] = {
        "anchor_name": anchor_name,
        "matched_score": confidence,
        "extra": extra,
    }

    if center is not None:
        extra["center"] = center
    if kind is not None:
        extra["anchor_type"] = kind
    if detail:
        extra["detail"] = detail

    roi = getattr(anchor_config, "roi", None)
    if roi is not None and frame is not None:
        try:
            x0, y0, x1, y1 = relative_roi_to_pixels(frame, roi)
            data["roi"] = [x0, y0, x1 - x0, y1 - y0]
        except Exception:
            extra["roi"] = roi
    elif roi is not None:
        extra["roi"] = roi

    if isinstance(anchor_config, TemplateAnchorConfig):
        extra["template_name"] = anchor_config.image
        extra["threshold"] = anchor_config.threshold
        extra["match_mode"] = anchor_config.match_mode
        extra["scales"] = anchor_config.scales
    elif isinstance(anchor_config, OcrAnchorConfig):
        extra["expect"] = anchor_config.expect
        extra["min_confidence"] = anchor_config.min_confidence
        if detail:
            extra["ocr_text"] = detail

    if center is not None:
        data["matched_bbox"] = [center[0], center[1], 0, 0]

    return data


__all__ = ["diagnostics_from_anchor_result"]
