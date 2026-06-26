"""工作流 when/if 条件求值。"""

from __future__ import annotations

from typing import Any

from ocr4game.workflow.context import RunContext


class ConditionError(ValueError):
    pass


def evaluate_condition(condition: Any, ctx: RunContext) -> bool:
    """求值条件表达式；None 视为 True。"""
    if condition is None:
        return True
    if isinstance(condition, bool):
        return condition
    if not isinstance(condition, dict):
        raise ConditionError(f"无效条件类型: {type(condition)!r}")

    if "all" in condition:
        items = condition["all"]
        if not isinstance(items, list):
            raise ConditionError("all 必须是列表")
        return all(evaluate_condition(item, ctx) for item in items)

    if "any" in condition:
        items = condition["any"]
        if not isinstance(items, list):
            raise ConditionError("any 必须是列表")
        return any(evaluate_condition(item, ctx) for item in items)

    if "not" in condition:
        return not evaluate_condition(condition["not"], ctx)

    if "anchor_visible" in condition:
        return _anchor_visible(str(condition["anchor_visible"]), ctx)

    if "anchor_missing" in condition:
        return not _anchor_visible(str(condition["anchor_missing"]), ctx)

    for key in ("var_eq", "var_ne", "var_gt", "var_gte", "var_lt", "var_lte"):
        if key in condition:
            return _compare_var(key, condition[key], ctx.vars)

    raise ConditionError(f"未知条件键: {list(condition.keys())}")


def _anchor_visible(anchor_name: str, ctx: RunContext) -> bool:
    if ctx.perception is None or ctx.capture is None:
        ctx.log.warning("条件求值缺少 perception/capture", anchor=anchor_name)
        return False
    frame = ctx.grab_frame()
    return ctx.perception.evaluate_anchor(frame, anchor_name).found


def _compare_var(op: str, spec: Any, vars: dict[str, Any]) -> bool:
    if not isinstance(spec, dict) or len(spec) != 1:
        raise ConditionError(f"{op} 需要单键 dict，如 {{sweep_times: 0}}")

    name, expected = next(iter(spec.items()))
    if name not in vars:
        return False
    actual = vars[name]

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
    raise ConditionError(f"未知比较: {op}")


def validate_condition_syntax(
    condition: Any,
    *,
    profile,
    path: str,
) -> list[str]:
    """离线校验条件结构，返回错误消息列表。"""
    errors: list[str] = []
    _walk_validate(condition, profile, path, errors)
    return errors


def _walk_validate(condition: Any, profile, path: str, errors: list[str]) -> None:
    if condition is None or isinstance(condition, bool):
        return
    if not isinstance(condition, dict):
        errors.append(f"{path}: 条件必须是 dict/bool")
        return

    if "all" in condition or "any" in condition:
        key = "all" if "all" in condition else "any"
        items = condition[key]
        if not isinstance(items, list):
            errors.append(f"{path}.{key}: 必须是列表")
            return
        for index, item in enumerate(items):
            _walk_validate(item, profile, f"{path}.{key}[{index}]", errors)
        return

    if "not" in condition:
        _walk_validate(condition["not"], profile, f"{path}.not", errors)
        return

    if "anchor_visible" in condition or "anchor_missing" in condition:
        key = "anchor_visible" if "anchor_visible" in condition else "anchor_missing"
        name = condition[key]
        if not isinstance(name, str) or name not in profile.anchors:
            errors.append(f"{path}.{key}: 未定义锚点 {name!r}")
        return

    for key in ("var_eq", "var_ne", "var_gt", "var_gte", "var_lt", "var_lte"):
        if key in condition:
            spec = condition[key]
            if not isinstance(spec, dict) or len(spec) != 1:
                errors.append(f"{path}.{key}: 需要单键 dict")
            return

    errors.append(f"{path}: 未知条件键 {list(condition.keys())}")
