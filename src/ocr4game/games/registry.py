"""游戏插件注册表。"""

from __future__ import annotations

from ocr4game.config import GameProfile
from ocr4game.games.base import GamePlugin
from ocr4game.games.star_rail.plugin import StarRailPlugin

_REGISTRY: dict[str, type[GamePlugin]] = {
    "star_rail": StarRailPlugin,
}


def get_plugin(profile: GameProfile) -> GamePlugin:
    cls = _REGISTRY.get(profile.game_id)
    if cls is None:
        raise KeyError(f"未注册的游戏插件: {profile.game_id}")
    return cls(profile)
