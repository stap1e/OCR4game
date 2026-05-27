"""YAML 工作流执行引擎。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ocr4game.config import load_yaml
from ocr4game.games.base import GamePlugin
from ocr4game.workflow.actions import ActionExecutor, ActionRegistry, build_default_registry
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.errors import StepFailed


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
        self._registry = registry or build_default_registry(default_timeout_ms=self._default_timeout)
        if plugin is not None:
            plugin.register_actions(self._registry)
        self._executor = ActionExecutor(ctx, self._registry)

    def run_task(self, task_path: Path) -> None:
        data = load_yaml(task_path)
        self._ctx.vars.update(data.get("vars") or {})
        steps = data.get("steps") or []
        for block in steps:
            self._run_step_block(block)

    def _run_step_block(self, block: dict[str, Any]) -> None:
        step_id = block.get("id", "anonymous")
        actions = block.get("do") or []
        loop_cfg = block.get("loop")
        repeat = block.get("repeat")
        retry = int(block.get("retry", self._default_retry))

        if loop_cfg is not None:
            max_iter = int(loop_cfg) if isinstance(loop_cfg, int) else int(loop_cfg.get("max", 10))
            for _ in range(max_iter):
                if not self._run_with_retry(step_id, actions, retry=retry):
                    break
            return

        if repeat is not None:
            for _ in range(int(repeat)):
                self._run_with_retry(step_id, actions, retry=retry)
            return

        self._run_with_retry(step_id, actions, retry=retry, allow_fail=True)

    def _run_with_retry(
        self,
        step_id: str,
        actions: list[dict[str, Any]],
        *,
        retry: int,
        allow_fail: bool = False,
    ) -> bool:
        attempts = max(retry, 0) + 1
        for attempt in range(attempts):
            try:
                return self._run_actions(step_id, actions, allow_fail=allow_fail)
            except StepFailed:
                if attempt + 1 >= attempts:
                    raise
        return True

    def _run_actions(
        self,
        step_id: str,
        actions: list[dict[str, Any]],
        *,
        allow_fail: bool = False,
    ) -> bool:
        for action in actions:
            if not self._executor.execute(step_id, action):
                if allow_fail:
                    continue
                return False
        return True
