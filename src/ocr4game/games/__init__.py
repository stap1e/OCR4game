from ocr4game.games.base import GamePlugin
from ocr4game.games.registry import (
    PluginSpec,
    discover_configured_games,
    get_plugin,
    get_plugin_spec,
    list_registered_games,
)

__all__ = [
    "GamePlugin",
    "PluginSpec",
    "discover_configured_games",
    "get_plugin",
    "get_plugin_spec",
    "list_registered_games",
]
