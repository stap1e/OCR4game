from __future__ import annotations

import json
from pathlib import Path

import pytest

from ocr4game.config import OcrAnchorConfig, TemplateAnchorConfig, load_game_profile
from ocr4game.tools.anchor_eval import evaluate_anchors, main, write_reports
from tests.conftest import STAR_RAIL_FIXTURES


def test_anchor_eval_writes_json_markdown_html_and_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = load_game_profile("star_rail")
    profile.anchors["claim_button"] = TemplateAnchorConfig(
        image="templates/claim_button.png",
        threshold=0.88,
        roi=[0.3, 0.5, 0.7, 0.95],
    )
    monkeypatch.setattr(
        "ocr4game.tools.anchor_eval.game_assets_dir",
        lambda _profile: STAR_RAIL_FIXTURES,
    )
    output_dir = tmp_path / "anchor_eval"
    screenshots = [STAR_RAIL_FIXTURES / "frames" / "daily_panel.png"]

    summary = evaluate_anchors(
        profile,
        screenshots,
        anchor_names=["claim_button"],
        output_dir=output_dir,
        write_overlays=True,
    )
    paths = write_reports(summary, output_dir, html=True)

    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
    assert paths["html"].is_file()
    assert list((output_dir / "overlays").glob("*.png"))

    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    claim = data["anchors"]["claim_button"]
    assert claim["num_images"] == 1
    assert claim["visible_count"] == 1
    assert claim["missing_count"] == 0
    assert claim["score_min"] >= 0.88
    assert claim["score_mean"] >= 0.88
    assert claim["score_median"] >= 0.88
    assert claim["score_p10"] >= 0.88
    assert claim["score_p90"] >= 0.88
    assert claim["recommended_threshold"] <= claim["score_p10"]
    assert claim["failure_examples"] == []

    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Anchor Statistics" in markdown
    assert "claim_button" in markdown
    assert "Failure Examples" in paths["html"].read_text(encoding="utf-8")


def test_anchor_eval_cli_filters_anchor_and_generates_html(tmp_path: Path) -> None:
    output_dir = tmp_path / "cli_eval"
    code = main(
        [
            "--game",
            "star_rail",
            "--anchor",
            "claim_button",
            "--screenshots",
            str(STAR_RAIL_FIXTURES / "frames" / "daily_panel.png"),
            "--output-dir",
            str(output_dir),
            "--html",
        ]
    )

    assert code == 0
    data = json.loads((output_dir / "anchor_eval_summary.json").read_text(encoding="utf-8"))
    assert list(data["anchors"]) == ["claim_button"]
    assert (output_dir / "anchor_eval_report.md").is_file()
    assert (output_dir / "anchor_eval_report.html").is_file()


def test_anchor_eval_cli_missing_screenshots_returns_nonzero(tmp_path: Path) -> None:
    code = main(
        [
            "--game",
            "star_rail",
            "--screenshots",
            str(tmp_path / "missing"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )
    assert code == 1


def test_anchor_eval_only_ocr_uses_ocr_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = load_game_profile("star_rail")
    profile.anchors["daily_training_title"] = OcrAnchorConfig(expect=["每日实训"])
    screenshot = STAR_RAIL_FIXTURES / "frames" / "daily_panel.png"

    monkeypatch.setattr(
        "ocr4game.tools.anchor_eval.evaluate_ocr_anchor",
        lambda *_args, **_kwargs: {
            "type": "ocr",
            "anchor_name": "daily_training_title",
            "num_images": 1,
            "hit_count": 1,
            "miss_count": 0,
            "hit_rate": 1.0,
            "score_mean": 0.91,
            "text_examples": ["每日实训"],
            "miss_examples": [],
            "visible_count": 1,
            "missing_count": 0,
            "score_min": 0.91,
            "score_median": 0.91,
            "score_p10": 0.91,
            "score_p90": 0.91,
            "recommended_threshold": None,
            "failure_examples": [],
            "warning": None,
        },
    )

    summary = evaluate_anchors(
        profile,
        [screenshot],
        anchor_names=["daily_training_title"],
        output_dir=tmp_path,
        include_ocr=True,
        only_ocr=True,
    )
    assert summary["anchors"]["daily_training_title"]["hit_count"] == 1
    markdown = write_reports(summary, tmp_path, html=False)["markdown"].read_text(encoding="utf-8")
    assert "OCR Anchor Diagnostics" in markdown
