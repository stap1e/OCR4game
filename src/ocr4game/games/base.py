"""游戏插件抽象。"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

import numpy as np

from ocr4game.config import GameProfile
from ocr4game.workflow.context import RunContext

if TYPE_CHECKING:
    from ocr4game.workflow.actions import ActionRegistry


class GamePlugin(ABC):
    game_id: str
    display_name: str = ""

    def __init__(self, profile: GameProfile) -> None:
        self.profile = profile

    def preflight(self, ctx: RunContext) -> bool:
        return True

    def normalize_frame(self, frame: np.ndarray) -> np.ndarray:
        return frame

    def register_actions(self, registry: ActionRegistry) -> None:
        return None

    def on_step_failure(self, ctx: RunContext, step_id: str, frame: np.ndarray) -> None:
        key = self.profile.recovery.escape_key
        if ctx.input:
            ctx.input.press(key)
