from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ocr4game.perception.content import (
    AnchorObservation,
    GameContentSnapshot,
    ScreenStateResult,
    TextDetection,
)


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _evaluate_case(case_path: Path, snapshot: GameContentSnapshot) -> dict[str, float]:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    expected = case["expected"]
    data = snapshot.to_dict()

    screen_ok = data["screen_state"]["state"] == expected.get("screen_state")
    visible = {anchor["name"] for anchor in data["anchors"] if anchor["visible"]}
    anchor_expected = expected.get("anchors_visible") or []
    anchor_hits = sum(1 for name in anchor_expected if name in visible)

    all_text = " ".join(item["text"] for item in data["texts"])
    text_expected = expected.get("texts_contains") or []
    text_hits = sum(1 for text in text_expected if text in all_text)

    extracted_expected = expected.get("extracted") or {}
    extracted_hits = sum(
        1 for path, value in extracted_expected.items() if _get_path(data["extracted"], path) == value
    )

    return {
        "screen_state_accuracy": 1.0 if screen_ok else 0.0,
        "anchor_visible_hit_rate": anchor_hits / len(anchor_expected) if anchor_expected else 1.0,
        "text_contains_hit_rate": text_hits / len(text_expected) if text_expected else 1.0,
        "extracted_exact_match_rate": extracted_hits / len(extracted_expected)
        if extracted_expected
        else 1.0,
    }


def test_content_case_metrics_helper() -> None:
    snapshot = GameContentSnapshot(
        game_id="star_rail",
        image_path="daily_panel.png",
        screen_state=ScreenStateResult("reward_screen", 1.0, [], []),
        anchors=[AnchorObservation("claim_button", True)],
        texts=[TextDetection("领取奖励")],
        extracted={"daily_training": {"reward_claimable": True}},
        warnings=[],
    )
    metrics = _evaluate_case(
        Path("tests/fixtures/star_rail/content_cases/daily_panel.json"), snapshot
    )
    assert metrics == {
        "screen_state_accuracy": 1.0,
        "anchor_visible_hit_rate": 1.0,
        "text_contains_hit_rate": 1.0,
        "extracted_exact_match_rate": 1.0,
    }
