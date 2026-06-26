from __future__ import annotations

import json
from pathlib import Path

from ocr4game.perception.content import GameContentSnapshot, ScreenStateResult, TextDetection
from ocr4game.tools import recognize
from tests.conftest import STAR_RAIL_FIXTURES


def _fake_snapshot(self, frame, *, image_path=None):
    return GameContentSnapshot(
        game_id=self._profile.game_id,
        image_path=image_path,
        screen_state=ScreenStateResult("reward_screen", 0.9, ["anchor_visible:claim_button"], []),
        anchors=[],
        texts=[TextDetection("领取奖励")],
        extracted={"daily_training": {"reward_claimable": True}},
        warnings=[],
    )


def test_recognize_single_image_json_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr("ocr4game.perception.fusion.Perception.snapshot", _fake_snapshot)
    image = STAR_RAIL_FIXTURES / "frames" / "daily_panel.png"

    code = recognize.main(["--game", "star_rail", "--image", str(image), "--json"])

    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["game_id"] == "star_rail"
    assert data["screen_state"]["state"] == "reward_screen"
    assert data["texts"][0]["text"] == "领取奖励"


def test_recognize_batch_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("ocr4game.perception.fusion.Perception.snapshot", _fake_snapshot)
    output_dir = tmp_path / "recognize"

    code = recognize.main(
        [
            "--game",
            "star_rail",
            "--images",
            str(STAR_RAIL_FIXTURES / "frames"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert (output_dir / "recognize_summary.json").is_file()
    assert (output_dir / "recognize_report.md").is_file()
    assert list(output_dir.glob("*.content.json"))
