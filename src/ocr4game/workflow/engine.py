"""YAML 工作流执行引擎。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ocr4game.config import game_config_dir, load_yaml
from ocr4game.workflow.context import RunContext


class StepFailed(Exception):
    def __init__(self, step_id: str, message: str = "") -> None:
        self.step_id = step_id
        super().__init__(message or f"步骤失败: {step_id}")


class WorkflowEngine:
    def __init__(self, ctx: RunContext) -> None:
        self._ctx = ctx
        wf = ctx.global_cfg.workflow
        self._default_timeout = int(wf.get("default_step_timeout_ms", 10000))
        self._default_retry = int(wf.get("default_max_retry", 3))

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

        if loop_cfg is not None:
            max_iter = int(loop_cfg) if isinstance(loop_cfg, int) else int(loop_cfg.get("max", 10))
            for _ in range(max_iter):
                if not self._run_actions(step_id, actions):
                    break
            return

        if repeat is not None:
            for _ in range(int(repeat)):
                self._run_actions(step_id, actions)
            return

        self._run_actions(step_id, actions, allow_fail=True)

    def _run_actions(
        self,
        step_id: str,
        actions: list[dict[str, Any]],
        *,
        allow_fail: bool = False,
    ) -> bool:
        for action in actions:
            if not self._execute_action(step_id, action):
                if allow_fail:
                    continue
                return False
        return True

    def _execute_action(self, step_id: str, action: dict[str, Any]) -> bool:
        if len(action) != 1:
            self._ctx.log.warning("无效动作", action=action)
            return True

        name, params = next(iter(action.items()))
        params = params if isinstance(params, dict) else {}
        optional = bool(params.get("optional", False))

        try:
            if name == "log":
                msg = params if isinstance(params, str) else params.get("msg", "")
                self._ctx.log.info("workflow", step=step_id, msg=msg)
                return True

            if name == "assert_window":
                if self._ctx.window is None:
                    raise StepFailed(step_id, "游戏窗口未找到")
                return True

            if name == "wait":
                ms = int(params.get("ms", 500))
                assert self._ctx.input is not None
                self._ctx.input.sleep_ms(ms)
                return True

            if name == "wait_for":
                return self._wait_for_anchor(step_id, params)

            if name == "click_template":
                return self._click_anchor(step_id, params, kind="template")

            if name == "click_ocr":
                return self._click_anchor(step_id, params, kind="ocr")

            self._ctx.log.warning("未知动作", name=name)
            return True

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

    def _wait_for_anchor(self, step_id: str, params: dict[str, Any]) -> bool:
        anchor = params.get("anchor", "")
        timeout_ms = int(params.get("timeout_ms", self._default_timeout))
        optional = bool(params.get("optional", False))
        deadline = time.time() + timeout_ms / 1000.0

        while time.time() < deadline:
            frame = self._ctx.grab_frame()
            assert self._ctx.perception is not None
            if self._ctx.perception.evaluate_anchor(frame, anchor).found:
                return True
            assert self._ctx.input is not None
            self._ctx.input.sleep_ms(200)

        if optional:
            return True
        raise StepFailed(step_id, f"等待锚点超时: {anchor}")

    def _click_anchor(self, step_id: str, params: dict[str, Any], *, kind: str) -> bool:
        anchor = params.get("anchor", "")
        optional = bool(params.get("optional", False))
        frame = self._ctx.grab_frame()
        assert self._ctx.perception is not None
        result = self._ctx.perception.evaluate_anchor(frame, anchor)

        if not result.found:
            if optional:
                return True
            self._ctx.save_failure_shot(step_id, frame)
            raise StepFailed(step_id, f"未找到锚点: {anchor}")

        if kind == "template" and result.kind != "template":
            if optional:
                return True
            raise StepFailed(step_id, f"锚点 {anchor} 不是模板类型")

        assert self._ctx.input is not None
        self._ctx.input.click(result.center[0], result.center[1])
        self._ctx.log.info(
            "点击",
            step=step_id,
            anchor=anchor,
            center=result.center,
            confidence=result.confidence,
        )
        return True
