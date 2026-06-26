from ocr4game.resources import (
    configs_dir,
    game_assets_dir,
    game_config_dir,
    game_profile_path,
    game_task_path,
    games_config_dir,
    global_config_path,
    repo_root,
)


def test_repo_root_contains_configs_and_src() -> None:
    root = repo_root()
    assert (root / "configs").is_dir()
    assert (root / "src" / "ocr4game").is_dir()


def test_global_config_path() -> None:
    assert global_config_path() == configs_dir() / "global.yaml"


def test_star_rail_paths() -> None:
    assert game_config_dir("star_rail") == games_config_dir() / "star_rail"
    assert game_profile_path("star_rail").name == "profile.yaml"
    assert game_task_path.__name__ == "game_task_path"

    from ocr4game.config import load_game_profile

    profile = load_game_profile("star_rail")
    assert game_assets_dir(profile) == game_config_dir("star_rail") / "assets"
    assert game_task_path(profile, "daily").name == "daily.yaml"
