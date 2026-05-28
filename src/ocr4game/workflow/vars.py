"""任务 vars 插值：支持 {var_name} 引用。"""

from __future__ import annotations

import re
from typing import Any

_VAR_REF = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_VAR_SUB = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class UndefinedVarError(KeyError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"未定义的任务变量: {name}")


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
