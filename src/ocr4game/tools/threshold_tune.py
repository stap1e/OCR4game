"""模板阈值标定 CLI：扫描匹配置信度并建议 threshold。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

from ocr4game.config import GameProfile, load_game_profile, load_global_config, load_yaml
from ocr4game.resources import game_profile_path
from ocr4game.tools.threshold import (
    ThresholdReport,
    evaluate_template_anchor,
    list_template_anchors,
    sweep_lines,
)
from ocr4game.workflow.context import RunContext


def _load_frame(frame_path: Path | None, ctx: RunContext | None) -> tuple[np.ndarray, str]:
    if frame_path is not None:
        frame = cv2.imread(str(frame_path))
        if frame is None:
            raise FileNotFoundError(f"无法读取图片: {frame_path}")
        return frame, str(frame_path)

    if ctx is None or ctx.capture is None:
        raise RuntimeError("未提供 --frame 且未绑定游戏窗口")
    return ctx.grab_frame(), "live-window"


def _update_threshold(profile_path: Path, anchor_name: str, threshold: float) -> None:
    data = load_yaml(profile_path)
    anchors = data.get("anchors") or {}
    anchor = anchors.get(anchor_name)
    if not isinstance(anchor, dict):
        raise KeyError(f"profile 中无锚点: {anchor_name}")
    if anchor.get("type", "template") != "template":
        raise TypeError(f"锚点 {anchor_name} 不是 template 类型")

    anchor["threshold"] = threshold
    profile = GameProfile.model_validate(data)
    with profile_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            profile.model_dump(mode="python"),
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def _print_report(
    report: ThresholdReport,
    *,
    frame_source: str,
    sweep: bool,
    apply: bool,
    profile_path: Path,
) -> None:
    print(f"anchor: {report.anchor}")
    print(f"frame: {frame_source}")
    print(f"template: {report.template_path}")
    print(f"confidence: {report.confidence:.4f}")
    print(f"current threshold: {report.current_threshold:.2f}")
    print(f"suggested threshold: {report.suggested_threshold:.2f}")
    print(f"center: {report.center}")

    if sweep:
        print("sweep:")
        for line in sweep_lines(report.confidence):
            print(line)

    if apply:
        _update_threshold(profile_path, report.anchor, report.suggested_threshold)
        print(f"已写入 profile: {report.anchor}.threshold = {report.suggested_threshold:.2f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="标定 template 锚点 threshold")
    parser.add_argument("--game", default="star_rail")
    parser.add_argument("--anchor", help="锚点名称（与 --all 二选一）")
    parser.add_argument("--all", action="store_true", help="标定 profile 中全部 template 锚点")
    parser.add_argument("--frame", type=Path, help="离线截图路径（不指定则从游戏窗口截屏）")
    parser.add_argument("--margin", type=float, default=0.03, help="建议 threshold = confidence - margin")
    parser.add_argument("--sweep", action="store_true", help="打印常见 threshold 档位是否匹配")
    parser.add_argument("--apply", action="store_true", help="将建议 threshold 写回 profile.yaml")
    args = parser.parse_args(argv)

    if not args.all and not args.anchor:
        parser.error("请指定 --anchor 或 --all")
    if args.all and args.anchor:
        parser.error("--anchor 与 --all 不能同时使用")

    profile = load_game_profile(args.game)
    anchor_names = list_template_anchors(profile) if args.all else [args.anchor or ""]

    ctx: RunContext | None = None
    if args.frame is None:
        from ocr4game.games.registry import get_plugin
        from ocr4game.runtime.binding import bind_runtime

        global_cfg = load_global_config()
        plugin = get_plugin(profile)
        ctx = RunContext(profile=profile, global_cfg=global_cfg)
        if not bind_runtime(ctx) or not plugin.preflight(ctx):
            print("未找到游戏窗口。请窗口化启动游戏，或使用 --frame 指定截图。", file=sys.stderr)
            return 1

    try:
        frame, frame_source = _load_frame(args.frame, ctx)
    except (FileNotFoundError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    profile_path = game_profile_path(args.game)
    exit_code = 0

    for index, anchor_name in enumerate(anchor_names):
        if index > 0:
            print("---")
        try:
            report = evaluate_template_anchor(
                profile,
                anchor_name,
                frame,
                margin=args.margin,
            )
        except (KeyError, TypeError, FileNotFoundError) as exc:
            print(f"跳过 {anchor_name}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        if not report.template_path.is_file():
            print(f"跳过 {anchor_name}: 模板不存在 {report.template_path}", file=sys.stderr)
            exit_code = 1
            continue

        _print_report(
            report,
            frame_source=frame_source,
            sweep=args.sweep,
            apply=args.apply,
            profile_path=profile_path,
        )

        if args.apply:
            profile = load_game_profile(args.game)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
