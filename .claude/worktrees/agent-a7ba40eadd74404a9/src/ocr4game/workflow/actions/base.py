"""基础动作注册与执行。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ocr4game.workflow.context import RunContext
from ocr4game.workflow.errors import StepFailed
from ocr4game.workflow.semantics import parse_action

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

    def execute(
        self,
        step_id: str,
        action: dict[str, Any],
        *,
        step_index: int | None = None,
        action_index: int | None = None,
        retry_count: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        try:
            parsed = parse_action(action)
        except ValueError as exc:
            raise StepFailed(step_id, str(exc)) from exc

        params = parsed.params
        optional = bool(params.get("optional", False)) if isinstance(params, dict) else False
        anchor_name = params.get("anchor") if isinstance(params, dict) else None
        handler = self._registry.get(parsed.name)
        if handler is None:
            raise StepFailed(step_id, f"未知动作: {parsed.name}")

        started_at = time.monotonic()
        trace_base = {
            "step_index": step_index,
            "step_name": step_id,
            "action_index": action_index,
            "action_type": parsed.name,
            "retry_count": retry_count,
            "anchor_name": anchor_name,
            "extra": extra or {},
        }
        self._ctx.trace.log("action_started", status="started", **trace_base)

        try:
            result = handler(self._ctx, step_id, params)
            self._ctx.trace.log(
                "action_finished",
                status="success",
                elapsed_ms=_elapsed_ms(started_at),
                **trace_base,
            )
            return result
        except StepFailed as exc:
            if optional:
                self._ctx.trace.log(
                    "action_optional_failed",
                    status="optional_failed",
                    message=str(exc),
                    elapsed_ms=_elapsed_ms(started_at),
                    **trace_base,
                )
                self._ctx.log.info("可选步骤跳过", step=step_id, action=parsed.name)
                return True
            frame = self._ctx.grab_frame()
            path = self._ctx.save_failure_shot(step_id, frame)
            screenshot_path = self._ctx.run_relative_path(path)
            self._ctx.trace.log(
                "action_failed",
                status="failed",
                message=str(exc),
                elapsed_ms=_elapsed_ms(started_at),
                screenshot_path=screenshot_path,
                **trace_base,
            )
            self._ctx.log.error("步骤失败", step=step_id, screenshot=str(path))
            raise
        except Exception as exc:
            if optional:
                self._ctx.trace.log(
                    "action_optional_failed",
                    status="optional_failed",
                    message=str(exc),
                    elapsed_ms=_elapsed_ms(started_at),
                    **trace_base,
                )
                self._ctx.log.info("可选步骤异常", step=step_id, error=str(exc))
                return True
            self._ctx.trace.log(
                "action_failed",
                status="failed",
                message=str(exc),
                elapsed_ms=_elapsed_ms(started_at),
                **trace_base,
            )
            raise StepFailed(step_id, str(exc)) from exc


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
