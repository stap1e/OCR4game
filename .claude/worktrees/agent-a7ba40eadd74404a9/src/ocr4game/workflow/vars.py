"""任务 vars 插值：支持 {var_name} 引用。"""

from __future__ import annotations

import re
from typing import Any

_VAR_REF = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_VAR_SUB = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_VAR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class UndefinedVarError(KeyError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"未定义的任务变量: {name}")


class InvalidVarAssignmentError(ValueError):
    pass


def resolve_value(value: Any, vars: dict[str, Any]) -> Any:
    """递归解析 value 中的 {var} 引用。"""
    if isinstance(value, str):
        return _resolve_string(value, vars)
    if isinstance(value, dict):
        return {key: resolve_value(item, vars) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_value(item, vars) for item in value]
    return value


def _resolve_string(text: str, vars: dict[str, Any]) -> Any:
    stripped = text.strip()
    exact = _VAR_REF.match(stripped)
    if exact:
        name = exact.group(1)
        if name not in vars:
            raise UndefinedVarError(name)
        return vars[name]

    if "{" not in text:
        return text

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in vars:
            raise UndefinedVarError(name)
        return str(vars[name])

    return _VAR_SUB.sub(repl, text)


def coerce_var_value(text: str) -> Any:
    """将 CLI/YAML 文本转为 Python 值。"""
    stripped = text.strip()
    lower = stripped.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in ("null", "none", "~"):
        return None
    try:
        if any(ch in stripped for ch in (".", "e", "E")):
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


def parse_var_assignment(raw: str) -> tuple[str, Any]:
    """解析 KEY=VALUE 赋值（用于 --var）。"""
    if "=" not in raw:
        raise InvalidVarAssignmentError(f"无效 --var 格式: {raw!r}，应为 KEY=VALUE")

    key, value = raw.split("=", 1)
    key = key.strip()
    if not key or not _VAR_NAME.match(key):
        raise InvalidVarAssignmentError(f"无效变量名: {key!r}")

    return key, coerce_var_value(value)


def merge_var_overrides(
    base: dict[str, Any],
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(base)
    if overrides:
        merged.update(overrides)
    return merged
