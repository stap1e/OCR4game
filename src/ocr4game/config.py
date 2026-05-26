"""配置加载与路径解析。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configs_dir() -> Path:
    return repo_root() / "configs"


def game_config_dir(game_id: str) -> Path:
    return configs_dir() / "games" / game_id


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


class GlobalConfig(BaseModel):
    log_level: str = "INFO"
    runs_dir: str = "runs"
    capture: dict[str, Any] = Field(default_factory=dict)
    input: dict[str, Any] = Field(default_factory=dict)
    workflow: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def load(cls) -> GlobalConfig:
        path = configs_dir() / "global.yaml"
        if not path.exists():
            return cls()
        return cls.model_validate(load_yaml(path))


class GameProfile(BaseModel):
    game_id: str
    display_name: str = ""
    window: dict[str, Any] = Field(default_factory=dict)
    resolution: dict[str, int] = Field(default_factory=dict)
    paths: dict[str, str] = Field(default_factory=dict)
    anchors: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recovery: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def load(cls, game_id: str) -> GameProfile:
        path = game_config_dir(game_id) / "profile.yaml"
        data = load_yaml(path)
        data.setdefault("game_id", game_id)
        return cls.model_validate(data)

    def assets_dir(self) -> Path:
        rel = self.paths.get("assets", "assets")
        return game_config_dir(self.game_id) / rel

    def anchor_image_path(self, anchor_name: str) -> Path | None:
        anchor = self.anchors.get(anchor_name)
        if not anchor or anchor.get("type") != "template":
            return None
        image = anchor.get("image")
        if not image:
            return None
        return self.assets_dir() / image
