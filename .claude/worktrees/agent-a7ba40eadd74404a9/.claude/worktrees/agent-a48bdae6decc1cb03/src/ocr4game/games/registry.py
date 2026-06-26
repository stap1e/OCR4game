"""游戏插件注册表（entry_points 自动发现 + 内置回退）。"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points as get_entry_points

from ocr4game.config import GameProfile
from ocr4game.games.base import GamePlugin
from ocr4game.games.star_rail.plugin import StarRailPlugin
from ocr4game.resources import games_config_dir

PLUGIN_GROUP = "ocr4game.plugins"


@dataclass(frozen=True)
class PluginSpec:
    game_id: str
    plugin_cls: type[GamePlugin]
    display_name: str = ""
    source: str = "entry-point"


# 未 pip install 时（仅 PYTHONPATH=src）仍可用的内置插件
_BUILTIN_REGISTRY: dict[str, PluginSpec] = {
    "star_rail": PluginSpec(
        game_id="star_rail",
        plugin_cls=StarRailPlugin,
        display_name="崩坏：星穹铁道",
        source="builtin",
    ),
}

_REGISTRY: dict[str, PluginSpec] | None = None


def _iter_plugin_entry_points():
    try:
        return get_entry_points(group=PLUGIN_GROUP)
    except TypeError:
        return get_entry_points().get(PLUGIN_GROUP, [])


def _spec_from_entry_point(ep) -> PluginSpec:
    plugin_cls = ep.load()
    if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, GamePlugin):
        raise TypeError(f"插件 {ep.name} 必须继承 GamePlugin，实际: {plugin_cls!r}")

    game_id = getattr(plugin_cls, "game_id", None) or ep.name
    display_name = getattr(plugin_cls, "display_name", "") or ""
    return PluginSpec(
        game_id=game_id,
        plugin_cls=plugin_cls,
        display_name=display_name,
        source="entry-point",
    )


def load_plugin_registry(*, force_reload: bool = False) -> dict[str, PluginSpec]:
    global _REGISTRY
    if _REGISTRY is not None and not force_reload:
        return _REGISTRY

    registry: dict[str, PluginSpec] = dict(_BUILTIN_REGISTRY)
    for ep in _iter_plugin_entry_points():
        spec = _spec_from_entry_point(ep)
        registry[spec.game_id] = spec

    _REGISTRY = registry
    return _REGISTRY


def reload_plugin_registry() -> dict[str, PluginSpec]:
    return load_plugin_registry(force_reload=True)


def list_registered_games() -> list[str]:
    return sorted(load_plugin_registry().keys())


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
    spec = load_plugin_registry().get(game_id)
    if spec is None:
        available = ", ".join(list_registered_games()) or "(无)"
        raise KeyError(
            f"未注册的游戏插件: {game_id}。"
            f"请在 pyproject.toml 的 [project.entry-points.\"{PLUGIN_GROUP}\"] 注册，"
            f"当前可用: {available}"
        )
    return spec


def get_plugin(profile: GameProfile) -> GamePlugin:
    return get_plugin_spec(profile.game_id).plugin_cls(profile)
