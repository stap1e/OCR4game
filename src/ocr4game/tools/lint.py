"""Workflow static lint CLI."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from ocr4game.config import load_game_profile
from ocr4game.games.registry import get_plugin
from ocr4game.resources import game_task_path
from ocr4game.validation import format_issues, has_errors
from ocr4game.workflow.lint import lint_task_file
from ocr4game.workflow.vars import InvalidVarAssignmentError, parse_var_assignment


def _parse_var_overrides(raw_vars: list[str], parser: argparse.ArgumentParser) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    try:
        for raw in raw_vars:
            key, value = parse_var_assignment(raw)
            overrides[key] = value
    except InvalidVarAssignmentError as exc:
        parser.error(str(exc))
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="静态 lint OCR4game workflow")
    parser.add_argument("--game", default="star_rail", help="游戏 ID（默认 star_rail）")
    parser.add_argument("--task", default="daily", help="任务名，对应 tasks/<name>.yaml")
    parser.add_argument("--strict", action="store_true", help="warning 也视为失败")
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="覆盖任务 vars，可多次指定",
    )
    args = parser.parse_args(argv)
    var_overrides = _parse_var_overrides(args.var, parser)

    try:
        profile = load_game_profile(args.game)
        plugin = get_plugin(profile)
        task_path = game_task_path(profile, args.task)
        issues = lint_task_file(
            profile,
            task_path,
            plugin=plugin,
            var_overrides=var_overrides or None,
            strict_assets=args.strict,
        )
    except Exception as exc:
        print(f"lint 失败: {exc}", file=sys.stderr)
        return 1

    if issues:
        print(format_issues(issues))
    else:
        print(f"lint 通过: game={args.game} task={args.task}")

    if has_errors(issues):
        return 1
    if args.strict and any(issue.level == "warning" for issue in issues):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
