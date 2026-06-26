from __future__ import annotations

import numpy as np

from ocr4game.config import GameProfile, ScreenStateConfig, TemplateAnchorConfig
from ocr4game.perception.fusion import PerceptionResult
from ocr4game.perception.ocr import OcrHit
from ocr4game.perception.screen_state import ScreenStateRecognizer


class FakePerception:
    def __init__(self, anchors: dict[str, bool], texts: list[str] | None = None) -> None:
        self.anchors = anchors
        self.texts = texts or []

    def evaluate_anchor(self, frame, name: str) -> PerceptionResult:
        return PerceptionResult(self.anchors.get(name, False), "template", 0.9, (0, 0))

    def read_texts(self, frame, *, roi=None):
        return [OcrHit(text, 0.9, (0, 0)) for text in self.texts]


def _profile() -> GameProfile:
    return GameProfile(
        game_id="test",
        anchors={
            "claim_button": TemplateAnchorConfig(image="claim.png"),
            "loading_spinner": TemplateAnchorConfig(image="loading.png"),
        },
        screen_states={
            "reward_screen": ScreenStateConfig(
                require=[{"anchor_visible": "claim_button"}],
                optional=[{"ocr_contains_any": ["领取", "奖励"]}],
                reject=[{"anchor_visible": "loading_spinner"}],
            )
        },
    )


def test_screen_state_recognizes_best_candidate() -> None:
    result = ScreenStateRecognizer().recognize(
        np.zeros((10, 10, 3), dtype=np.uint8),
        _profile(),
        FakePerception({"claim_button": True}, ["领取奖励"]),
    )
    assert result.state == "reward_screen"
    assert result.confidence == 1.0
    assert any("claim_button" in rule for rule in result.matched_rules)


def test_screen_state_rejects_matching_reject_rule() -> None:
    result = ScreenStateRecognizer().recognize(
        np.zeros((10, 10, 3), dtype=np.uint8),
        _profile(),
        FakePerception({"claim_button": True, "loading_spinner": True}, ["领取"]),
    )
    assert result.state == "unknown"
