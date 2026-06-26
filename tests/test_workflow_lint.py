from __future__ import annotations

from pathlib import Path

from ocr4game.config import load_game_profile
from ocr4game.resources import game_task_path
from ocr4game.tools.lint import main as lint_main
from ocr4game.validation import has_errors
from ocr4game.workflow.lint import lint_task_file


def _write_task(path: Path, body: str) -> Path:
    path.write_text(body.strip(), encoding="utf-8")
    return path


def _messages(path: Path) -> list[str]:
    profile = load_game_profile("star_rail")
    return [issue.message for issue in lint_task_file(profile, path)]


def test_lint_daily_has_no_errors() -> None:
    profile = load_game_profile("star_rail")
    issues = lint_task_file(profile, game_task_path(profile, "daily"))
    assert not has_errors(issues)


def test_lint_unused_var(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path / "unused.yaml",
        """
vars:
  unused: 1
steps:
  - id: s
    do:
      - wait:
          ms: 1
""",
    )
    assert any("未使用的任务变量" in message for message in _messages(task))


def test_lint_loop_retry_and_wait_ranges(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path / "ranges.yaml",
        """
steps:
  - id: ranges
    loop:
      max: 101
    retry: 11
    do:
      - wait:
          ms: 130000
""",
    )
    messages = _messages(task)
    assert any("loop.max 过大" in message for message in messages)
    assert any("retry 过大" in message for message in messages)
    assert any("ms 异常偏大" in message for message in messages)


def test_lint_invalid_wait_and_negative_retry_are_errors(tmp_path: Path) -> None:
    profile = load_game_profile("star_rail")
    task = _write_task(
        tmp_path / "bad_wait.yaml",
        """
steps:
  - id: bad
    retry: -1
    do:
      - wait:
          ms: 0
""",
    )
    issues = lint_task_file(profile, task)
    assert has_errors(issues)
    assert any("retry 不能为负数" in issue.message for issue in issues)
    assert any("ms 必须大于 0" in issue.message for issue in issues)


def test_lint_optional_without_recovery_and_duplicate_click(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path / "actions.yaml",
        """
steps:
  - id: actions
    do:
      - click_template:
          anchor: claim_button
          optional: true
      - click_template:
          anchor: claim_button
""",
    )
    messages = _messages(task)
    assert any("optional action 后缺少" in message for message in messages)
    assert any("连续重复点击同一锚点" in message for message in messages)


def test_lint_static_false_condition(tmp_path: Path) -> None:
    task = _write_task(
        tmp_path / "condition.yaml",
        """
vars:
  enabled: false
steps:
  - id: condition
    when:
      var_eq:
        enabled: true
    do:
      - wait:
          ms: 1
""",
    )
    assert any("condition 明显永远为 false" in message for message in _messages(task))


def test_lint_includes_validate_errors(tmp_path: Path) -> None:
    profile = load_game_profile("star_rail")
    task = _write_task(
        tmp_path / "unknowns.yaml",
        """
steps:
  - id: bad
    do:
      - fly_to_moon: {}
      - click_template:
          anchor: missing_anchor
""",
    )
    issues = lint_task_file(profile, task)
    assert has_errors(issues)
    assert any("未知动作" in issue.message for issue in issues)
    assert any("未定义的锚点" in issue.message for issue in issues)


def test_lint_cli_daily_exits_zero() -> None:
    assert lint_main(["--game", "star_rail", "--task", "daily"]) == 0


def test_lint_cli_strict_fails_on_warning(tmp_path: Path, monkeypatch) -> None:
    profile = load_game_profile("star_rail")
    task = _write_task(
        tmp_path / "warn.yaml",
        """
vars:
  unused: 1
steps:
  - id: s
    do:
      - wait:
          ms: 1
""",
    )
    monkeypatch.setattr("ocr4game.tools.lint.game_task_path", lambda _profile, _task: task)
    assert lint_main(["--game", profile.game_id, "--task", "warn", "--strict"]) == 1
