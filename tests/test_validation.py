from ocr4game.config import load_game_profile, load_task_config
from ocr4game.resources import game_task_path
from ocr4game.validation import has_errors, validate_run


def test_daily_task_yaml_parses() -> None:
    profile = load_game_profile("star_rail")
    task_path = game_task_path(profile, "daily")
    task = load_task_config(task_path)
    assert task.name == "star_rail_daily"
    assert len(task.steps) >= 5


def test_validate_daily_has_no_errors_without_strict() -> None:
    profile = load_game_profile("star_rail")
    task_path = game_task_path(profile, "daily")
    issues = validate_run(profile, task_path)
    assert not has_errors(issues)


def test_validate_daily_strict_passes_with_synced_assets() -> None:
    profile = load_game_profile("star_rail")
    task_path = game_task_path(profile, "daily")
    issues = validate_run(profile, task_path, strict_assets=True)
    assert not has_errors(issues)


def test_validate_unknown_anchor(tmp_path) -> None:
    profile = load_game_profile("star_rail")
    bad_task = tmp_path / "bad.yaml"
    bad_task.write_text(
        """
steps:
  - id: bad
    do:
      - click_template:
          anchor: not_exists
""".strip(),
        encoding="utf-8",
    )
    issues = validate_run(profile, bad_task)
    assert has_errors(issues)
    assert any("not_exists" in issue.message for issue in issues)


def test_validate_unknown_action(tmp_path) -> None:
    profile = load_game_profile("star_rail")
    bad_task = tmp_path / "bad_action.yaml"
    bad_task.write_text(
        """
steps:
  - id: bad
    do:
      - fly_to_moon: {}
""".strip(),
        encoding="utf-8",
    )
    issues = validate_run(profile, bad_task)
    assert has_errors(issues)
