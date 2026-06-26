from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from ocr4game.tools import replay


def _write_trace(run_dir: Path, records: list[dict]) -> None:
    with (run_dir / "trace.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _base_record(**kwargs) -> dict:
    record = {
        "ts": "2026-01-01T00:00:00.000",
        "event": "action_failed",
        "game_id": "star_rail",
        "task_id": "daily",
        "step_index": 1,
        "step_name": "claim",
        "action_type": "click_template",
        "status": "failed",
    }
    record.update(kwargs)
    return record


def test_replay_without_screenshots_returns_nonzero(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_trace(run_dir, [_base_record(event="task_finished", status="finished")])

    assert replay.main(["--run", str(run_dir)]) == 1


def test_replay_with_screenshot_writes_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    cv2.imwrite(str(run_dir / "fail_claim.png"), image)
    _write_trace(
        run_dir,
        [_base_record(anchor_name="claim_button", screenshot_path="fail_claim.png")],
    )

    class DummyPerception:
        def __init__(self, _profile) -> None:
            return None

        def evaluate_anchor(self, _frame, anchor_name: str):
            return type(
                "Result",
                (),
                {
                    "found": False,
                    "kind": "template",
                    "confidence": 0.1,
                    "center": (0, 0),
                    "detail": anchor_name,
                },
            )()

    monkeypatch.setattr(replay, "Perception", DummyPerception)

    assert replay.main(["--run", str(run_dir)]) == 0
    summary = json.loads((run_dir / "replay_summary.json").read_text(encoding="utf-8"))
    assert summary["game_id"] == "star_rail"
    assert summary["task_id"] == "daily"
    assert summary["total_evaluations"] == 1
    assert summary["results"][0]["anchor_name"] == "claim_button"
    assert (run_dir / "replay_report.md").is_file()


def test_replay_step_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    cv2.imwrite(str(run_dir / "fail_1.png"), image)
    cv2.imwrite(str(run_dir / "fail_2.png"), image)
    _write_trace(
        run_dir,
        [
            _base_record(step_index=1, anchor_name="claim_button", screenshot_path="fail_1.png"),
            _base_record(step_index=2, anchor_name="confirm_button", screenshot_path="fail_2.png"),
        ],
    )

    class DummyPerception:
        def __init__(self, _profile) -> None:
            return None

        def evaluate_anchor(self, _frame, anchor_name: str):
            return type(
                "Result",
                (),
                {
                    "found": True,
                    "kind": "template",
                    "confidence": 0.9,
                    "center": (5, 5),
                    "detail": anchor_name,
                },
            )()

    monkeypatch.setattr(replay, "Perception", DummyPerception)

    assert replay.main(["--run", str(run_dir), "--step-index", "2"]) == 0
    summary = json.loads((run_dir / "replay_summary.json").read_text(encoding="utf-8"))
    assert summary["total_events"] == 1
    assert summary["results"][0]["anchor_name"] == "confirm_button"
