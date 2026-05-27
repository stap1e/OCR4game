"""CLI 入口：运行日常任务工作流。"""

from __future__ import annotations

import argparse
import sys

import structlog

from ocr4game.config import GameProfile, GlobalConfig, load_game_profile, load_global_config
from ocr4game.games.registry import get_plugin
from ocr4game.resources import game_task_path
from ocr4game.runtime.binding import bind_runtime
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.engine import WorkflowEngine
from ocr4game.workflow.errors import StepFailed


def _configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OCR4game — 游戏视觉自动化")
    parser.add_argument(
        "--game",
        default="star_rail",
        help="游戏 ID（默认 star_rail）",
    )
    parser.add_argument(
        "--task",
        default="daily",
        help="任务名，对应 tasks/<name>.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅检查窗口与配置，不执行工作流",
    )
    args = parser.parse_args(argv)

    global_cfg = load_global_config()
    _configure_logging(global_cfg.log_level)

    log = structlog.get_logger()
    profile = load_game_profile(args.game)
    plugin = get_plugin(profile)

    ctx = RunContext(profile=profile, global_cfg=global_cfg, log=log)
    if not bind_runtime(ctx) or not plugin.preflight(ctx):
        log.error("预检失败，请确认游戏已窗口化启动")
        return 1

    if args.dry_run:
        log.info("dry-run 通过", game=args.game)
        return 0

    task_path = game_task_path(profile, args.task)
    if not task_path.exists():
        log.error("任务文件不存在", path=str(task_path))
        return 1

    engine = WorkflowEngine(ctx, plugin=plugin)
    try:
        engine.run_task(task_path)
        log.info("任务完成", task=args.task)
        return 0
    except StepFailed as exc:
        log.error("任务中止", error=str(exc), step=exc.step_id)
        if ctx.window and ctx.capture and ctx.input:
            frame = ctx.grab_frame()
            plugin.on_step_failure(ctx, exc.step_id, frame)
        return 2


if __name__ == "__main__":
    sys.exit(main())
