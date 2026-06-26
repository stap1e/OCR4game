from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ocr4game.config import (
    ContentExtractorConfig,
    ContentFieldConfig,
    GameProfile,
    GlobalConfig,
    ScreenStateConfig,
)
from ocr4game.perception.content import GameContentSnapshot, ScreenStateResult, TextDetection
from ocr4game.workflow.conditions import evaluate_condition, validate_condition_syntax
from ocr4game.workflow.context import RunContext


@dataclass
class DummyCapture:
    calls: int = 0

    def grab(self):
        self.calls += 1
        return np.zeros((10, 10, 3), dtype=np.uint8)


class DummyPerception:
    def snapshot(self, frame):
        return GameContentSnapshot(
            game_id="test",
            image_path=None,
            screen_state=ScreenStateResult("reward_screen", 1.0, [], []),
            anchors=[],
            texts=[TextDetection("领取奖励")],
            extracted={"daily_training": {"reward_claimable": True, "active_points": 500}},
            warnings=[],
        )


def _ctx(capture: DummyCapture) -> RunContext:
    return RunContext(
        profile=GameProfile(game_id="test"),
        global_cfg=GlobalConfig(),
        capture=capture,  # type: ignore[arg-type]
        perception=DummyPerception(),  # type: ignore[arg-type]
    )


def test_content_conditions_use_cached_snapshot_frame() -> None:
    capture = DummyCapture()
    condition = {
        "all": [
            {"screen_state": "reward_screen"},
            {"ocr_contains": "领取"},
            {"content_gt": {"field": "daily_training.active_points", "value": 400}},
            {"content_eq": {"field": "daily_training.reward_claimable", "value": True}},
        ]
    }

    assert evaluate_condition(condition, _ctx(capture)) is True
    assert capture.calls == 1


def test_validate_content_condition_syntax() -> None:
    profile = GameProfile(
        game_id="test",
        screen_states={"reward_screen": ScreenStateConfig()},
        content_extractors={
            "daily_training": ContentExtractorConfig(
                fields={"active_points": ContentFieldConfig(type="ocr_number")}
            )
        },
    )
    errors = validate_condition_syntax(
        {"content_gt": {"field": "daily_training.active_points", "value": 400}},
        profile=profile,
        path="steps.s.when",
    )
    assert errors == []
    assert validate_condition_syntax({"screen_state": "missing"}, profile=profile, path="p")
