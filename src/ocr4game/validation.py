"""配置与任务离线校验。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from ocr4game.config import (
    GameProfile,
    TaskConfig,
    TemplateAnchorConfig,
    load_task_config,
)
from ocr4game.games.base import GamePlugin
from ocr4game.perception.screen_state import rule_anchor_refs
from ocr4game.resources import game_assets_dir
from ocr4game.workflow.actions.base import build_default_registry
from ocr4game.workflow.conditions import validate_condition_syntax
from ocr4game.workflow.semantics import parse_action, parse_step_runtime
from ocr4game.workflow.vars import UndefinedVarError, merge_var_overrides, resolve_value


@dataclass(frozen=True)
class ValidationIssue:
    level: Literal["error", "warning"]
    message: str
    path: str = ""


def validate_game_profile(
    profile: GameProfile,
    *,
    strict_assets: bool = False,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not profile.window.title_contains:
        issues.append(
            ValidationIssue("warning", "window.title_contains 为空", "profile.window")
        )

    for name, anchor in profile.anchors.items():
        if isinstance(anchor, TemplateAnchorConfig):
            image_path = game_assets_dir(profile) / anchor.image
            if not image_path.is_file():
                level: Literal["error", "warning"] = "error" if strict_assets else "warning"
                issues.append(
                    ValidationIssue(
                        level,
                        f"模板文件不存在: {anchor.image}（请用 ocr4game-annotate 截取）",
                        f"profile.anchors.{name}",
                    )
                )

    issues.extend(_validate_content_profile(profile))

    return issues


def _validate_content_profile(profile: GameProfile) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for state_name, state in profile.screen_states.items():
        for group_name, rules in (
            ("require", state.require),
            ("optional", state.optional),
            ("reject", state.reject),
        ):
            for index, rule in enumerate(rules):
                for anchor_name in rule_anchor_refs(rule):
                    if anchor_name not in profile.anchors:
                        issues.append(
                            ValidationIssue(
                                "error",
                                f"screen_state 引用未定义锚点: {anchor_name}",
                                f"profile.screen_states.{state_name}.{group_name}[{index}]",
                            )
                        )
    for extractor_name, extractor in profile.content_extractors.items():
        if extractor.when_state and extractor.when_state not in profile.screen_states:
            issues.append(
                ValidationIssue(
                    "error",
                    f"content_extractor 引用未定义 screen_state: {extractor.when_state}",
                    f"profile.content_extractors.{extractor_name}.when_state",
                )
            )
        for field_name, field in extractor.fields.items():
            if field.anchor and field.anchor not in profile.anchors:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"content field 引用未定义锚点: {field.anchor}",
                        f"profile.content_extractors.{extractor_name}.fields.{field_name}",
                    )
                )
    return issues


def validate_task_config(
    profile: GameProfile,
    task: TaskConfig,
    *,
    registry=None,
    merged_vars: dict[str, Any] | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    vars = merge_var_overrides(task.vars, merged_vars)

    if registry is None:
        registry = build_default_registry(default_timeout_ms=10_000)

    for step in task.steps:
        step_path = f"steps.{step.id}"
        try:
            resolved = resolve_value(step.model_dump(), vars)
        except UndefinedVarError as exc:
            issues.append(
                ValidationIssue("error", str(exc), f"{step_path}.vars")
            )
            continue

        when = resolved.get("when")
        if when is not None:
            for message in validate_condition_syntax(when, profile=profile, path=f"{step_path}.when"):
                issues.append(ValidationIssue("error", message, step_path))

        try:
            runtime = parse_step_runtime(resolved, default_retry=0)
        except (AttributeError, TypeError, ValueError) as exc:
            issues.append(ValidationIssue("error", f"步骤运行参数无效: {exc}", step_path))
            continue

        for index, action in enumerate(runtime.actions):
            action_path = f"{step_path}.do[{index}]"
            issues.extend(_validate_action(profile, action, action_path, registry))

    return issues


def _validate_action(profile, action: dict, action_path: str, registry) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    try:
        parsed = parse_action(action)
    except ValueError as exc:
        issues.append(ValidationIssue("error", str(exc), action_path))
        return issues

    name = parsed.name
    params = parsed.params
    if name == "if":
        if not isinstance(params, dict):
            issues.append(ValidationIssue("error", "if 分支必须是 dict", action_path))
            return issues
        when = params.get("when")
        for message in validate_condition_syntax(
            when, profile=profile, path=f"{action_path}.if.when"
        ):
            issues.append(ValidationIssue("error", message, action_path))
        nested = params.get("do") or []
        if not isinstance(nested, list):
            issues.append(ValidationIssue("error", "if.do 必须是列表", action_path))
            return issues
        for index, nested_action in enumerate(nested):
            issues.extend(
                _validate_action(profile, nested_action, f"{action_path}.if.do[{index}]", registry)
            )
        return issues

    if registry.get(name) is None:
        issues.append(ValidationIssue("error", f"未知动作: {name}", action_path))

    if isinstance(params, dict) and "anchor" in params:
        anchor_name = params["anchor"]
        if anchor_name not in profile.anchors:
            issues.append(
                ValidationIssue("error", f"未定义的锚点: {anchor_name}", action_path)
            )
    return issues


def validate_task_file(
    profile: GameProfile,
    task_path: Path,
    *,
    plugin: GamePlugin | None = None,
    merged_vars: dict[str, Any] | None = None,
    strict_assets: bool = False,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not task_path.is_file():
        return [ValidationIssue("error", f"任务文件不存在: {task_path}")]

    try:
        task = load_task_config(task_path)
    except ValidationError as exc:
        return [ValidationIssue("error", f"任务 YAML 结构无效: {exc}")]

    registry = build_default_registry(default_timeout_ms=10_000)
    if plugin is not None:
        plugin.register_actions(registry)

    issues.extend(validate_game_profile(profile, strict_assets=strict_assets))
    if plugin is not None:
        issues.extend(
            ValidationIssue("warning", message, "profile.extensions")
            for message in plugin.validate_profile()
        )
    issues.extend(
        validate_task_config(
            profile,
            task,
            registry=registry,
            merged_vars=merged_vars,
        )
    )
    if plugin is not None:
        issues.extend(
            ValidationIssue("warning", message, "task.extensions")
            for message in plugin.validate_task(task)
        )
    return issues


def validate_run(
    profile: GameProfile,
    task_path: Path,
    *,
    plugin: GamePlugin | None = None,
    var_overrides: dict[str, Any] | None = None,
    strict_assets: bool = False,
) -> list[ValidationIssue]:
    return validate_task_file(
        profile,
        task_path,
        plugin=plugin,
        merged_vars=var_overrides,
        strict_assets=strict_assets,
    )


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.level == "error" for issue in issues)


def format_issues(issues: list[ValidationIssue]) -> str:
    lines: list[str] = []
    for issue in issues:
        prefix = "ERROR" if issue.level == "error" else "WARN"
        location = f" [{issue.path}]" if issue.path else ""
        lines.append(f"{prefix}{location}: {issue.message}")
    return "\n".join(lines)
