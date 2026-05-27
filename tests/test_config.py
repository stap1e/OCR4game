from pathlib import Path

import pytest
from pydantic import ValidationError

from ocr4game.config import (
    GameProfile,
    OcrAnchorConfig,
    PathsConfig,
    TemplateAnchorConfig,
    load_game_profile,
    load_global_config,
    load_yaml,
)
from ocr4game.resources import game_task_path, repo_root


def test_global_config_parses_sample() -> None:
    cfg = load_global_config()
    assert cfg.log_level == "INFO"
    assert cfg.runs_dir == "runs"
    assert cfg.capture.backend == "mss"
    assert cfg.capture.fps_limit == 10
    assert cfg.input.click_jitter == 3
    assert cfg.input.default_delay_ms == 80
    assert cfg.workflow.default_step_timeout_ms == 10000
    assert cfg.workflow.default_max_retry == 3
    assert cfg.workflow.max_run_minutes == 45


def test_game_profile_parses_sample() -> None:
    profile = load_game_profile("star_rail")
    assert profile.game_id == "star_rail"
    assert "Star Rail" in profile.window.title_contains
    assert profile.resolution.width == 2048
    assert profile.paths.assets == "assets"
    assert isinstance(profile.anchors["main_menu_marker"], TemplateAnchorConfig)
    assert isinstance(profile.anchors["daily_text"], OcrAnchorConfig)
    assert profile.recovery.escape_key == "escape"




def test_invalid_anchor_roi_fails_validation() -> None:
    data = load_yaml(Path("configs/games/star_rail/profile.yaml"))
    data["anchors"]["main_menu_marker"]["roi"] = [0.0, 0.0, 1.0]

    with pytest.raises(ValidationError):
        GameProfile.model_validate(data)


def test_game_task_path_uses_profile_paths_tasks() -> None:
    profile = GameProfile(game_id="star_rail", paths=PathsConfig(tasks="custom_tasks"))

    assert game_task_path(profile, "daily") == repo_root() / "configs/games/star_rail/custom_tasks/daily.yaml"
