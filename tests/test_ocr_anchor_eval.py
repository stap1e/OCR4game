from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from ocr4game.config import OcrAnchorConfig, load_game_profile
from ocr4game.perception.ocr import OcrHit
from ocr4game.perception.ocr_eval import evaluate_ocr_anchor, match_texts, normalize_text


class FakeOcr:
    def __init__(self, hits: list[OcrHit]) -> None:
        self.hits = hits

    def read(self, frame, *, roi=None):
        return self.hits


def test_text_matching_modes() -> None:
    assert normalize_text("每日 实训，A") == "每日实训,a"
    assert match_texts(["每日实训"], "每日", mode="contains").matched
    assert match_texts(["每日 实训"], "每日实训", mode="normalized_contains").matched
    assert match_texts(["领取奖励"], r"领取.*", mode="regex").matched
    assert match_texts(["每日训练"], "每日实训", mode="fuzzy", fuzzy_threshold=0.5).matched


def test_evaluate_ocr_anchor_with_fake_engine(tmp_path: Path) -> None:
    image = tmp_path / "frame.png"
    cv2.imwrite(str(image), np.zeros((16, 16, 3), dtype=np.uint8))
    profile = load_game_profile("star_rail")
    anchor = OcrAnchorConfig(expect=["每日实训"], roi=[0, 0, 1, 1], min_confidence=0.5)

    summary = evaluate_ocr_anchor(
        profile,
        "daily_training_title",
        anchor,
        [image],
        ocr_engine=FakeOcr([OcrHit("每日 实训", 0.91, (5, 5))]),
    )

    assert summary["anchor_name"] == "daily_training_title"
    assert summary["anchor_type"] == "ocr"
    assert summary["num_images"] == 1
    assert summary["hit_count"] == 1
    assert summary["hit_rate"] == 1.0
    assert summary["score_mean"] == 0.91
    assert summary["text_examples"] == ["每日 实训"]
