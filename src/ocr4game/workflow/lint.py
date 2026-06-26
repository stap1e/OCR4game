"""Static workflow lint rules."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ocr4game.config import GameProfile, TaskConfig, load_task_config
from ocr4game.games.base import GamePlugin
from ocr4game.validation import ValidationIssue, validate_task_file
from ocr4game.workflow.actions.base import build_default_registry
from ocr4game.workflow.semantics import ParsedAction, parse_action, parse_step_runtime
from ocr4game.workflow.vars import UndefinedVarError, merge_var_overrides, resolve_value

_VAR_SUB = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_LOOP_MAX_WARNING = 100
_RETRY_WARNING = 10
_WAIT_WARNING_MS = 120_000
_RECOVERY_ACTIONS = {"log", "wait", "wait_for", "assert_window"}
_CLICK_ACTIONS = {"click_template", "click_ocr"}


def lint_task_file(
    profile: GameProfile,
    task_path: Path,
    *,
    plugin: GamePlugin | None = None,
    var_overrides: dict[str, Any] | None = None,
    include_validation: bool = True,
    strict_assets: bool = False,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if include_validation:
        issues.extend(
            validate_task_file(
                profile,
                task_path,
                plugin=plugin,
                merged_vars=var_overrides,
                strict_assets=strict_assets,
            )
        )

    if not task_path.is_file():
        return issues or [ValidationIssue("error", f"任务文件不存在: {task_path}")]

    try:
        task = load_task_config(task_path)
    except ValidationError as exc:
        if not include_validation:
            issues.append(ValidationIssue("error", f"任务 YAML 结构无效: {exc}"))
        return issues

    registry = build_default_registry(default_timeout_ms=10_000)
    if plugin is not None:
        plugin.register_actions(registry)
    issues.extend(lint_task_config(profile, task, registry=registry, var_overrides=var_overrides))
    return issues


def lint_task_config(
    profile: GameProfile,
    task: TaskConfig,
    *,
    registry=None,
    var_overrides: dict[str, Any] | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    vars = merge_var_overrides(task.vars, var_overrides)
    raw_steps = [step.model_dump() for step in task.steps]

    issues.extend(_lint_screen_states(profile))
    issues.extend(_lint_unused_vars(task, raw_steps))

    for step in task.steps:
        step_path = f"steps.{step.id}"
        raw_step = step.model_dump()
        try:
            resolved = resolve_value(raw_step, vars)
        except UndefinedVarError:
            continue

        issues.extend(_lint_static_condition(resolved.get("when"), vars, f"{step_path}.when"))

        try:
            runtime = parse_step_runtime(resolved, default_retry=0)
        except (AttributeError, TypeError, ValueError):
            continue

        if runtime.loop_max is not None:
            if runtime.loop_max <= 0:
                issues.append(ValidationIssue("error", "loop.max 必须大于 0", f"{step_path}.loop"))
            elif runtime.loop_max > _LOOP_MAX_WARNING:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"loop.max 过大: {runtime.loop_max}（建议 <= {_LOOP_MAX_WARNING}）",
                        f"{step_path}.loop",
                    )
                )
        if runtime.retry < 0:
            issues.append(ValidationIssue("error", "retry 不能为负数", f"{step_path}.retry"))
        elif runtime.retry > _RETRY_WARNING:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"retry 过大: {runtime.retry}（建议 <= {_RETRY_WARNING}）",
                    f"{step_path}.retry",
                )
            )

        parsed_actions = _parse_actions(runtime.actions)
        issues.extend(_lint_actions(parsed_actions, f"{step_path}.do", vars))
        for index, parsed in enumerate(parsed_actions):
            if parsed is None or parsed.name != "if" or not isinstance(parsed.params, dict):
                continue
            issues.extend(
                _lint_static_condition(
                    parsed.params.get("when"), vars, f"{step_path}.do[{index}].if.when"
                )
            )
            nested = parsed.params.get("do") or []
            if isinstance(nested, list):
                issues.extend(
                    _lint_actions(_parse_actions(nested), f"{step_path}.do[{index}].if.do", vars)
                )
    return issues


def _lint_screen_states(profile: GameProfile) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for state_name, state in profile.screen_states.items():
        required_visible = _collect_anchor_rule_values(state.require, "anchor_visible")
        rejected_visible = _collect_anchor_rule_values(state.reject, "anchor_visible")
        conflicts = sorted(required_visible & rejected_visible)
        for anchor in conflicts:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"screen_state 同时 require/reject 同一可见锚点，可能永远无法满足: {anchor}",
                    f"profile.screen_states.{state_name}",
                )
            )
    return issues


def _collect_anchor_rule_values(rules: list[dict[str, Any]], key: str) -> set[str]:
    values: set[str] = set()
    for rule in rules:
        values.update(_collect_anchor_rule_value(rule, key))
    return values


def _collect_anchor_rule_value(rule: Any, key: str) -> set[str]:
    if not isinstance(rule, dict):
        return set()
    if key in rule and isinstance(rule[key], str):
        return {rule[key]}
    values: set[str] = set()
    for nested_key in ("all", "any"):
        if isinstance(rule.get(nested_key), list):
            for item in rule[nested_key]:
                values.update(_collect_anchor_rule_value(item, key))
    if "not" in rule:
        values.update(_collect_anchor_rule_value(rule["not"], key))
    return values


def _lint_unused_vars(task: TaskConfig, raw_steps: list[dict[str, Any]]) -> list[ValidationIssue]:
    used: set[str] = set()
    for step in raw_steps:
        used.update(_collect_var_refs(step))
    return [
        ValidationIssue("warning", f"未使用的任务变量: {name}", f"vars.{name}")
        for name in sorted(set(task.vars) - used)
    ]


def _collect_var_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        refs.update(_VAR_SUB.findall(value))
    elif isinstance(value, dict):
        for item in value.values():
            refs.update(_collect_var_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_collect_var_refs(item))
    return refs


def _parse_actions(actions: list[dict[str, Any]]) -> list[ParsedAction | None]:
    parsed: list[ParsedAction | None] = []
    for action in actions:
        try:
            parsed.append(parse_action(action))
        except ValueError:
            parsed.append(None)
    return parsed


def _lint_actions(
    parsed_actions: list[ParsedAction | None], path: str, vars: dict[str, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    previous_click: tuple[str, str] | None = None

    for index, parsed in enumerate(parsed_actions):
        if parsed is None:
            previous_click = None
            continue
        action_path = f"{path}[{index}]"
        params = parsed.params if isinstance(parsed.params, dict) else {}

        if (
            params.get("optional") is True
            and parsed.name not in _RECOVERY_ACTIONS
            and not _has_recovery_nearby(parsed_actions, index)
        ):
            issues.append(
                ValidationIssue(
                    "warning",
                    "optional action 后缺少 log/wait_for/assert_window 等诊断或恢复动作",
                    action_path,
                )
            )

        issues.extend(_lint_wait(parsed.name, params, action_path))

        if parsed.name in _CLICK_ACTIONS:
            anchor = params.get("anchor")
            current = (parsed.name, str(anchor)) if anchor else None
            if current is not None and current == previous_click:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"同一 step 内连续重复点击同一锚点: {anchor}",
                        action_path,
                    )
                )
            previous_click = current
        elif parsed.name != "if":
            previous_click = None

        if parsed.name == "if" and isinstance(parsed.params, dict):
            issues.extend(_lint_static_condition(parsed.params.get("when"), vars, f"{action_path}.when"))
    return issues


def _has_recovery_nearby(actions: list[ParsedAction | None], index: int) -> bool:
    return _has_named_action(actions[index + 1 :], _RECOVERY_ACTIONS) or _has_named_action(
        actions[:index], {"log", "wait_for", "assert_window"}
    )


def _has_named_action(actions: list[ParsedAction | None], names: set[str]) -> bool:
    return any(action is not None and action.name in names for action in actions)


def _lint_wait(name: str, params: dict[str, Any], path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    field = "ms" if name == "wait" else "timeout_ms" if name == "wait_for" else None
    if field is None or field not in params:
        return issues
    try:
        value = int(params[field])
    except (TypeError, ValueError):
        return [ValidationIssue("error", f"{field} 必须是整数毫秒", path)]
    if value <= 0:
        issues.append(ValidationIssue("error", f"{field} 必须大于 0", path))
    elif value > _WAIT_WARNING_MS:
        issues.append(
            ValidationIssue("warning", f"{field} 异常偏大: {value}ms", path)
        )
    return issues


def _lint_static_condition(condition: Any, vars: dict[str, Any], path: str) -> list[ValidationIssue]:
    if condition is None:
        return []
    result = _eval_static_condition(condition, vars)
    if result is False:
        return [ValidationIssue("warning", "condition 明显永远为 false", path)]
    return []


def _eval_static_condition(condition: Any, vars: dict[str, Any]) -> bool | None:
    if isinstance(condition, bool):
        return condition
    if not isinstance(condition, dict):
        return None
    if "all" in condition and isinstance(condition["all"], list):
        values = [_eval_static_condition(item, vars) for item in condition["all"]]
        if any(value is False for value in values):
            return False
        if values and all(value is True for value in values):
            return True
        return None
    if "any" in condition and isinstance(condition["any"], list):
        values = [_eval_static_condition(item, vars) for item in condition["any"]]
        if not values:
            return False
        if any(value is True for value in values):
            return True
        if all(value is False for value in values):
            return False
        return None
    if "not" in condition:
        value = _eval_static_condition(condition["not"], vars)
        return None if value is None else not value
    for key in ("var_eq", "var_ne", "var_gt", "var_gte", "var_lt", "var_lte"):
        if key in condition:
            return _eval_var_compare(key, condition[key], vars)
    return None


def _eval_var_compare(op: str, spec: Any, vars: dict[str, Any]) -> bool | None:
    if not isinstance(spec, dict) or len(spec) != 1:
        return None
    name, expected = next(iter(spec.items()))
    if name not in vars:
        return False
    actual = vars[name]
    try:
        if op == "var_eq":
            return actual == expected
        if op == "var_ne":
            return actual != expected
        if op == "var_gt":
            return actual > expected
        if op == "var_gte":
            return actual >= expected
        if op == "var_lt":
            return actual < expected
        if op == "var_lte":
            return actual <= expected
    except TypeError:
        return None
    return None
