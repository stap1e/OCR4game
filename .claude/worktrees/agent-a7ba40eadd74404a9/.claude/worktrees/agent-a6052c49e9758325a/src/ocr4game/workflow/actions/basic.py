"""简单动作处理器。"""

from __future__ import annotations

from typing import Any

from ocr4game.workflow.actions.base import ActionRegistry
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.errors import StepFailed


def _log(ctx: RunContext, step_id: str, params: Any) -> bool:
    msg = params if isinstance(params, str) else params.get("msg", "")
    ctx.log.info("workflow", step=step_id, msg=msg)
    return True


def _assert_window(ctx: RunContext, step_id: str, _params: Any) -> bool:
    if ctx.window is None:
        raise StepFailed(step_id, "游戏窗口未找到")
    return True


def _wait(ctx: RunContext, _step_id: str, params: Any) -> bool:
    ms = int(params.get("ms", 500))
    assert ctx.input is not None
    ctx.input.sleep_ms(ms)
    return True


def register_basic_handlers(registry: ActionRegistry) -> None:
    registry.register("log", _log)
    registry.register("assert_window", _assert_window)
    registry.register("wait", _wait)
