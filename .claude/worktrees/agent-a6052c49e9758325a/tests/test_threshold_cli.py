from pathlib import Path

from ocr4game.tools.threshold_tune import main


def test_threshold_cli_offline_with_synced_assets() -> None:
    frame = Path("tests/fixtures/star_rail/frames/daily_panel.png").resolve()
    code = main(
        [
            "--game",
            "star_rail",
            "--anchor",
            "claim_button",
            "--frame",
            str(frame),
        ]
    )
    assert code == 0
