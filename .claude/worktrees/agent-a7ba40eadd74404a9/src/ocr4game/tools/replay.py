"""Offline replay of saved run screenshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import cv2

from ocr4game.config import load_game_profile
from ocr4game.perception.fusion import Perception
from ocr4game.tools.report import _load_trace


def _find_replay_events(
    records: list[dict[str, Any]],
    *,
    step_index: int | None = None,
    anchor: str | None = None,
) -> list[dict[str, Any]]:
    events = [record for record in records if record.get("screenshot_path")]
    if step_index is not None:
        events = [record for record in events if record.get("step_index") == step_index]
    if anchor is not None:
        events = [record for record in events if record.get("anchor_name") in {anchor, None, ""}]
    return events


def _infer_metadata(records: list[dict[str, Any]]) -> tuple[str, str]:
    game_id = next((str(r.get("game_id")) for r in records if r.get("game_id")), "")
    task_id = next((str(r.get("task_id")) for r in records if r.get("task_id")), "")
    if not game_id or not task_id:
        raise ValueError("无法从 trace 推断 game_id/task_id")
    return game_id, task_id


def replay_run(
    run_dir: Path,
    *,
    step_index: int | None = None,
    anchor: str | None = None,
) -> Path:
    records = _load_trace(run_dir)
    game_id, task_id = _infer_metadata(records)
    events = _find_replay_events(records, step_index=step_index, anchor=anchor)
    if not events:
        raise ValueError("trace 中没有可 replay 的 screenshot_path 事件")

    profile = load_game_profile(game_id)
    perception = Perception(profile)
    results: list[dict[str, Any]] = []

    for event in events:
        screenshot_path = run_dir / str(event.get("screenshot_path"))
        frame = cv2.imread(str(screenshot_path))
        if frame is None:
            results.append(
                {
                    "screenshot_path": str(event.get("screenshot_path")),
                    "step_index": event.get("step_index"),
                    "anchor_name": anchor or event.get("anchor_name"),
                    "status": "failed",
                    "message": "无法读取截图",
                }
            )
            continue

        anchor_names = [anchor] if anchor else []
        if not anchor_names and event.get("anchor_name"):
            anchor_names = [str(event.get("anchor_name"))]
        if not anchor_names:
            anchor_names = list(profile.anchors)

        for anchor_name in anchor_names:
            result = perception.evaluate_anchor(frame, anchor_name)
            results.append(
                {
                    "screenshot_path": str(event.get("screenshot_path")),
                    "step_index": event.get("step_index"),
                    "step_name": event.get("step_name"),
                    "anchor_name": anchor_name,
                    "found": result.found,
                    "kind": result.kind,
                    "confidence": result.confidence,
                    "center": list(result.center),
                    "detail": result.detail,
                }
            )

    summary = {
        "game_id": game_id,
        "task_id": task_id,
        "run_dir": str(run_dir),
        "filters": {"step_index": step_index, "anchor": anchor},
        "total_events": len(events),
        "total_evaluations": len(results),
        "results": results,
    }
    out = run_dir / "replay_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "replay_report.md").write_text(_render_replay_markdown(summary), encoding="utf-8")
    return out


def _render_replay_markdown(summary: dict[str, Any]) -> str:
    lines = ["# OCR4game Replay Report", ""]
    lines.extend(
        [
            f"- game_id: `{summary['game_id']}`",
            f"- task_id: `{summary['task_id']}`",
            f"- total events: `{summary['total_events']}`",
            f"- total evaluations: `{summary['total_evaluations']}`",
            "",
            "| Screenshot | Step | Anchor | Found | Confidence | Detail |",
            "|---|---|---|---|---:|---|",
        ]
    )
    for item in summary["results"]:
        lines.append(
            f"| {item.get('screenshot_path', '')} | {item.get('step_index', '')} | "
            f"{item.get('anchor_name', '')} | {item.get('found', '')} | "
            f"{item.get('confidence', '')} | {item.get('detail', '')} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="离线 replay OCR4game run 截图")
    parser.add_argument("--run", required=True, help="run 目录，如 runs/star_rail_20260101_120000")
    parser.add_argument("--step-index", type=int, help="只 replay 指定 step_index 的截图")
    parser.add_argument("--anchor", help="只 evaluate 指定 anchor")
    args = parser.parse_args(argv)

    try:
        out = replay_run(Path(args.run), step_index=args.step_index, anchor=args.anchor)
    except Exception as exc:
        print(f"replay 失败: {exc}", file=sys.stderr)
        return 1

    print(f"已生成: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
