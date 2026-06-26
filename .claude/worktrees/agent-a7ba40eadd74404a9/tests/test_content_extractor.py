from __future__ import annotations

import numpy as np

from ocr4game.config import (
    ContentExtractorConfig,
    ContentFieldConfig,
    GameProfile,
    TemplateAnchorConfig,
)
from ocr4game.perception.extractor import ContentExtractor
from ocr4game.perception.fusion import PerceptionResult
from ocr4game.perception.ocr import OcrHit


class FakePerception:
    def evaluate_anchor(self, frame, name: str) -> PerceptionResult:
        return PerceptionResult(name == "claim_button", "template", 0.92, (1, 1))

    def read_texts(self, frame, *, roi=None):
        return [OcrHit("每日实训 活跃度 500/500", 0.9, (1, 1))]


def test_content_extractor_extracts_fields() -> None:
    profile = GameProfile(
        game_id="test",
        anchors={"claim_button": TemplateAnchorConfig(image="claim.png")},
        content_extractors={
            "daily_training": ContentExtractorConfig(
                fields={
                    "title": ContentFieldConfig(type="ocr_text", contains_any=["每日实训"]),
                    "active_points": ContentFieldConfig(type="ocr_number"),
                    "reward_claimable": ContentFieldConfig(type="anchor_visible", anchor="claim_button"),
                    "claim_score": ContentFieldConfig(type="anchor_score", anchor="claim_button"),
                }
            )
        },
    )

    extracted, warnings = ContentExtractor().extract(
        np.zeros((10, 10, 3), dtype=np.uint8), profile, FakePerception()
    )

    assert warnings == []
    assert extracted["daily_training"]["title"] == "每日实训 活跃度 500/500"
    assert extracted["daily_training"]["active_points"] == 500
    assert extracted["daily_training"]["reward_claimable"] is True
    assert extracted["daily_training"]["claim_score"] == 0.92


def test_content_extractor_field_failure_becomes_warning() -> None:
    profile = GameProfile(
        game_id="test",
        content_extractors={
            "bad": ContentExtractorConfig(
                fields={"missing": ContentFieldConfig(type="anchor_visible")}
            )
        },
    )

    extracted, warnings = ContentExtractor().extract(
        np.zeros((10, 10, 3), dtype=np.uint8), profile, FakePerception()
    )

    assert extracted["bad"]["missing"] is None
    assert warnings
