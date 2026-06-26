"""YAML 工作流执行引擎。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ocr4game.config import load_task_config
from ocr4game.games.base import GamePlugin
from ocr4game.workflow.actions import ActionExecutor, ActionRegistry, build_default_registry
from ocr4game.workflow.conditions import evaluate_condition
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.errors import RunTimeout, StepFailed
from ocr4game.workflow.semantics import parse_step_runtime
from ocr4game.workflow.vars import resolve_value


class WorkflowEngine:
    def __init__(
        self,
        ctx: RunContext,
        *,
        plugin: GamePlugin | None = None,
        registry: ActionRegistry | None = None,
    ) -> None:
        self._ctx = ctx
        self._default_timeout = ctx.global_cfg.workflow.default_step_timeout_ms
        self._default_retry = ctx.global_cfg.workflow.default_max_retry
        self._max_run_seconds = ctx.global_cfg.workflow.max_run_minutes * 60
        self._run_started_at: float | None = None
        self._registry = registry or build_default_registry(default_timeout_ms=self._default_timeout)
        if plugin is not None:
            plugin.register_actions(self._registry)
        self._executor = ActionExecutor(ctx, self._registry)

    def run_task(
        self,
        task_path: Path,
        *,
        var_overrides: dict[str, Any] | None = None,
    ) -> None:
        task = load_task_config(task_path)
        self._ctx.vars.update(task.vars)
        if var_overrides:
            self._ctx.vars.update(var_overrides)

        self._run_started_at = time.monotonic()
        self._ctx.trace.log(
            "task_started",
            status="started",
            message=str(task_path),
            extra={"task_name": task.name or task_path.stem},
        )
        try:
            for step_index, block in enumerate(task.steps):
                self._check_run_timeout()
                self._run_step_block(self._resolve(block.model_dump()), step_index=step_index)
        except Exception:
            self._ctx.trace.log(
                "task_finished",
                status="failed",
                elapsed_ms=None,
            )
            raise
        self._ctx.trace.log(
            "task_finished",
            status="finished",
            elapsed_ms=self._run_elapsed_ms(),
        )

    def _check_run_timeout(self) -> None:
        if self._run_started_at is None or self._max_run_seconds <= 0:
            return
        elapsed = time.monotonic() - self._run_started_at
        if elapsed > self._max_run_seconds:
            raise RunTimeout(max_minutes=self._ctx.global_cfg.workflow.max_run_minutes)

    def _resolve(self, value: Any) -> Any:
        return resolve_value(value, self._ctx.vars)

    def _run_step_block(self, block: dict[str, Any], *, step_index: int) -> None:
        step_id = block.get("id", "anonymous")
        when = block.get("when")
        if when is not None:
            condition_result = evaluate_condition(when, self._ctx)
            self._ctx.trace.log(
                "condition_evaluated",
                step_index=step_index,
                step_name=step_id,
                status="success",
                condition=_condition_summary(when),
                condition_result=condition_result,
            )
            if not condition_result:
                self._ctx.log.info("步骤跳过", step=step_id, reason="when=false")
                self._ctx.trace.log(
                    "step_skipped",
                    step_index=step_index,
                    step_name=step_id,
                    status="skipped",
                    message="when=false",
                )
                return

        runtime = parse_step_runtime(block, default_retry=self._default_retry)
        started_at = time.monotonic()
        self._ctx.trace.log(
            "step_started",
            step_index=step_index,
            step_name=step_id,
            status="started",
        )
        try:
            if runtime.loop_max is not None:
                for iteration in range(runtime.loop_max):
                    self._check_run_timeout()
                    if not self._run_with_retry(
                        step_id,
                        runtime.actions,
                        retry=runtime.retry,
                        step_index=step_index,
                        iteration_extra={"loop_iteration": iteration},
                    ):
                        break
            elif runtime.repeat is not None:
                for iteration in range(runtime.repeat):
                    self._check_run_timeout()
                    if not self._run_with_retry(
                        step_id,
                        runtime.actions,
                        retry=runtime.retry,
                        step_index=step_index,
                        iteration_extra={"repeat_iteration": iteration},
                    ):
                        break
            else:
                self._run_with_retry(
                    step_id,
                    runtime.actions,
                    retry=runtime.retry,
                    allow_fail=True,
                    step_index=step_index,
                )
        except StepFailed as exc:
            self._ctx.trace.log(
                "step_failed",
                step_index=step_index,
                step_name=step_id,
                status="failed",
                message=str(exc),
                elapsed_ms=_elapsed_ms(started_at),
            )
            raise

        self._ctx.trace.log(
            "step_finished",
            step_index=step_index,
            step_name=step_id,
            status="finished",
            elapsed_ms=_elapsed_ms(started_at),
        )

    def _run_with_retry(
        self,
        step_id: str,
        actions: list[dict[str, Any]],
        *,
        retry: int,
        allow_fail: bool = False,
        step_index: int | None = None,
        iteration_extra: dict[str, Any] | None = None,
    ) -> bool:
        attempts = max(retry, 0) + 1
        for attempt in range(attempts):
            self._check_run_timeout()
            try:
                return self._run_actions(
                    step_id,
                    actions,
                    allow_fail=allow_fail,
                    step_index=step_index,
                    retry_count=attempt,
                    extra=iteration_extra,
                )
            except StepFailed as exc:
                if attempt + 1 >= attempts:
                    raise
                self._ctx.trace.log(
                    "step_retry",
                    step_index=step_index,
                    step_name=step_id,
                    status="retry",
                    retry_count=attempt + 1,
                    message=str(exc),
                    extra=iteration_extra or {},
                )
        return True

    def _run_actions(
        self,
        step_id: str,
        actions: list[dict[str, Any]],
        *,
        allow_fail: bool = False,
        step_index: int | None = None,
        retry_count: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        for action_index, action in enumerate(actions):
            self._check_run_timeout()
            if (
                self._execute_action_or_if(
                    step_id,
                    action,
                    allow_fail=allow_fail,
                    step_index=step_index,
                    action_index=action_index,
                    retry_count=retry_count,
                    extra=extra,
                )
                is False
            ):
                if allow_fail:
                    continue
                return False
        return True

    def _execute_action_or_if(
        self,
        step_id: str,
        action: dict[str, Any],
        *,
        allow_fail: bool,
        step_index: int | None = None,
        action_index: int | None = None,
        retry_count: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        if isinstance(action, dict) and len(action) == 1 and "if" in action:
            branch = action["if"]
            if not isinstance(branch, dict):
                raise StepFailed(step_id, f"无效 if 分支: {branch!r}")
            when = branch.get("when")
            condition_result = evaluate_condition(when, self._ctx)
            self._ctx.trace.log(
                "condition_evaluated",
                step_index=step_index,
                step_name=step_id,
                action_index=action_index,
                action_type="if",
                status="success",
                condition=_condition_summary(when),
                condition_result=condition_result,
                extra=extra or {},
            )
            if condition_result:
                nested = branch.get("do") or []
                return self._run_actions(
                    step_id,
                    nested,
                    allow_fail=allow_fail,
                    step_index=step_index,
                    retry_count=retry_count,
                    extra={**(extra or {}), "parent_action_index": action_index},
                )
            return True

        if not self._executor.execute(
            step_id,
            action,
            step_index=step_index,
            action_index=action_index,
            retry_count=retry_count,
            extra=extra,
        ):
            return False
        return True

    def _run_elapsed_ms(self) -> int | None:
        if self._run_started_at is None:
            return None
        return _elapsed_ms(self._run_started_at)


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _condition_summary(condition: Any) -> str:
    return str(condition)
