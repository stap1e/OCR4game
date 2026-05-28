"""基础动作注册与执行。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ocr4game.workflow.context import RunContext
from ocr4game.workflow.errors import StepFailed

ActionHandler = Callable[[RunContext, str, Any], bool]


class ActionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, name: str, handler: ActionHandler) -> None:
        self._handlers[name] = handler

    def get(self, name: str) -> ActionHandler | None:
        return self._handlers.get(name)


def build_default_registry(*, default_timeout_ms: int) -> ActionRegistry:
    registry = ActionRegistry()

    from ocr4game.workflow.actions.anchors import register_anchor_handlers
    from ocr4game.workflow.actions.basic import register_basic_handlers

    register_basic_handlers(registry)
    register_anchor_handlers(registry, default_timeout_ms=default_timeout_ms)
    return registry


class ActionExecutor:
    def __init__(self, ctx: RunContext, registry: ActionRegistry) -> None:
        self._ctx = ctx
        self._registry = registry

    def execute(self, step_id: str, action: dict[str, Any]) -> bool:
        if len(action) != 1:
            raise StepFailed(step_id, f"无效动作（需为单键 dict）: {action!r}")

        name, raw_params = next(iter(action.items()))
        params = raw_params if isinstance(raw_params, dict) else raw_params
        optional = bool(params.get("optional", False)) if isinstance(params, dict) else False
        handler = self._registry.get(name)
        if handler is None:
            raise StepFailed(step_id, f"未知动作: {name}")

        try:
            return handler(self._ctx, step_id, params)
        except StepFailed:
            if optional:
                self._ctx.log.info("可选步骤跳过", step=step_id, action=name)
                return True
            frame = self._ctx.grab_frame()
            path = self._ctx.save_failure_shot(step_id, frame)
            self._ctx.log.error("步骤失败", step=step_id, screenshot=str(path))
            raise
        except Exception as exc:
            if optional:
                self._ctx.log.info("可选步骤异常", step=step_id, error=str(exc))
                return True
            raise StepFailed(step_id, str(exc)) from exc
