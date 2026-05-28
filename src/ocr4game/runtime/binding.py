"""运行时资源绑定。"""

from __future__ import annotations

from ocr4game.perception.fusion import Perception
from ocr4game.platform.capture import ScreenCapture
from ocr4game.platform.input_win import InputDriver
from ocr4game.platform.window import GameWindow
from ocr4game.workflow.context import RunContext


def bind_runtime(ctx: RunContext) -> bool:
    window_cfg = ctx.profile.window
    resolution = ctx.profile.resolution
    window, mode = GameWindow.find_with_fallback(
        window_cfg.title_contains,
        title_exclude=window_cfg.title_exclude,
        class_exclude=window_cfg.class_exclude,
        process_names=window_cfg.process_names,
        expected_size=(resolution.width, resolution.height),
        size_tolerance=resolution.tolerance,
    )
    if window is None:
        ctx.log.error(
            "未找到游戏窗口",
            game=ctx.profile.game_id,
            titles=window_cfg.title_contains,
            exclude=window_cfg.title_exclude or None,
            process_names=window_cfg.process_names or None,
            expected_resolution=(resolution.width, resolution.height),
            hint="运行 ocr4game-annotate --game star_rail --list-windows --verbose",
        )
        return False

    ctx.window = window
    ctx.capture = ScreenCapture(window)
    ctx.input = InputDriver(window, click_jitter=ctx.global_cfg.input.click_jitter)
    ctx.perception = Perception(ctx.profile)
    ctx.log.info(
        "窗口已绑定",
        match_mode=mode,
        title=window.title,
        process=window.process_name or "(unknown)",
        class_name=window.class_name,
        client_size=window.client_size(),
        capture_hwnd=window.capture_hwnd(),
    )
    return True
