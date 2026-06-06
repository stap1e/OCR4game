"""锚点 fixture 回归：用静态合成图验证模板匹配。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from ocr4game.config import GameProfile, TemplateAnchorConfig
from ocr4game.perception.fusion import Perception
from ocr4game.perception.template import TemplateMatcher
from tests.conftest import STAR_RAIL_FIXTURES, load_star_rail_manifest


def _manifest_cases() -> list[dict[str, Any]]:
    manifest = load_star_rail_manifest()
    cases = manifest.get("cases") or []
    return [case for case in cases if isinstance(case, dict) and case.get("id")]


def _profile_for_case(case: dict[str, Any]) -> GameProfile:
    anchor_name = str(case["anchor"])
    template_rel = str(case["template"]).replace("\\", "/")
    image_name = Path(template_rel).name
    return GameProfile(
        game_id="star_rail_fixture",
        anchors={
            anchor_name: TemplateAnchorConfig(
                image=image_name,
                threshold=float(case.get("threshold", 0.85)),
                roi=case.get("roi"),
                scales=case.get("scales", [1.0]),
                match_mode=str(case.get("match_mode", "gray")),
            ),
        },
    )


@pytest.mark.parametrize("case", _manifest_cases(), ids=lambda c: str(c["id"]))
def test_template_anchor_regression(case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    frame_path = STAR_RAIL_FIXTURES / str(case["frame"])
    template_path = STAR_RAIL_FIXTURES / str(case["template"])
    assert frame_path.is_file(), f"缺少帧图: {frame_path}"
    assert template_path.is_file(), f"缺少模板: {template_path}"

    frame = cv2.imread(str(frame_path))
    assert frame is not None

    profile = _profile_for_case(case)
    assets_dir = template_path.parent

    monkeypatch.setattr(
        "ocr4game.perception.fusion.game_assets_dir",
        lambda _profile: assets_dir,
    )

    perception = Perception(profile)
    result = perception.evaluate_anchor(frame, str(case["anchor"]))

    expect_found = bool(case.get("expect_found", True))
    threshold = float(case.get("threshold", 0.85))
    assert result.found is expect_found, (
        f"anchor={case['anchor']} frame={case['frame']} "
        f"confidence={result.confidence:.3f} expect_found={expect_found}"
    )
    if expect_found:
        assert result.kind == "template"
        assert result.confidence >= threshold
    else:
        assert result.confidence < threshold

def test_template_matcher_handles_scaled_templates() -> None:
    template_path = STAR_RAIL_FIXTURES / "templates" / "claim_button.png"
    template = cv2.imread(str(template_path))
    assert template is not None

    scaled = cv2.resize(template, (0, 0), fx=1.05, fy=1.05, interpolation=cv2.INTER_CUBIC)
    frame = np.full((140, 220, 3), (28, 32, 40), dtype=np.uint8)
    y, x = 58, 74
    h, w = scaled.shape[:2]
    frame[y : y + h, x : x + w] = scaled

    matcher = TemplateMatcher()
    default_result = matcher.match(frame, template_path, threshold=0.95)
    scaled_result = matcher.match(
        frame,
        template_path,
        threshold=0.95,
        scales=[0.95, 1.0, 1.05],
    )

    assert default_result.found is False
    assert scaled_result.found is True
    assert scaled_result.confidence > default_result.confidence
    assert scaled_result.center == (x + w // 2, y + h // 2)


def test_manifest_covers_production_template_anchors() -> None:
    """生产 profile 中的 template 锚点都应在 manifest 中有正样本用例。"""
    from ocr4game.config import load_game_profile

    profile = load_game_profile("star_rail")
    production_templates = {
        name
        for name, anchor in profile.anchors.items()
        if isinstance(anchor, TemplateAnchorConfig)
    }

    positive_anchors = {
        str(case["anchor"])
        for case in _manifest_cases()
        if case.get("expect_found") is True
    }

    missing = production_templates - positive_anchors
    assert not missing, f"manifest 缺少正样本用例: {sorted(missing)}"


def test_manifest_frame_size_matches_images() -> None:
    manifest = load_star_rail_manifest()
    expected_w, expected_h = manifest.get("frame_size", [512, 288])
    for case in _manifest_cases():
        frame_path = STAR_RAIL_FIXTURES / str(case["frame"])
        frame = cv2.imread(str(frame_path))
        assert frame is not None
        h, w = frame.shape[:2]
        assert (w, h) == (expected_w, expected_h), case["id"]
