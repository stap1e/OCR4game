from ocr4game.config import TaskConfig, load_game_profile, load_task_config
from ocr4game.games.base import GamePlugin
from ocr4game.resources import game_task_path
from ocr4game.validation import has_errors, validate_run
from ocr4game.workflow.actions import ActionRegistry


class ValidationPlugin(GamePlugin):
    game_id = "star_rail"

    def register_actions(self, registry: ActionRegistry) -> None:
        registry.register("plugin_action", lambda *_args: True)

    def validate_profile(self) -> list[str]:
        return ["profile warning"]

    def validate_task(self, task: TaskConfig) -> list[str]:
        return [f"task warning: {len(task.steps)} steps"]


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


def test_plugin_registered_action_and_validation_hooks(tmp_path) -> None:
    profile = load_game_profile("star_rail")
    task_path = tmp_path / "plugin_action.yaml"
    task_path.write_text(
        """
steps:
  - id: plugin
    do:
      - plugin_action: {}
""".strip(),
        encoding="utf-8",
    )

    issues = validate_run(profile, task_path, plugin=ValidationPlugin(profile))

    assert not has_errors(issues)
    assert any(issue.message == "profile warning" for issue in issues)
    assert any(issue.message.startswith("task warning") for issue in issues)


def test_validate_invalid_loop_max_after_vars(tmp_path) -> None:
    profile = load_game_profile("star_rail")
    bad_task = tmp_path / "bad_loop.yaml"
    bad_task.write_text(
        """
vars:
  loop_max: many
steps:
  - id: bad_loop
    loop:
      max: "{loop_max}"
    do:
      - wait:
          ms: 1
""".strip(),
        encoding="utf-8",
    )

    issues = validate_run(profile, bad_task)

    assert has_errors(issues)
    assert any("步骤运行参数无效" in issue.message for issue in issues)


def test_validate_if_uses_shared_action_shape_check(tmp_path) -> None:
    profile = load_game_profile("star_rail")
    bad_task = tmp_path / "bad_if_action.yaml"
    bad_task.write_text(
        """
steps:
  - id: bad_if
    do:
      - if:
          when:
            var_eq:
              enabled: true
          do:
            - wait: {}
              log: extra
""".strip(),
        encoding="utf-8",
    )

    issues = validate_run(profile, bad_task, var_overrides={"enabled": True})

    assert has_errors(issues)
    assert any("动作必须是单键 dict" in issue.message for issue in issues)
