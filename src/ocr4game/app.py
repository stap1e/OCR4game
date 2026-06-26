"""CLI 入口：运行日常任务工作流。"""

from __future__ import annotations

import argparse
import sys

import structlog

from ocr4game import __version__
from ocr4game.config import load_game_profile, load_global_config
from ocr4game.games.registry import (
    discover_configured_games,
    get_plugin,
    get_plugin_spec,
    list_registered_games,
)
from ocr4game.resources import game_task_path
from ocr4game.validation import format_issues, has_errors, validate_run
from ocr4game.workflow.lint import lint_task_file
from ocr4game.workflow.vars import InvalidVarAssignmentError, parse_var_assignment


def _configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )


def _parse_var_overrides(raw_vars: list[str], parser: argparse.ArgumentParser) -> dict:
    overrides: dict = {}
    try:
        for raw in raw_vars:
            key, value = parse_var_assignment(raw)
            overrides[key] = value
    except InvalidVarAssignmentError as exc:
        parser.error(str(exc))
    return overrides


def _report_validation(log, issues, *, strict: bool) -> int:
    for line in format_issues(issues).splitlines():
        if line.startswith("ERROR"):
            log.error("校验", detail=line)
        else:
            log.warning("校验", detail=line)

    if has_errors(issues):
        return 1
    if strict and any(issue.level == "warning" for issue in issues):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OCR4game — 游戏视觉自动化")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
        help="离线校验 + 窗口预检，不执行任务",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="仅离线校验 profile 与任务（无需启动游戏）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：缺模板等资源也视为失败",
    )
    parser.add_argument(
        "--list-games",
        action="store_true",
        help="列出已注册与已配置的游戏 ID",
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="覆盖任务 vars，可多次指定（如 --var sweep_times=3）",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="覆盖 global.yaml 中的 log_level",
    )
    args = parser.parse_args(argv)

    if args.list_games:
        registered = list_registered_games()
        configured = discover_configured_games()
        print("已注册插件:")
        for game_id in registered:
            spec = get_plugin_spec(game_id)
            label = spec.display_name or game_id
            print(f"  {game_id} — {label} [{spec.source}]")
        print("已配置目录:", ", ".join(configured) or "(无)")
        unregistered = sorted(set(configured) - set(registered))
        if unregistered:
            print("未注册插件（需在 games/registry.py 中注册）:", ", ".join(unregistered))
        return 0

    var_overrides = _parse_var_overrides(args.var, parser)

    global_cfg = load_global_config()
    log_level = args.log_level or global_cfg.log_level
    _configure_logging(log_level)
    log = structlog.get_logger()

    try:
        profile = load_game_profile(args.game)
        plugin = get_plugin(profile)
    except (KeyError, FileNotFoundError, Exception) as exc:
        log.error("加载游戏配置失败", game=args.game, error=str(exc))
        return 1

    task_path = game_task_path(profile, args.task)

    if args.validate or args.dry_run:
        issues = validate_run(
            profile,
            task_path,
            plugin=plugin,
            var_overrides=var_overrides or None,
            strict_assets=args.strict,
        )
        if args.validate and args.strict:
            issues = lint_task_file(
                profile,
                task_path,
                plugin=plugin,
                var_overrides=var_overrides or None,
                include_validation=False,
            ) + issues
        code = _report_validation(log, issues, strict=args.strict)
        if code != 0:
            return code
        if args.validate:
            log.info("校验通过", game=args.game, task=args.task)
            return 0

    if args.dry_run:
        from ocr4game.runtime.binding import bind_runtime
        from ocr4game.workflow.context import RunContext

        ctx = RunContext(profile=profile, global_cfg=global_cfg, log=log)
        if not bind_runtime(ctx) or not plugin.preflight(ctx):
            log.error("窗口预检失败，请确认游戏已窗口化启动")
            return 1
        log.info("dry-run 通过", game=args.game, task=args.task, vars=var_overrides or None)
        return 0

    from ocr4game.runtime.binding import bind_runtime
    from ocr4game.runtime.trace import TraceLogger
    from ocr4game.workflow.context import RunContext
    from ocr4game.workflow.engine import WorkflowEngine
    from ocr4game.workflow.errors import RunTimeout, StepFailed

    issues = validate_run(
        profile,
        task_path,
        plugin=plugin,
        var_overrides=var_overrides or None,
        strict_assets=args.strict,
    )
    if has_errors(issues):
        _report_validation(log, issues, strict=False)
        return 1

    ctx = RunContext(profile=profile, global_cfg=global_cfg, log=log)
    if not bind_runtime(ctx) or not plugin.preflight(ctx):
        log.error("预检失败，请确认游戏已窗口化启动")
        return 1

    if var_overrides:
        log.info("CLI 覆盖 vars", **var_overrides)

    ctx.ensure_run_dir()
    ctx.trace = TraceLogger(ctx.run_dir, profile.game_id, args.task, logger=log)
    engine = WorkflowEngine(ctx, plugin=plugin)
    try:
        engine.run_task(task_path, var_overrides=var_overrides or None)
        log.info("任务完成", task=args.task)
        return 0
    except RunTimeout as exc:
        log.error("任务超时", max_minutes=exc.max_minutes)
        return 2
    except StepFailed as exc:
        log.error("任务中止", error=str(exc), step=exc.step_id)
        if ctx.window and ctx.capture and ctx.input:
            frame = ctx.grab_frame()
            plugin.on_step_failure(ctx, exc.step_id, frame)
        return 2
    finally:
        ctx.trace.close()


if __name__ == "__main__":
    sys.exit(main())
