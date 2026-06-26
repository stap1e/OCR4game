from __future__ import annotations

import json

import numpy as np

from ocr4game.perception.content import (
    AnchorObservation,
    GameContentSnapshot,
    ScreenStateResult,
    TextDetection,
)


def test_content_models_json_safe() -> None:
    snapshot = GameContentSnapshot(
        game_id="star_rail",
        image_path="frame.png",
        screen_state=ScreenStateResult("reward_screen", np.float32(0.87), ["a"], ["b"]),
        anchors=[
            AnchorObservation(
                "claim_button",
                True,
                score=np.float32(0.9),
                bbox=(1, 2, 3, 4),
                anchor_type="template",
            )
        ],
        texts=[TextDetection("领取", bbox=(5, 6, 7, 8), score=np.float64(0.95), region="button")],
        extracted={"daily_training": {"active_points": np.int64(500)}},
        warnings=[],
    )

    data = snapshot.to_dict()
    assert data["screen_state"]["confidence"] == 0.8700000047683716
    assert data["anchors"][0]["bbox"] == [1, 2, 3, 4]
    assert data["texts"][0]["bbox"] == [5, 6, 7, 8]
    assert data["extracted"]["daily_training"]["active_points"] == 500
    assert json.loads(snapshot.to_json())["game_id"] == "star_rail"
