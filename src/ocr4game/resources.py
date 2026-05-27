"""仓库内资源路径定位。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ocr4game.config import GameProfile, GlobalConfig


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configs_dir() -> Path:
    return repo_root() / "configs"


def game_config_dir(game_id: str) -> Path:
    return configs_dir() / "games" / game_id


def global_config_path() -> Path:
    return configs_dir() / "global.yaml"


def game_profile_path(game_id: str) -> Path:
    return game_config_dir(game_id) / "profile.yaml"


def game_assets_dir(profile: GameProfile) -> Path:
    return game_config_dir(profile.game_id) / profile.paths.assets


def game_task_path(profile: GameProfile, task_name: str) -> Path:
    return game_config_dir(profile.game_id) / profile.paths.tasks / f"{task_name}.yaml"


def game_anchor_image_path(profile: GameProfile, anchor_name: str) -> Path | None:
    from ocr4game.config import TemplateAnchorConfig

    anchor = profile.anchors.get(anchor_name)
    if not anchor or not isinstance(anchor, TemplateAnchorConfig):
        return None
    return game_assets_dir(profile) / anchor.image


def runs_base_dir(global_cfg: GlobalConfig) -> Path:
    return repo_root() / global_cfg.runs_dir
