"""运行时资源绑定。"""

from __future__ import annotations

from ocr4game.perception.fusion import Perception
from ocr4game.platform.capture import ScreenCapture
from ocr4game.platform.input_win import InputDriver
from ocr4game.platform.window import GameWindow
from ocr4game.workflow.context import RunContext


def bind_runtime(ctx: RunContext) -> bool:
    titles = ctx.profile.window.title_contains
    window = GameWindow.find_by_titles(titles)
    if window is None:
        ctx.log.error("未找到游戏窗口", game=ctx.profile.game_id, titles=titles)
        return False

    ctx.window = window
    ctx.capture = ScreenCapture(window)
    ctx.input = InputDriver(window, click_jitter=ctx.global_cfg.input.click_jitter)
    ctx.perception = Perception(ctx.profile)
    return True
