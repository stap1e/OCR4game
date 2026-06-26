from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ocr4game.config import load_game_profile, load_global_config
from ocr4game.workflow.actions import ActionRegistry
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.engine import WorkflowEngine
from ocr4game.workflow.errors import StepFailed


class DummyLog:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def info(self, event: str, **kwargs) -> None:
        self.events.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs) -> None:
        self.events.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs) -> None:
        self.events.append(("error", event, kwargs))


class DummyInput:
    def __init__(self) -> None:
        self.sleep_calls: list[int] = []
        self.click_calls: list[tuple[int, int]] = []

    def sleep_ms(self, ms: int) -> None:
        self.sleep_calls.append(ms)

    def click(self, x: int, y: int) -> None:
        self.click_calls.append((x, y))


class DummyPerception:
    def __init__(self, results: list[SimpleNamespace]) -> None:
        self._results = results
        self.calls = 0

    def evaluate_anchor(self, frame: np.ndarray, anchor_name: str) -> SimpleNamespace:
        index = min(self.calls, len(self._results) - 1)
        self.calls += 1
        return self._results[index]


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    profile = load_game_profile("star_rail")
    global_cfg = load_global_config()
    global_cfg.runs_dir = str(tmp_path)
    log = DummyLog()
    ctx = RunContext(profile=profile, global_cfg=global_cfg, log=log)
    ctx.input = DummyInput()
    return ctx


def _result(*, found: bool, kind: str = "template", center: tuple[int, int] = (10, 20), confidence: float = 0.9) -> SimpleNamespace:
    return SimpleNamespace(found=found, kind=kind, center=center, confidence=confidence)


def test_click_template_optional_skip(run_context: RunContext) -> None:
    run_context.perception = DummyPerception([_result(found=False)])
    run_context.capture = SimpleNamespace(grab=lambda: np.zeros((20, 20, 3), dtype=np.uint8))
    engine = WorkflowEngine(run_context)

    ok = engine._run_actions(
        "claim_rewards",
        [{"click_template": {"anchor": "claim_button", "optional": True}}],
    )

    assert ok is True
    assert run_context.input.click_calls == []
    assert any(event == "可选步骤跳过" for _, event, _ in run_context.log.events)


def test_click_template_failure_raises(run_context: RunContext) -> None:
    run_context.perception = DummyPerception([_result(found=False)])
    run_context.capture = SimpleNamespace(grab=lambda: np.zeros((20, 20, 3), dtype=np.uint8))
    engine = WorkflowEngine(run_context)

    with pytest.raises(StepFailed):
        engine._run_actions(
            "claim_rewards",
            [{"click_template": {"anchor": "claim_button"}}],
        )

    assert any(event == "步骤失败" for _, event, _ in run_context.log.events)


def test_wait_for_uses_default_timeout_and_polls(run_context: RunContext) -> None:
    run_context.perception = DummyPerception([_result(found=False), _result(found=True)])
    engine = WorkflowEngine(run_context)
    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    run_context.capture = SimpleNamespace(grab=lambda: frame)

    ok = engine._run_actions(
        "wait_main",
        [{"wait_for": {"anchor": "main_menu_marker"}}],
    )

    assert ok is True
    assert run_context.perception.calls == 2
    assert run_context.input.sleep_calls == [200]


def test_loop_breaks_on_false_return(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "loop.yaml"
    task_path.write_text(
        """
steps:
  - id: claim_rewards
    loop:
      max: 5
    do:
      - stop_here: {}
""".strip(),
        encoding="utf-8",
    )

    registry = ActionRegistry()
    engine = WorkflowEngine(run_context, registry=registry)
    calls = {"count": 0}

    def stop_here(_ctx, _step_id, _params):
        calls["count"] += 1
        return False

    registry.register("stop_here", stop_here)
    engine.run_task(task_path)

    assert calls["count"] == 1




def test_repeat_breaks_on_false_return(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "repeat.yaml"
    task_path.write_text(
        """
steps:
  - id: claim_rewards
    repeat: 3
    do:
      - stop_here: {}
""".strip(),
        encoding="utf-8",
    )

    registry = ActionRegistry()
    engine = WorkflowEngine(run_context, registry=registry)
    calls = {"count": 0}

    def stop_here(_ctx, _step_id, _params):
        calls["count"] += 1
        return False

    registry.register("stop_here", stop_here)
    engine.run_task(task_path)

    assert calls["count"] == 1


def test_retry_retries_step_until_success(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "retry.yaml"
    task_path.write_text(
        """
steps:
  - id: claim_rewards
    retry: 2
    do:
      - flaky: {}
""".strip(),
        encoding="utf-8",
    )

    run_context.capture = SimpleNamespace(grab=lambda: np.zeros((20, 20, 3), dtype=np.uint8))
    registry = ActionRegistry()
    engine = WorkflowEngine(run_context, registry=registry)
    calls = {"count": 0}

    def flaky(_ctx, step_id, _params):
        calls["count"] += 1
        if calls["count"] < 3:
            raise StepFailed(step_id, "temporary")
        return True

    registry.register("flaky", flaky)
    engine.run_task(task_path)

    assert calls["count"] == 3


def test_task_vars_interpolate_repeat_and_wait(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "vars.yaml"
    task_path.write_text(
        """
vars:
  sweep_times: 2
  panel_wait_ms: 900

steps:
  - id: sweep
    repeat: "{sweep_times}"
    do:
      - wait:
          ms: "{panel_wait_ms}"
      - log: "第 {sweep_times} 轮"
""".strip(),
        encoding="utf-8",
    )

    engine = WorkflowEngine(run_context)
    engine.run_task(task_path)

    assert run_context.input.sleep_calls == [900, 900]
    assert any(
        event == "workflow" and kwargs.get("msg") == "第 2 轮"
        for _, event, kwargs in run_context.log.events
    )


def test_task_vars_interpolate_loop_max(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "loop_vars.yaml"
    task_path.write_text(
        """
vars:
  claim_loop_max: 3

steps:
  - id: claim
    loop:
      max: "{claim_loop_max}"
    do:
      - tick: {}
""".strip(),
        encoding="utf-8",
    )

    registry = ActionRegistry()
    engine = WorkflowEngine(run_context, registry=registry)
    calls = {"count": 0}

    def tick(_ctx, _step_id, _params):
        calls["count"] += 1
        return True

    registry.register("tick", tick)
    engine.run_task(task_path)

    assert calls["count"] == 3


def test_var_overrides_beat_task_yaml(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "override.yaml"
    task_path.write_text(
        """
vars:
  sweep_times: 1
  claim_loop_max: 8

steps:
  - id: sweep
    repeat: "{sweep_times}"
    do:
      - wait:
          ms: "{claim_loop_max}"
""".strip(),
        encoding="utf-8",
    )

    engine = WorkflowEngine(run_context)
    engine.run_task(task_path, var_overrides={"sweep_times": 2, "claim_loop_max": 500})

    assert run_context.input.sleep_calls == [500, 500]


def test_step_when_skips_block(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "when_skip.yaml"
    task_path.write_text(
        """
steps:
  - id: only_if_visible
    when:
      anchor_visible: claim_button
    do:
      - stop_here: {}
  - id: always
    do:
      - tick: {}
""".strip(),
        encoding="utf-8",
    )

    from types import SimpleNamespace

    run_context.perception = SimpleNamespace(
        evaluate_anchor=lambda _f, name: SimpleNamespace(
            found=name == "claim_button",
            kind="template",
            confidence=0.9,
        )
    )
    run_context.capture = SimpleNamespace(grab=lambda: None)

    registry = ActionRegistry()
    engine = WorkflowEngine(run_context, registry=registry)
    calls: list[str] = []

    def stop_here(_ctx, _step_id, _params):
        calls.append("stop")
        return True

    def tick(_ctx, _step_id, _params):
        calls.append("tick")
        return True

    registry.register("stop_here", stop_here)
    registry.register("tick", tick)
    engine.run_task(task_path)

    assert calls == ["stop", "tick"]


def test_action_if_branch(run_context: RunContext, tmp_path: Path) -> None:
    task_path = tmp_path / "if_action.yaml"
    task_path.write_text(
        """
steps:
  - id: branch
    do:
      - if:
          when:
            var_eq:
              go: true
          do:
            - mark: {}
""".strip(),
        encoding="utf-8",
    )

    run_context.vars["go"] = True
    registry = ActionRegistry()
    engine = WorkflowEngine(run_context, registry=registry)
    calls: list[str] = []

    registry.register("mark", lambda *_a: calls.append("mark") or True)
    engine.run_task(task_path)
    assert calls == ["mark"]

