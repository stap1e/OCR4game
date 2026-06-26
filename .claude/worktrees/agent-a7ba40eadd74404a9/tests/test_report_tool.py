from __future__ import annotations

import json
from pathlib import Path

from ocr4game.tools.report import main


def _write_trace(run_dir: Path) -> None:
    records = [
        {
            "ts": "2026-01-01T00:00:00.000",
            "event": "task_started",
            "game_id": "star_rail",
            "task_id": "daily",
            "status": "started",
        },
        {
            "ts": "2026-01-01T00:00:01.000",
            "event": "action_failed",
            "game_id": "star_rail",
            "task_id": "daily",
            "step_index": 1,
            "step_name": "claim",
            "action_index": 0,
            "action_type": "click_template",
            "status": "failed",
            "message": "未找到锚点",
            "anchor_name": "claim_button",
            "matched_score": 0.42,
            "matched_bbox": [1, 2, 3, 4],
            "screenshot_path": "fail_claim.png",
        },
        {
            "ts": "2026-01-01T00:00:02.000",
            "event": "task_finished",
            "game_id": "star_rail",
            "task_id": "daily",
            "status": "failed",
            "elapsed_ms": 2000,
        },
    ]
    with (run_dir / "trace.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_report_tool_generates_markdown_and_html(tmp_path: Path) -> None:
    run_dir = tmp_path / "star_rail_20260101_000000"
    run_dir.mkdir()
    (run_dir / "fail_claim.png").write_bytes(b"not a real png")
    _write_trace(run_dir)

    assert main(["--run", str(run_dir)]) == 0

    markdown = (run_dir / "report.md").read_text(encoding="utf-8")
    html = (run_dir / "report.html").read_text(encoding="utf-8")
    assert "Failure Summary" in markdown
    assert "Step Timeline" in markdown
    assert "Anchor Diagnostics" in markdown
    assert "claim_button" in markdown
    assert "Failure Summary" in html


def test_report_tool_missing_trace_returns_nonzero(tmp_path: Path) -> None:
    run_dir = tmp_path / "empty_run"
    run_dir.mkdir()

    assert main(["--run", str(run_dir)]) == 1
