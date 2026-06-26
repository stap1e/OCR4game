from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ocr4game.config import load_game_profile, load_global_config
from ocr4game.runtime.trace import TraceLogger
from ocr4game.workflow.actions import ActionRegistry
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.engine import WorkflowEngine
from ocr4game.workflow.errors import StepFailed


class DummyLog:
    def info(self, _event: str, **_kwargs) -> None:
        return None

    def warning(self, _event: str, **_kwargs) -> None:
        return None

    def error(self, _event: str, **_kwargs) -> None:
        return None


class DummyInput:
    def sleep_ms(self, _ms: int) -> None:
        return None

    def click(self, _x: int, _y: int) -> None:
        return None


def _context(tmp_path: Path) -> tuple[RunContext, Path]:
    profile = load_game_profile("star_rail")
    global_cfg = load_global_config()
    global_cfg.runs_dir = str(tmp_path)
    ctx = RunContext(profile=profile, global_cfg=global_cfg, log=DummyLog())
    ctx.input = DummyInput()
    ctx.capture = SimpleNamespace(grab=lambda: np.zeros((20, 20, 3), dtype=np.uint8))
    ctx.run_dir = tmp_path / "run"
    ctx.trace = TraceLogger(ctx.run_dir, ctx.profile.game_id, "daily")
    return ctx, ctx.run_dir / "trace.jsonl"


def _trace_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_workflow_trace_records_successful_actions(tmp_path: Path) -> None:
    ctx, trace_path = _context(tmp_path)
    task_path = tmp_path / "trace_success.yaml"
    task_path.write_text(
        """
steps:
  - id: trace_step
    do:
      - mark: {}
""".strip(),
        encoding="utf-8",
    )

    registry = ActionRegistry()
    registry.register("mark", lambda *_a: True)
    WorkflowEngine(ctx, registry=registry).run_task(task_path)
    ctx.trace.close()

    names = [event["event"] for event in _trace_events(trace_path)]
    assert "action_started" in names
    assert "action_finished" in names


def test_workflow_trace_records_optional_failure_and_continues(tmp_path: Path) -> None:
    ctx, trace_path = _context(tmp_path)
    task_path = tmp_path / "trace_optional.yaml"
    task_path.write_text(
        """
steps:
  - id: optional_step
    do:
      - flaky: { optional: true }
      - mark: {}
""".strip(),
        encoding="utf-8",
    )

    calls: list[str] = []
    registry = ActionRegistry()

    def flaky(_ctx, step_id, _params):
        raise StepFailed(step_id, "optional boom")

    registry.register("flaky", flaky)
    registry.register("mark", lambda *_a: calls.append("mark") or True)
    WorkflowEngine(ctx, registry=registry).run_task(task_path)
    ctx.trace.close()

    events = _trace_events(trace_path)
    assert calls == ["mark"]
    assert any(event["event"] == "action_optional_failed" for event in events)


def test_workflow_trace_records_retry(tmp_path: Path) -> None:
    ctx, trace_path = _context(tmp_path)
    task_path = tmp_path / "trace_retry.yaml"
    task_path.write_text(
        """
steps:
  - id: retry_step
    retry: 1
    do:
      - flaky: {}
""".strip(),
        encoding="utf-8",
    )

    calls = {"count": 0}
    registry = ActionRegistry()

    def flaky(_ctx, step_id, _params):
        calls["count"] += 1
        if calls["count"] == 1:
            raise StepFailed(step_id, "temporary")
        return True

    registry.register("flaky", flaky)
    WorkflowEngine(ctx, registry=registry).run_task(task_path)
    ctx.trace.close()

    events = _trace_events(trace_path)
    assert any(event["event"] == "step_retry" and event["retry_count"] == 1 for event in events)
