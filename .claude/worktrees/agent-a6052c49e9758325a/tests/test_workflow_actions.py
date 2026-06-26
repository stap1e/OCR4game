from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ocr4game.config import load_game_profile, load_global_config
from ocr4game.workflow.context import RunContext
from ocr4game.workflow.engine import WorkflowEngine
from ocr4game.workflow.errors import RunTimeout, StepFailed


class DummyLog:
    def info(self, *_a, **_k) -> None:
        return None

    def warning(self, *_a, **_k) -> None:
        return None

    def error(self, *_a, **_k) -> None:
        return None


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    profile = load_game_profile("star_rail")
    global_cfg = load_global_config()
    global_cfg.runs_dir = str(tmp_path)
    return RunContext(profile=profile, global_cfg=global_cfg, log=DummyLog())


def test_unknown_action_raises(run_context: RunContext) -> None:
    engine = WorkflowEngine(run_context)
    with pytest.raises(StepFailed, match="未知动作"):
        engine._run_actions("bad", [{"fly_to_moon": {}}])


def test_run_timeout(run_context: RunContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    task_path = tmp_path / "slow.yaml"
    task_path.write_text(
        """
steps:
  - id: slow
    do:
      - wait:
          ms: 100
""".strip(),
        encoding="utf-8",
    )

    run_context.global_cfg.workflow.max_run_minutes = 1
    run_context.input = SimpleNamespace(sleep_ms=lambda _ms: None, click=lambda *_a: None)
    engine = WorkflowEngine(run_context)

    times = iter([0.0, 61.0])
    monkeypatch.setattr("ocr4game.workflow.engine.time.monotonic", lambda: next(times))

    with pytest.raises(RunTimeout):
        engine.run_task(task_path)
