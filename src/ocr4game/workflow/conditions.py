"""工作流 when/if 条件求值。"""

from __future__ import annotations

from typing import Any

from ocr4game.workflow.context import RunContext


class ConditionError(ValueError):
    pass


def evaluate_condition(condition: Any, ctx: RunContext) -> bool:
    """求值条件表达式；None 视为 True。"""
    return _evaluate_condition(condition, ctx, {})


def _evaluate_condition(condition: Any, ctx: RunContext, cache: dict[str, Any]) -> bool:
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
        return all(_evaluate_condition(item, ctx, cache) for item in items)

    if "any" in condition:
        items = condition["any"]
        if not isinstance(items, list):
            raise ConditionError("any 必须是列表")
        return any(_evaluate_condition(item, ctx, cache) for item in items)

    if "not" in condition:
        return not _evaluate_condition(condition["not"], ctx, cache)

    if "anchor_visible" in condition:
        return _anchor_visible(str(condition["anchor_visible"]), ctx, cache)

    if "anchor_missing" in condition:
        return not _anchor_visible(str(condition["anchor_missing"]), ctx, cache)

    if "screen_state" in condition:
        return _screen_state(str(condition["screen_state"]), ctx, cache)

    if "ocr_contains" in condition:
        return _ocr_contains(condition["ocr_contains"], ctx, cache)

    for key in ("content_eq", "content_ne", "content_gt", "content_gte", "content_lt", "content_lte"):
        if key in condition:
            return _compare_content(key, condition[key], ctx, cache)

    for key in ("var_eq", "var_ne", "var_gt", "var_gte", "var_lt", "var_lte"):
        if key in condition:
            return _compare_var(key, condition[key], ctx.vars)

    raise ConditionError(f"未知条件键: {list(condition.keys())}")


def _frame(ctx: RunContext, cache: dict[str, Any]):
    if "frame" not in cache:
        if ctx.capture is None:
            raise ConditionError("条件求值缺少 capture")
        cache["frame"] = ctx.grab_frame()
    return cache["frame"]


def _anchor_visible(anchor_name: str, ctx: RunContext, cache: dict[str, Any]) -> bool:
    if ctx.perception is None or ctx.capture is None:
        ctx.log.warning("条件求值缺少 perception/capture", anchor=anchor_name)
        return False
    return ctx.perception.evaluate_anchor(_frame(ctx, cache), anchor_name).found


def _snapshot(ctx: RunContext, cache: dict[str, Any]) -> dict[str, Any] | None:
    if "snapshot" in cache:
        return cache["snapshot"]
    if ctx.perception is None or ctx.capture is None:
        ctx.log.warning("条件求值缺少 perception/capture")
        cache["snapshot"] = None
        return None
    frame = _frame(ctx, cache)
    try:
        snapshot = ctx.perception.snapshot(frame)
    except AttributeError:
        snapshot = None
    cache["snapshot"] = snapshot.to_dict() if hasattr(snapshot, "to_dict") else snapshot
    return cache["snapshot"]


def _screen_state(expected: str, ctx: RunContext, cache: dict[str, Any]) -> bool:
    snapshot = _snapshot(ctx, cache)
    if snapshot is None:
        return False
    state = snapshot.get("screen_state") or {}
    return state.get("state") == expected


def _ocr_contains(spec: Any, ctx: RunContext, cache: dict[str, Any]) -> bool:
    text = spec.get("text") if isinstance(spec, dict) else spec
    if text is None:
        return False
    snapshot = _snapshot(ctx, cache)
    if snapshot is not None:
        return any(str(text) in item.get("text", "") for item in snapshot.get("texts", []))
    if ctx.perception is None or ctx.capture is None:
        return False
    try:
        return any(str(text) in hit.text for hit in ctx.perception.read_texts(_frame(ctx, cache)))
    except Exception:
        return False


def _compare_content(op: str, spec: Any, ctx: RunContext, cache: dict[str, Any]) -> bool:
    if not isinstance(spec, dict) or "field" not in spec or "value" not in spec:
        raise ConditionError(f"{op} 需要 field/value")
    snapshot = _snapshot(ctx, cache)
    if snapshot is None:
        return False
    actual = _get_field(snapshot.get("extracted") or {}, str(spec["field"]))
    expected = spec["value"]
    try:
        if op == "content_eq":
            return actual == expected
        if op == "content_ne":
            return actual != expected
        if op == "content_gt":
            return actual > expected
        if op == "content_gte":
            return actual >= expected
        if op == "content_lt":
            return actual < expected
        if op == "content_lte":
            return actual <= expected
    except TypeError:
        return False
    raise ConditionError(f"未知内容比较: {op}")


def _get_field(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


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

    if "screen_state" in condition:
        name = condition["screen_state"]
        if not isinstance(name, str) or name not in profile.screen_states:
            errors.append(f"{path}.screen_state: 未定义 screen_state {name!r}")
        return

    if "ocr_contains" in condition:
        spec = condition["ocr_contains"]
        if not isinstance(spec, str) and not (isinstance(spec, dict) and isinstance(spec.get("text"), str)):
            errors.append(f"{path}.ocr_contains: 需要字符串或包含 text 的 dict")
        return

    for key in ("content_eq", "content_ne", "content_gt", "content_gte", "content_lt", "content_lte"):
        if key in condition:
            _validate_content_compare(key, condition[key], profile, path, errors)
            return

    for key in ("var_eq", "var_ne", "var_gt", "var_gte", "var_lt", "var_lte"):
        if key in condition:
            spec = condition[key]
            if not isinstance(spec, dict) or len(spec) != 1:
                errors.append(f"{path}.{key}: 需要单键 dict")
            return

    errors.append(f"{path}: 未知条件键 {list(condition.keys())}")


def _validate_content_compare(key: str, spec: Any, profile, path: str, errors: list[str]) -> None:
    if not isinstance(spec, dict) or "field" not in spec or "value" not in spec:
        errors.append(f"{path}.{key}: 需要 field/value")
        return
    field = spec["field"]
    if not isinstance(field, str) or len(field.split(".")) != 2:
        errors.append(f"{path}.{key}.field: 需要 extractor.field 格式")
        return
    extractor_name, field_name = field.split(".")
    extractor = profile.content_extractors.get(extractor_name)
    if extractor is None or field_name not in extractor.fields:
        errors.append(f"{path}.{key}.field: 未定义 content field {field!r}")
