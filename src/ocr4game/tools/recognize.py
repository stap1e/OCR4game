"""Offline image content-recognition CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2

from ocr4game.config import load_game_profile, load_global_config
from ocr4game.perception.fusion import Perception
from ocr4game.resources import runs_base_dir
from ocr4game.tools.anchor_eval import _IMAGE_SUFFIXES, discover_screenshots


def default_output_dir(game_id: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return runs_base_dir(load_global_config()) / f"{game_id}_recognize_{stamp}"


def recognize_image(game_id: str, image: Path) -> dict[str, Any]:
    profile = load_game_profile(game_id)
    frame = cv2.imread(str(image))
    if frame is None:
        raise FileNotFoundError(f"无法读取图片: {image}")
    snapshot = Perception(profile).snapshot(frame, image_path=str(image))
    return snapshot.to_dict()


def write_batch(results: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        stem = Path(result.get("image_path") or "image").stem
        (output_dir / f"{stem}.content.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    summary = {
        "num_images": len(results),
        "results": results,
    }
    summary_path = output_dir / "recognize_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = output_dir / "recognize_report.md"
    report_path.write_text(render_report(summary), encoding="utf-8")
    return {"summary": summary_path, "report": report_path}


def render_report(summary: dict[str, Any]) -> str:
    lines = ["# OCR4game Content Recognition", "", f"- num_images: `{summary['num_images']}`", ""]
    lines.append("| Image | Screen state | Confidence | Warnings |")
    lines.append("|---|---|---:|---|")
    for result in summary["results"]:
        state = result.get("screen_state") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(result.get("image_path") or ""),
                    str(state.get("state") or ""),
                    _fmt(state.get("confidence")),
                    "; ".join(result.get("warnings") or []),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="离线识别游戏截图中的 screen/content")
    parser.add_argument("--game", default="star_rail")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="单张截图")
    group.add_argument("--images", type=Path, help="截图目录")
    parser.add_argument("--json", action="store_true", help="单图模式输出 JSON")
    parser.add_argument("--output", type=Path, help="单图模式 JSON 输出路径")
    parser.add_argument("--output-dir", type=Path, help="批量输出目录")
    args = parser.parse_args(argv)

    try:
        if args.image:
            result = recognize_image(args.game, args.image)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                state = result.get("screen_state") or {}
                print(f"game={result['game_id']} image={result['image_path']}")
                print(f"screen_state={state.get('state')} confidence={_fmt(state.get('confidence'))}")
                for warning in result.get("warnings") or []:
                    print(f"warning: {warning}")
            return 0

        screenshots = [path for path in discover_screenshots(args.images) if path.suffix.lower() in _IMAGE_SUFFIXES]
        if not screenshots:
            raise FileNotFoundError(f"未找到截图: {args.images}")
        results = [recognize_image(args.game, path) for path in screenshots]
        out_dir = args.output_dir or default_output_dir(args.game)
        paths = write_batch(results, out_dir)
        for path in paths.values():
            print(f"已生成: {path}")
        return 0
    except Exception as exc:
        print(f"recognize 失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
