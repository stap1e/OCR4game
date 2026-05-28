"""游戏插件注册表。"""

from __future__ import annotations

from dataclasses import dataclass

from ocr4game.config import GameProfile
from ocr4game.games.base import GamePlugin
from ocr4game.games.star_rail.plugin import StarRailPlugin
from ocr4game.resources import games_config_dir


@dataclass(frozen=True)
class PluginSpec:
    game_id: str
    plugin_cls: type[GamePlugin]
    display_name: str = ""


_REGISTRY: dict[str, PluginSpec] = {
    "star_rail": PluginSpec(
        game_id="star_rail",
        plugin_cls=StarRailPlugin,
        display_name="崩坏：星穹铁道",
    ),
}


def list_registered_games() -> list[str]:
    return sorted(_REGISTRY.keys())


def discover_configured_games() -> list[str]:
    """configs/games/ 下已有 profile.yaml 的游戏（排除 _ 前缀脚手架）。"""
    root = games_config_dir()
    if not root.is_dir():
        return []
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir()
        and not path.name.startswith("_")
        and (path / "profile.yaml").is_file()
    )


def get_plugin_spec(game_id: str) -> PluginSpec:
    spec = _REGISTRY.get(game_id)
    if spec is None:
        raise KeyError(f"未注册的游戏插件: {game_id}")
    return spec


def get_plugin(profile: GameProfile) -> GamePlugin:
    return get_plugin_spec(profile.game_id).plugin_cls(profile)
