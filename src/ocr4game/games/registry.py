"""游戏插件注册表。"""

from __future__ import annotations

from dataclasses import dataclass

from ocr4game.config import GameProfile
from ocr4game.games.base import GamePlugin
from ocr4game.games.star_rail.plugin import StarRailPlugin


@dataclass(frozen=True)
class PluginSpec:
    game_id: str
    plugin_cls: type[GamePlugin]


_REGISTRY: dict[str, PluginSpec] = {
    "star_rail": PluginSpec(game_id="star_rail", plugin_cls=StarRailPlugin),
}


def get_plugin_spec(game_id: str) -> PluginSpec:
    spec = _REGISTRY.get(game_id)
    if spec is None:
        raise KeyError(f"未注册的游戏插件: {game_id}")
    return spec


def get_plugin(profile: GameProfile) -> GamePlugin:
    return get_plugin_spec(profile.game_id).plugin_cls(profile)
