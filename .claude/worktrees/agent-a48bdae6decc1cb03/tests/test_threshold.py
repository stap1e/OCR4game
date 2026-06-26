import cv2
import pytest

from ocr4game.config import TemplateAnchorConfig, load_game_profile
from ocr4game.games.registry import get_plugin_spec, load_plugin_registry
from ocr4game.tools.threshold import (
    evaluate_template_anchor,
    suggest_threshold,
    sweep_lines,
)
from tests.conftest import STAR_RAIL_FIXTURES


def test_suggest_threshold_clamps() -> None:
    assert suggest_threshold(0.99) == 0.96
    assert suggest_threshold(0.52) == 0.50
    assert suggest_threshold(0.40) == 0.50


def test_sweep_lines() -> None:
    lines = sweep_lines(0.87)
    assert any("0.85: match" in line for line in lines)
    assert any("0.90: miss" in line for line in lines)


def test_evaluate_template_anchor_with_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = load_game_profile("star_rail")
    frame_path = STAR_RAIL_FIXTURES / "frames" / "daily_panel.png"
    frame = cv2.imread(str(frame_path))
    assert frame is not None

    profile.anchors["claim_button"] = TemplateAnchorConfig(
        image="templates/claim_button.png",
        threshold=0.88,
        roi=[0.3, 0.5, 0.7, 0.95],
    )
    monkeypatch.setattr(
        "ocr4game.tools.threshold.game_assets_dir",
        lambda _profile: STAR_RAIL_FIXTURES,
    )

    report = evaluate_template_anchor(profile, "claim_button", frame)
    assert report.confidence >= 0.88
    assert report.suggested_threshold <= report.confidence


def test_star_rail_plugin_from_entry_points_or_builtin() -> None:
    registry = load_plugin_registry(force_reload=True)
    assert "star_rail" in registry
    spec = get_plugin_spec("star_rail")
    assert spec.plugin_cls.game_id == "star_rail"
    assert spec.source in {"entry-point", "builtin"}
