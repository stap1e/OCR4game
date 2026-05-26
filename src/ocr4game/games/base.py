"""游戏插件抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ocr4game.config import GameProfile
from ocr4game.workflow.context import RunContext


class GamePlugin(ABC):
    game_id: str

    def __init__(self, profile: GameProfile) -> None:
        self.profile = profile

    @abstractmethod
    def preflight(self, ctx: RunContext) -> bool:
        """运行前检查：窗口、分辨率等。"""

    def normalize_frame(self, frame: np.ndarray) -> np.ndarray:
        return frame

    def on_step_failure(self, ctx: RunContext, step_id: str, frame: np.ndarray) -> None:
        """失败恢复：默认按 Esc。"""
        key = self.profile.recovery.get("escape_key", "escape")
        if ctx.input:
            ctx.input.press(key)
