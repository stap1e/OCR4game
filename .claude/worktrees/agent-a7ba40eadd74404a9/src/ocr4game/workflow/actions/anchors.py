"""锚点相关动作处理器。"""

from __future__ import annotations

import time
from typing import Any

from ocr4game.perception.diagnostics import diagnostics_from_anchor_result
from ocr4game.workflow.actions.base import ActionRegistry
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.errors import StepFailed


def _wait_for_anchor(ctx: RunContext, step_id: str, params: Any, *, default_timeout_ms: int) -> bool:
    anchor = params.get("anchor", "")
    timeout_ms = int(params.get("timeout_ms", default_timeout_ms))
    deadline = time.time() + timeout_ms / 1000.0

    while time.time() < deadline:
        frame = ctx.grab_frame()
        assert ctx.perception is not None
        result = ctx.perception.evaluate_anchor(frame, anchor)
        if result.found:
            ctx.trace.log(
                "anchor_evaluated",
                step_name=step_id,
                action_type="wait_for",
                status="success",
                **_anchor_trace_kwargs(ctx, frame, anchor, result),
            )
            return True
        assert ctx.input is not None
        ctx.input.sleep_ms(200)

    raise StepFailed(step_id, f"等待锚点超时: {anchor}")


def _click_anchor(ctx: RunContext, step_id: str, params: Any, *, kind: str) -> bool:
    anchor = params.get("anchor", "")
    frame = ctx.grab_frame()
    assert ctx.perception is not None
    result = ctx.perception.evaluate_anchor(frame, anchor)

    if not result.found:
        ctx.trace.log(
            "anchor_evaluated",
            step_name=step_id,
            action_type=f"click_{kind}",
            status="failed",
            message=f"未找到锚点: {anchor}",
            **_anchor_trace_kwargs(ctx, frame, anchor, result),
        )
        raise StepFailed(step_id, f"未找到锚点: {anchor}")

    if kind == "template" and result.kind != "template":
        raise StepFailed(step_id, f"锚点 {anchor} 不是模板类型")

    ctx.trace.log(
        "anchor_evaluated",
        step_name=step_id,
        action_type=f"click_{kind}",
        status="success",
        **_anchor_trace_kwargs(ctx, frame, anchor, result),
    )
    assert ctx.input is not None
    ctx.input.click(result.center[0], result.center[1])
    ctx.log.info(
        "点击",
        step=step_id,
        anchor=anchor,
        center=result.center,
        confidence=result.confidence,
    )
    return True


def _anchor_trace_kwargs(ctx: RunContext, frame, anchor: str, result) -> dict[str, Any]:
    anchor_config = ctx.profile.anchors.get(anchor)
    return diagnostics_from_anchor_result(
        result,
        anchor_name=anchor,
        anchor_config=anchor_config,
        frame=frame,
    )


def register_anchor_handlers(
    registry: ActionRegistry, *, default_timeout_ms: int
) -> None:
    registry.register(
        "wait_for",
        lambda ctx, step_id, params: _wait_for_anchor(
            ctx, step_id, params, default_timeout_ms=default_timeout_ms
        ),
    )
    registry.register(
        "click_template",
        lambda ctx, step_id, params: _click_anchor(ctx, step_id, params, kind="template"),
    )
    registry.register(
        "click_ocr",
        lambda ctx, step_id, params: _click_anchor(ctx, step_id, params, kind="ocr"),
    )
